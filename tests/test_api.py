import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ello import config
from ello.database import Base
from ello.main import app
from ello.models import Cargo, Usuario
from ello.routes import alunos, auth, livros, usuarios


@pytest.fixture
def cliente(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessao = sessionmaker(bind=engine)
    for modulo in (alunos, auth, livros, usuarios):
        monkeypatch.setattr(modulo, "SessionLocal", sessao)
    monkeypatch.setattr(
        config, "JWT_SECRET", "segredo-de-testes-com-mais-de-trinta-e-dois-caracteres"
    )

    with sessao() as banco:
        admin = Cargo(nome="admin")
        biblioteca = Cargo(nome="biblioteca")
        banco.add_all([admin, biblioteca])
        banco.flush()
        banco.add_all(
            [
                Usuario(
                    nome="Administrador",
                    login="admin",
                    senha_hash=auth.gerar_hash("senha-admin"),
                    cargos=[admin],
                ),
                Usuario(
                    nome="Bibliotecária",
                    login="biblioteca",
                    senha_hash=auth.gerar_hash("senha-biblioteca"),
                    cargos=[biblioteca],
                ),
                Usuario(
                    nome="Sem cargo",
                    login="comum",
                    senha_hash=auth.gerar_hash("senha-comum"),
                ),
            ]
        )
        banco.commit()

    return TestClient(app)


def autenticar(cliente, login, senha):
    resposta = cliente.post("/auth/login", json={"login": login, "senha": senha})
    assert resposta.status_code == 200
    return {"Authorization": f"Bearer {resposta.json()['access_token']}"}


def test_biblioteca_exige_login_e_cargo(cliente):
    assert cliente.get("/alive").status_code == 200
    assert cliente.get("/alunos").status_code == 401

    comum = autenticar(cliente, "comum", "senha-comum")
    assert cliente.get("/alunos", headers=comum).status_code == 403

    biblioteca = autenticar(cliente, "biblioteca", "senha-biblioteca")
    assert cliente.get("/alunos", headers=biblioteca).status_code == 200


def test_fluxo_http_de_aluno_com_cargo_biblioteca(cliente):
    headers = autenticar(cliente, "biblioteca", "senha-biblioteca")
    resposta = cliente.post(
        "/alunos",
        headers=headers,
        json={
            "matricula": "0007",
            "nome": "Ana Lima",
            "turma": "2º B",
            "telefone": "(84) 98888-7777",
        },
    )
    assert resposta.status_code == 201
    aluno_id = resposta.json()["id"]
    assert cliente.get(f"/alunos/{aluno_id}", headers=headers).status_code == 200

    resposta = cliente.put(
        f"/alunos/{aluno_id}",
        headers=headers,
        json={
            "matricula": "0007",
            "nome": "Ana Lima Souza",
            "turma": "2º B",
            "telefone": "(84) 98888-7777",
        },
    )
    assert resposta.json()["nome"] == "Ana Lima Souza"
    assert cliente.delete(f"/alunos/{aluno_id}", headers=headers).status_code == 204


def test_admin_cria_usuario_e_atribui_cargo(cliente):
    headers = autenticar(cliente, "admin", "senha-admin")
    resposta = cliente.post(
        "/usuarios",
        headers=headers,
        json={
            "nome": "Funcionário novo",
            "login": "funcionario",
            "senha": "senha-segura",
            "cargos": ["biblioteca"],
        },
    )
    assert resposta.status_code == 201
    assert resposta.json()["cargos"] == ["biblioteca"]

    acesso = autenticar(cliente, "funcionario", "senha-segura")
    assert cliente.get("/livros", headers=acesso).status_code == 200


def test_usuario_biblioteca_nao_administra_contas(cliente):
    headers = autenticar(cliente, "biblioteca", "senha-biblioteca")
    assert cliente.get("/usuarios", headers=headers).status_code == 403
