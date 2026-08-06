import csv
import io
import logging
import re

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ello.database import SessionLocal
from ello.models import Livro, gerar_chave_catalografica, normalizar_texto
from ello.routes.auth import exigir_cargo

router = APIRouter(
    prefix="/livros",
    tags=["Livros"],
    dependencies=[Depends(exigir_cargo("biblioteca"))],
)
logger = logging.getLogger(__name__)


class LivroEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    cdu: str = Field(min_length=1)
    titulo: str = Field(min_length=1)
    autor: str | None = None
    editora: str | None = None
    data_publicacao: str | None = None
    edicao: str | None = None
    colecao_serie: str | None = None
    numero_paginas: int | None = Field(default=None, gt=0)
    confirmar_duplicado: bool = False

    @field_validator("autor", "editora", "data_publicacao", "edicao", "colecao_serie")
    @classmethod
    def vazio_vira_nulo(cls, valor: str | None):
        return valor or None


class LivroAtualizacao(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    cdu: str | None = Field(default=None, min_length=1)
    titulo: str | None = Field(default=None, min_length=1)
    autor: str | None = None
    editora: str | None = None
    data_publicacao: str | None = None
    edicao: str | None = None
    colecao_serie: str | None = None
    numero_paginas: int | None = Field(default=None, gt=0)
    estoque: int | None = Field(default=None, ge=0)


class LivroResposta(BaseModel):
    id: int
    cdu: str
    titulo: str
    autor: str | None
    editora: str | None
    data_publicacao: str | None
    edicao: str | None
    colecao_serie: str | None
    numero_paginas: int | None
    estoque: int


class ImportacaoCsv(BaseModel):
    conteudo: str = Field(min_length=1)


def gerar_chave(data: LivroEntrada) -> str:
    # CDU, coleção e páginas descrevem o exemplar, mas não definem uma nova edição.
    return gerar_chave_catalografica(
        data.titulo,
        data.autor,
        data.editora,
        data.data_publicacao,
        data.edicao,
    )


def livro_para_dict(livro: Livro):
    return {
        "id": livro.id,
        "cdu": livro.cdu,
        "titulo": livro.titulo,
        "autor": livro.autor,
        "editora": livro.editora,
        "data_publicacao": livro.data_publicacao,
        "edicao": livro.edicao,
        "colecao_serie": livro.colecao_serie,
        "numero_paginas": livro.numero_paginas,
        "estoque": livro.estoque,
    }


def dados_do_livro(data: LivroEntrada):
    return data.model_dump(exclude={"confirmar_duplicado"})


@router.post("", status_code=201, response_model=LivroResposta)
def cadastrar_livro(data: LivroEntrada, response: Response):
    with SessionLocal() as banco:
        try:
            chave = gerar_chave(data)
            existente = banco.scalar(
                select(Livro).where(Livro.chave_catalografica == chave)
            )

            if existente is not None and not data.confirmar_duplicado:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "precisa_confirmacao": True,
                        "mensagem": (
                            "Este livro já está cadastrado. Confirme para adicionar "
                            "mais uma unidade ao estoque."
                        ),
                        "livro": livro_para_dict(existente),
                    },
                )

            if existente is not None:
                existente.estoque += 1
                banco.commit()
                banco.refresh(existente)
                response.status_code = 200
                return livro_para_dict(existente)

            livro = Livro(**dados_do_livro(data), estoque=1, chave_catalografica=chave)
            banco.add(livro)
            banco.commit()
            banco.refresh(livro)
            return livro_para_dict(livro)
        except HTTPException:
            raise
        except IntegrityError:
            banco.rollback()
            raise HTTPException(
                status_code=409,
                detail={
                    "precisa_confirmacao": True,
                    "mensagem": "Este livro já está cadastrado.",
                },
            )
        except SQLAlchemyError as erro:
            banco.rollback()
            logger.exception("Erro ao cadastrar livro")
            raise HTTPException(
                status_code=500, detail="Erro ao salvar no banco de dados"
            ) from erro


def limpar_conteudo_csv(conteudo: str) -> str:
    conteudo = conteudo.lstrip("\ufeff").strip()
    if conteudo.startswith('"\n') and conteudo.endswith('"'):
        conteudo = conteudo[1:-1]
    return conteudo


def paginas_para_int(valor: str) -> int | None:
    numeros = re.sub(r"\D", "", valor)
    return int(numeros) if numeros else None


