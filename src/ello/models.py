import re
import unicodedata

from sqlalchemy import Boolean, CheckConstraint, Column, ForeignKey, String, Table
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


usuarios_cargos = Table(
    "usuarios_cargos",
    Base.metadata,
    Column(
        "usuario_id", ForeignKey("usuarios.id", ondelete="CASCADE"), primary_key=True
    ),
    Column("cargo_id", ForeignKey("cargos.id", ondelete="CASCADE"), primary_key=True),
)


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(200))
    login: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(500))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    cargos: Mapped[list["Cargo"]] = relationship(
        secondary=usuarios_cargos,
        back_populates="usuarios",
        lazy="selectin",
    )


class Cargo(Base):
    __tablename__ = "cargos"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    usuarios: Mapped[list[Usuario]] = relationship(
        secondary=usuarios_cargos,
        back_populates="cargos",
    )


class Aluno(Base):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    nome: Mapped[str] = mapped_column(String(200))
    turma: Mapped[str] = mapped_column(String(100))
    telefone: Mapped[str] = mapped_column(String(30))


class Livro(Base):
    __tablename__ = "livros"
    __table_args__ = (CheckConstraint("estoque >= 0", name="ck_livros_estoque"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cdu: Mapped[str] = mapped_column(String(100), index=True)
    titulo: Mapped[str] = mapped_column(String(300), index=True)
    autor: Mapped[str | None] = mapped_column(String(300))
    editora: Mapped[str | None] = mapped_column(String(200))
    data_publicacao: Mapped[str | None] = mapped_column(String(50))
    edicao: Mapped[str | None] = mapped_column(String(50))
    colecao_serie: Mapped[str | None] = mapped_column(String(200))
    numero_paginas: Mapped[int | None]
    estoque: Mapped[int] = mapped_column(default=1)
    chave_catalografica: Mapped[str] = mapped_column(
        String(1000), unique=True, index=True
    )
