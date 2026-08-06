import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError

from ello.database import SessionLocal
from ello.models import Aluno, Cargo, Livro, Usuario
from ello.routes.auth import exigir_dev

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dev", tags=["Desenvolvimento"])
DevAtual = Annotated[Usuario, Depends(exigir_dev)]


class LimpezaEntrada(BaseModel):
    escopo: Literal["livros", "alunos", "usuarios", "tudo"]
    confirmacao: str


FRASES = {
    "livros": "ZERAR LIVROS",
    "alunos": "ZERAR ALUNOS",
    "usuarios": "ZERAR CONTAS",
    "tudo": "ZERAR TUDO",
}


@router.post("/limpar")
def limpar_banco(data: LimpezaEntrada, _dev: DevAtual):
    frase = FRASES[data.escopo]
    if data.confirmacao != frase:
        raise HTTPException(
            status_code=400,
            detail=f'Digite exatamente "{frase}" para confirmar.',
        )

    removidos = {"livros": 0, "alunos": 0, "usuarios": 0}
    with SessionLocal() as banco:
        try:
            if data.escopo in {"livros", "tudo"}:
                removidos["livros"] = banco.execute(delete(Livro)).rowcount
            if data.escopo in {"alunos", "tudo"}:
                removidos["alunos"] = banco.execute(delete(Aluno)).rowcount
            if data.escopo in {"usuarios", "tudo"}:
                usuarios = banco.scalars(
                    select(Usuario).where(~Usuario.cargos.any(Cargo.nome == "dev"))
                ).all()
                removidos["usuarios"] = len(usuarios)
                for usuario in usuarios:
                    banco.delete(usuario)
            banco.commit()
            return {"escopo": data.escopo, "removidos": removidos}
        except SQLAlchemyError as erro:
            banco.rollback()
            logger.exception("Erro ao limpar dados do banco")
            raise HTTPException(
                status_code=500, detail="Erro ao limpar dados do banco de dados."
            ) from erro