@router.post("/importar-csv", status_code=201)
def importar_csv(data: ImportacaoCsv):
    leitor = csv.reader(io.StringIO(limpar_conteudo_csv(data.conteudo)), delimiter=";")
    novos = 0
    estoque_adicionado = 0
    linhas_lidas = 0
    erros = []
    catalogo = {}

    for numero_linha, linha in enumerate(leitor, start=1):
        if not linha or not any(celula.strip() for celula in linha):
            continue
        if "cdu" in normalizar_texto(linha[0]):
            continue

        linhas_lidas += 1
        if len(linha) != 8:
            erros.append(
                {
                    "linha": numero_linha,
                    "erro": f"Esperadas 8 colunas, recebidas {len(linha)}.",
                }
            )
            continue

        try:
            entrada = LivroEntrada(
                cdu=linha[0],
                titulo=linha[1],
                autor=linha[2] or None,
                editora=linha[3] or None,
                data_publicacao=linha[4] or None,
                edicao=linha[5] or None,
                colecao_serie=linha[6] or None,
                numero_paginas=paginas_para_int(linha[7]),
            )
        except ValidationError as erro:
            erros.append({"linha": numero_linha, "erro": str(erro)})
            continue

        chave = gerar_chave(entrada)
        if chave in catalogo:
            catalogo[chave]["quantidade"] += 1
        else:
            catalogo[chave] = {"entrada": entrada, "quantidade": 1}

    with SessionLocal() as banco:
        try:
            existentes = {
                livro.chave_catalografica: livro
                for livro in banco.scalars(
                    select(Livro).where(Livro.chave_catalografica.in_(list(catalogo)))
                ).all()
            }

            for chave, item in catalogo.items():
                quantidade = item["quantidade"]
                existente = existentes.get(chave)
                if existente is not None:
                    existente.estoque += quantidade
                    estoque_adicionado += quantidade
                else:
                    banco.add(
                        Livro(
                            **dados_do_livro(item["entrada"]),
                            estoque=quantidade,
                            chave_catalografica=chave,
                        )
                    )
                    novos += 1
                    estoque_adicionado += quantidade - 1

            banco.commit()
            return {
                "linhas_lidas": linhas_lidas,
                "livros_novos": novos,
                "unidades_adicionadas_ao_estoque": estoque_adicionado,
                "linhas_com_erro": len(erros),
                "erros": erros,
            }
        except SQLAlchemyError as erro:
            banco.rollback()
            logger.exception("Erro ao importar CSV de livros")
            raise HTTPException(
                status_code=500, detail="Erro ao importar o CSV para o banco de dados"
            ) from erro


@router.get("", response_model=list[LivroResposta])
def listar_livros():
    with SessionLocal() as banco:
        livros = banco.scalars(select(Livro).order_by(Livro.titulo)).all()
        return [livro_para_dict(livro) for livro in livros]


@router.get("/{livro_id}", response_model=LivroResposta)
def buscar_livro(livro_id: int):
    with SessionLocal() as banco:
        livro = banco.get(Livro, livro_id)

        if livro is None:
            raise HTTPException(status_code=404, detail="Livro não encontrado.")

        return livro_para_dict(livro)


@router.put("/{livro_id}", response_model=LivroResposta)
def atualizar_livro(livro_id: int, data: LivroAtualizacao):
    with SessionLocal() as banco:
        livro = banco.get(Livro, livro_id)
        if livro is None:
            raise HTTPException(status_code=404, detail="Livro não encontrado.")

        alteracoes = data.model_dump(exclude_unset=True)
        if not alteracoes:
            return livro_para_dict(livro)

        valores = livro_para_dict(livro) | alteracoes
        if valores["cdu"] is None or valores["titulo"] is None:
            raise HTTPException(
                status_code=422, detail="CDU e título não podem ser nulos."
            )

        chave = gerar_chave_catalografica(
            valores["titulo"],
            valores["autor"],
            valores["editora"],
            valores["data_publicacao"],
            valores["edicao"],
        )
        duplicado = banco.scalar(
            select(Livro).where(
                Livro.chave_catalografica == chave,
                Livro.id != livro_id,
            )
        )
        if duplicado is not None:
            raise HTTPException(
                status_code=409,
                detail="A alteração deixaria dois cadastros para o mesmo livro.",
            )

        try:
            for campo, valor in alteracoes.items():
                setattr(livro, campo, valor)
            livro.chave_catalografica = chave
            banco.commit()
            banco.refresh(livro)
            return livro_para_dict(livro)
        except IntegrityError as erro:
            banco.rollback()
            raise HTTPException(
                status_code=409, detail="Já existe um cadastro para esse livro."
            ) from erro
        except SQLAlchemyError as erro:
            banco.rollback()
            logger.exception("Erro ao atualizar livro %s", livro_id)
            raise HTTPException(
                status_code=500, detail="Erro ao salvar no banco de dados."
            ) from erro


@router.delete("/{livro_id}")
def excluir_livro(livro_id: int, remover_todos: bool = False):
    """Remove uma unidade; remover_todos=true apaga o cadastro inteiro."""
    with SessionLocal() as banco:
        livro = banco.get(Livro, livro_id)
        if livro is None:
            raise HTTPException(status_code=404, detail="Livro não encontrado.")

        try:
            if livro.estoque > 1 and not remover_todos:
                livro.estoque -= 1
                banco.commit()
                banco.refresh(livro)
                return {
                    "cadastro_excluido": False,
                    "estoque": livro.estoque,
                }

            banco.delete(livro)
            banco.commit()
            return {"cadastro_excluido": True, "estoque": 0}
        except SQLAlchemyError as erro:
            banco.rollback()
            logger.exception("Erro ao excluir livro %s", livro_id)
            raise HTTPException(
                status_code=500, detail="Erro ao excluir livro do banco de dados."
            ) from erro
