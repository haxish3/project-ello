from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from ello import config
from ello.database import SessionLocal
from ello.models import Usuario

router = APIRouter(prefix="/auth", tags=["Autenticação"])
bearer = HTTPBearer(auto_error=False)
password_hash = PasswordHash.recommended()
ALGORITMO = "HS256"


class LoginEntrada(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    login: str = Field(min_length=1, max_length=100)
    senha: str = Field(min_length=1, max_length=200)


class TokenResposta(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UsuarioLogadoResposta(BaseModel):
    id: int
    nome: str
    login: str
    cargos: list[str]


def gerar_hash(senha: str) -> str:
    return password_hash.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    return password_hash.verify(senha, senha_hash)


def validar_segredo():
    if len(config.JWT_SECRET) < 32:
        raise HTTPException(
            status_code=500,
            detail="JWT_SECRET não está configurado corretamente no servidor.",
        )


def criar_token(usuario_id: int) -> str:
    validar_segredo()
    agora = datetime.now(UTC)
    payload = {
        "sub": str(usuario_id),
        "iat": agora,
        "exp": agora + timedelta(minutes=config.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=ALGORITMO)


def usuario_atual(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Usuario:
    erro_credencial = HTTPException(
        status_code=401,
        detail="Login necessário.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credenciais is None:
        raise erro_credencial

    validar_segredo()
    try:
        payload = jwt.decode(
            credenciais.credentials,
            config.JWT_SECRET,
            algorithms=[ALGORITMO],
        )
        usuario_id = int(payload["sub"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as erro:
        raise erro_credencial from erro

    with SessionLocal() as banco:
        usuario = banco.get(Usuario, usuario_id)
        if usuario is None or not usuario.ativo:
            raise erro_credencial
        banco.expunge(usuario)
        return usuario


def exigir_cargo(cargo_necessario: str):
    def verificar(usuario: Annotated[Usuario, Depends(usuario_atual)]):
        cargos = {cargo.nome for cargo in usuario.cargos}
        if not cargos.intersection({"admin", "dev"}) and cargo_necessario not in cargos:
            raise HTTPException(
                status_code=403,
                detail="Você não tem permissão para acessar este recurso.",
            )
        return usuario

    return verificar


def exigir_dev(usuario: Annotated[Usuario, Depends(usuario_atual)]):
    if "dev" not in {cargo.nome for cargo in usuario.cargos}:
        raise HTTPException(
            status_code=403,
            detail="Esta ação é exclusiva para desenvolvedores.",
        )
    return usuario


@router.post("/login", response_model=TokenResposta)
def login(data: LoginEntrada):
    with SessionLocal() as banco:
        usuario = banco.scalar(
            select(Usuario).where(Usuario.login == data.login.casefold())
        )
        if (
            usuario is None
            or not usuario.ativo
            or not verificar_senha(data.senha, usuario.senha_hash)
        ):
            raise HTTPException(status_code=401, detail="Login ou senha inválidos.")
        return TokenResposta(access_token=criar_token(usuario.id))


@router.get("/me", response_model=UsuarioLogadoResposta)
def meus_dados(usuario: Annotated[Usuario, Depends(usuario_atual)]):
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "login": usuario.login,
        "cargos": sorted(cargo.nome for cargo in usuario.cargos),
    }
