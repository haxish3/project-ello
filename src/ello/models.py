import re
import unicodedata

from sqlalchemy.orm import Mapped, mapped_column

from ello.database import Base


def normalizar_texto(valor: str | None) -> str:
    if not valor:
        return ""
    valor = unicodedata.normalize("NFKD", valor.casefold())
    valor = "".join(letra for letra in valor if not unicodedata.combining(letra))
    return " ".join(re.findall(r"[a-z0-9]+", valor))


def gerar_chave_catalografica(
    titulo: str,
    autor: str | None,
    editora: str | None,
    data_publicacao: str | None,
    edicao: str | None,
) -> str:
    campos = (titulo, autor, editora, data_publicacao, edicao)
    return "|".join(normalizar_texto(campo) for campo in campos)


class Aluno(Base):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(unique=True, index=True)
    nome: Mapped[str]
    turma: Mapped[str]
    telefone: Mapped[str]


class Livro(Base):
    __tablename__ = "livros"

    id: Mapped[int] = mapped_column(primary_key=True)
    cdu: Mapped[str] = mapped_column(index=True)
    titulo: Mapped[str] = mapped_column(index=True)
    autor: Mapped[str | None]
    editora: Mapped[str | None]
    data_publicacao: Mapped[str | None]
    edicao: Mapped[str | None]
    colecao_serie: Mapped[str | None]
    numero_paginas: Mapped[int | None]
    estoque: Mapped[int] = mapped_column(default=1)
    chave_catalografica: Mapped[str | None] = mapped_column(unique=True, index=True)
