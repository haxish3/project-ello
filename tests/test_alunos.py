import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ello.database import Base
from ello.routes import alunos


@pytest.fixture(autouse=True)
def banco_temporario(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(alunos, "SessionLocal", sessionmaker(bind=engine))


def dados_aluno(matricula="00123"):
    return alunos.AlunoDados(
        matricula=matricula,
        nome="  Maria da Silva  ",
        turma="3º A",
        telefone="(84) 99999-9999",
    )


def test_crud_completo_de_aluno():
    criado = alunos.cadastrar_aluno(dados_aluno())
    assert criado.nome == "Maria da Silva"

    encontrado = alunos.buscar_aluno(criado.id)
    assert encontrado.matricula == "00123"

    atualizacao = dados_aluno()
    atualizacao.nome = "Maria Souza"
    atualizado = alunos.atualizar_aluno(criado.id, atualizacao)
    assert atualizado.nome == "Maria Souza"

    alunos.excluir_aluno(criado.id)
    with pytest.raises(HTTPException) as erro:
        alunos.buscar_aluno(criado.id)
    assert erro.value.status_code == 404


def test_matricula_duplicada_retorna_conflito():
    alunos.cadastrar_aluno(dados_aluno())
    with pytest.raises(HTTPException) as erro:
        alunos.cadastrar_aluno(dados_aluno())
    assert erro.value.status_code == 409
