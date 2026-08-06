import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ello.database import SessionLocal
from ello.models import Cargo, Usuario
from ello.routes.auth import exigir_cargo, gerar_hash

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/usuarios", tags=["Usuários"])
AdminAtual = Annotated[Usuario, Depends(exigir_cargo("admin"))]


class UsuarioCriacao(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    nome: str = Field(min_length=1, max_length=200)
    login: str = Field(min_length=1, max_length=100)
    senha: str = Field(min_length=8, max_length=200)
    cargos: list[str] = Field(default_factory=list)


class CargosAtualizacao(BaseModel):
    cargos: list[str]


class SenhaAtualizacao(BaseModel):
    senha: str = Field(min_length=8, max_length=200)


class AtivoAtualizacao(BaseModel):
    ativo: bool


class UsuarioResposta(BaseModel):
    id: int
    nome: str
    login: str
    ativo: bool
    cargos: list[str]


def usuario_para_dict(usuario: Usuario):
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "login": usuario.login,
        "ativo": usuario.ativo,
        "cargos": sorted(cargo.nome for cargo in usuario.cargos),
    }


def buscar_cargos(banco, nomes: list[str]) -> list[Cargo]:
    nomes_normalizados = {nome.strip().casefold() for nome in nomes if nome.strip()}
    cargos = banco.scalars(
        select(Cargo).where(Cargo.nome.in_(nomes_normalizados))
    ).all()
    encontrados = {cargo.nome for cargo in cargos}
    inexistentes = nomes_normalizados - encontrados
    if inexistentes:
        raise HTTPException(
            status_code=422,
            detail=f"Cargos inexistentes: {', '.join(sorted(inexistentes))}.",
        )
    return list(cargos)


@router.post("", status_code=201, response_model=UsuarioResposta)
def criar_usuario(data: UsuarioCriacao, _admin: AdminAtual):
    with SessionLocal() as banco:
        try:
            usuario = Usuario(
                nome=data.nome,
                login=data.login.casefold(),
                senha_hash=gerar_hash(data.senha),
                cargos=buscar_cargos(banco, data.cargos),
            )
            banco.add(usuario)
            banco.commit()
            banco.refresh(usuario)
            return usuario_para_dict(usuario)
        except IntegrityError as erro:
            banco.rollback()
            raise HTTPException(
                status_code=409, detail="Já existe um usuário com esse login."
            ) from erro
        except SQLAlchemyError as erro:
            banco.rollback()
            logger.exception("Erro ao criar usuário")
            raise HTTPException(
                status_code=500, detail="Erro ao salvar usuário no banco de dados."
            ) from erro


@router.get("", response_model=list[UsuarioResposta])
def listar_usuarios(_admin: AdminAtual):
    with SessionLocal() as banco:
        usuarios = banco.scalars(select(Usuario).order_by(Usuario.nome)).all()
        return [usuario_para_dict(usuario) for usuario in usuarios]


@router.put("/{usuario_id}/cargos", response_model=UsuarioResposta)
def atualizar_cargos(usuario_id: int, data: CargosAtualizacao, admin: AdminAtual):
    with SessionLocal() as banco:
        usuario = banco.get(Usuario, usuario_id)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")

        cargos = buscar_cargos(banco, data.cargos)
        if usuario_id == admin.id and "admin" not in {cargo.nome for cargo in cargos}:
            raise HTTPException(
                status_code=400, detail="O admin não pode remover o próprio cargo."
            )

        usuario.cargos = cargos
        banco.commit()
        banco.refresh(usuario)
        return usuario_para_dict(usuario)


@router.put("/{usuario_id}/senha", status_code=204)
def redefinir_senha(usuario_id: int, data: SenhaAtualizacao, _admin: AdminAtual):
    with SessionLocal() as banco:
        usuario = banco.get(Usuario, usuario_id)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        usuario.senha_hash = gerar_hash(data.senha)
        banco.commit()


@router.put("/{usuario_id}/ativo", response_model=UsuarioResposta)
def alterar_ativo(usuario_id: int, data: AtivoAtualizacao, admin: AdminAtual):
    if usuario_id == admin.id and not data.ativo:
        raise HTTPException(
            status_code=400, detail="O admin não pode desativar a própria conta."
        )

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, usuario_id)
        if usuario is None:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        usuario.ativo = data.ativo
        banco.commit()
        banco.refresh(usuario)
        return usuario_para_dict(usuario)
