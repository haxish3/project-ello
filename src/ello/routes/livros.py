import csv
import io
import re

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ello.database import SessionLocal
from ello.models import Livro, gerar_chave_catalografica, normalizar_texto

router = APIRouter(prefix="/livros", tags=["Livros"])


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


@router.post("", status_code=201)
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
        except SQLAlchemyError:
            banco.rollback()
            raise HTTPException(
                status_code=500, detail="Erro ao salvar no banco de dados"
            )


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

    with SessionLocal() as banco:
        try:
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
                existente = banco.scalar(
                    select(Livro).where(Livro.chave_catalografica == chave)
                )
                if existente is not None:
                    existente.estoque += 1
                    estoque_adicionado += 1
                else:
                    banco.add(
                        Livro(
                            **dados_do_livro(entrada),
                            estoque=1,
                            chave_catalografica=chave,
                        )
                    )
                    banco.flush()
                    novos += 1

            banco.commit()
            return {
                "linhas_lidas": linhas_lidas,
                "livros_novos": novos,
                "unidades_adicionadas_ao_estoque": estoque_adicionado,
                "linhas_com_erro": len(erros),
                "erros": erros,
            }
        except SQLAlchemyError:
            banco.rollback()
            raise HTTPException(
                status_code=500, detail="Erro ao importar o CSV para o banco de dados"
            )


@router.get("")
def listar_livros():
    with SessionLocal() as banco:
        livros = banco.scalars(select(Livro).order_by(Livro.titulo)).all()
        return [livro_para_dict(livro) for livro in livros]


@router.get("/{livro_id}")
def buscar_livro(livro_id: int):
    with SessionLocal() as banco:
        livro = banco.get(Livro, livro_id)

        if livro is None:
            raise HTTPException(status_code=404, detail="Livro não encontrado.")

        return livro_para_dict(livro)
