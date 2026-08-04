from sqlalchemy.orm import Mapped, mapped_column

from ello.database import Base


class Aluno(Base):
    __tablename__ = "alunos"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(unique=True, index=True)
    nome: Mapped[str]
    turma: Mapped[str]
    telefone: Mapped[str]
