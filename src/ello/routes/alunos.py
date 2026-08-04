from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ello.database import SessionLocal
from ello.models import Aluno

router = APIRouter(prefix="/alunos", tags=["Alunos"])


class AlunoEntrada(BaseModel):
    matricula: str
    nome: str
    turma: str
    telefone: str


@router.post("", status_code=201)
def cadastrar_aluno(data: AlunoEntrada):
    with SessionLocal() as banco:
        try:
            aluno = Aluno(
                matricula=data.matricula,
                nome=data.nome,
                turma=data.turma,
                telefone=data.telefone,
            )

            banco.add(aluno)
            banco.commit()
            banco.refresh(aluno)

            return {
                "id": aluno.id,
                "matricula": aluno.matricula,
                "nome": aluno.nome,
                "turma": aluno.turma,
                "telefone": aluno.telefone,
            }

        except IntegrityError:
            banco.rollback()
            raise HTTPException(
                status_code=409, detail="Já existe um aluno com essa matrícula"
            )

        except SQLAlchemyError:
            banco.rollback()
            raise HTTPException(
                status_code=500, detail="Erro ao salvar no banco de dados"
            )


@router.get("")
def listar_alunos():
    with SessionLocal() as banco:
        alunos = banco.scalars(select(Aluno)).all()

        return [
            {
                "id": aluno.id,
                "matricula": aluno.matricula,
                "nome": aluno.nome,
                "turma": aluno.turma,
                "telefone": aluno.telefone,
            }
            for aluno in alunos
        ]


@router.get("/{id}")
def buscar_aluno(id: int):
    with SessionLocal() as banco:
        aluno = banco.get(Aluno, id)

        if aluno is None:
            raise HTTPException(status_code=404, detail="Aluno não encontrado.")

        return {
            "id": aluno.id,
            "matricula": aluno.matricula,
            "nome": aluno.nome,
            "turma": aluno.turma,
            "telefone": aluno.telefone,
        }
