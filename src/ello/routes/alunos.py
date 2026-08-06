import logging

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ello.database import SessionLocal
from ello.models import Aluno
from ello.routes.auth import exigir_cargo

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/alunos",
    tags=["Alunos"],
    dependencies=[Depends(exigir_cargo("biblioteca"))],
)


class AlunoDados(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    matricula: str = Field(min_length=1, max_length=50)
    nome: str = Field(min_length=1, max_length=200)
    turma: str = Field(min_length=1, max_length=100)
    telefone: str = Field(min_length=1, max_length=30)


class AlunoResposta(AlunoDados):
    model_config = ConfigDict(from_attributes=True)

    id: int


def conflito_matricula(erro: IntegrityError) -> HTTPException:
    return HTTPException(
        status_code=409,
        detail="Já existe um aluno com essa matrícula.",
    )


@router.post("", status_code=201, response_model=AlunoResposta)
def cadastrar_aluno(data: AlunoDados):
    with SessionLocal() as banco:
        try:
            aluno = Aluno(**data.model_dump())
            banco.add(aluno)
            banco.commit()
            banco.refresh(aluno)
            return aluno
        except IntegrityError as erro:
            banco.rollback()
            raise conflito_matricula(erro) from erro
        except SQLAlchemyError as erro:
            banco.rollback()
            logger.exception("Erro ao cadastrar aluno")
            raise HTTPException(
                status_code=500, detail="Erro ao salvar no banco de dados."
            ) from erro


@router.get("", response_model=list[AlunoResposta])
def listar_alunos():
    with SessionLocal() as banco:
        return banco.scalars(select(Aluno).order_by(Aluno.nome)).all()


@router.get("/{aluno_id}", response_model=AlunoResposta)
def buscar_aluno(aluno_id: int):
    with SessionLocal() as banco:
        aluno = banco.get(Aluno, aluno_id)
        if aluno is None:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")
        return aluno


@router.put("/{aluno_id}", response_model=AlunoResposta)
def atualizar_aluno(aluno_id: int, data: AlunoDados):
    with SessionLocal() as banco:
        aluno = banco.get(Aluno, aluno_id)
        if aluno is None:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")

        try:
            for campo, valor in data.model_dump().items():
                setattr(aluno, campo, valor)
            banco.commit()
            banco.refresh(aluno)
            return aluno
        except IntegrityError as erro:
            banco.rollback()
            raise conflito_matricula(erro) from erro
        except SQLAlchemyError as erro:
            banco.rollback()
            logger.exception("Erro ao atualizar aluno %s", aluno_id)
            raise HTTPException(
                status_code=500, detail="Erro ao salvar no banco de dados."
            ) from erro


@router.delete("/{aluno_id}", status_code=204)
def excluir_aluno(aluno_id: int):
    with SessionLocal() as banco:
        aluno = banco.get(Aluno, aluno_id)
        if aluno is None:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")

        try:
            banco.delete(aluno)
            banco.commit()
            return Response(status_code=204)
        except SQLAlchemyError as erro:
            banco.rollback()
            logger.exception("Erro ao excluir aluno %s", aluno_id)
            raise HTTPException(
                status_code=500, detail="Erro ao excluir aluno do banco de dados."
            ) from erro
