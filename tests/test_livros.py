import pytest
from fastapi import HTTPException, Response
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from ello.database import Base
from ello.routes import livros


@pytest.fixture(autouse=True)
def banco_temporario(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    monkeypatch.setattr(livros, "SessionLocal", sessionmaker(bind=engine))


def test_duplicata_exige_confirmacao_e_depois_incrementa_estoque():
    entrada = livros.LivroEntrada(
        cdu="1 - Filosofia. Psicologia.",
        titulo="As razões do iluminismo",
        autor="Sergio Paulo Rouanet",
        editora="Companhia de Letras",
        data_publicacao="1987",
        edicao="1º ed.",
        colecao_serie="V.1",
        numero_paginas=349,
    )
    livros.cadastrar_livro(entrada, Response())

    with pytest.raises(HTTPException) as erro:
        livros.cadastrar_livro(entrada, Response())
    assert erro.value.status_code == 409
    assert erro.value.detail["precisa_confirmacao"] is True

    confirmada = entrada.model_copy(update={"confirmar_duplicado": True})
    resultado = livros.cadastrar_livro(confirmada, Response())
    assert resultado["estoque"] == 2
    assert len(livros.listar_livros()) == 1


def test_importacao_csv_agrupa_livros_repetidos():
    linha = (
        "2 - Religião. Teologia;A voz do silêncio;H. P. Blavatsky;"
        "Pensamento;2010;1º e.d.;Budismo - Tibete;127"
    )
    resultado = livros.importar_csv(livros.ImportacaoCsv(conteudo=f"{linha}\n{linha}"))

    assert resultado["livros_novos"] == 1
    assert resultado["unidades_adicionadas_ao_estoque"] == 1
    assert resultado["linhas_com_erro"] == 0
    assert livros.listar_livros()[0]["estoque"] == 2
