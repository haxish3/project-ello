from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

engine = create_engine(
    "sqlite:///./escola.db",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine)


class Base(DeclarativeBase):
    pass


def atualizar_estrutura_do_banco():
    """Aplica as pequenas alterações necessárias nos bancos SQLite já existentes."""
    colunas = {coluna["name"] for coluna in inspect(engine).get_columns("livros")}

    with engine.begin() as conexao:
        if "estoque" not in colunas:
            conexao.execute(
                text("ALTER TABLE livros ADD COLUMN estoque INTEGER NOT NULL DEFAULT 1")
            )
        if "chave_catalografica" not in colunas:
            conexao.execute(
                text("ALTER TABLE livros ADD COLUMN chave_catalografica VARCHAR")
            )
            conexao.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS "
                    "ix_livros_chave_catalografica ON livros (chave_catalografica)"
                )
            )

    # Registros criados antes da chave existir são identificados e consolidados.
    from ello.models import Livro, gerar_chave_catalografica

    with SessionLocal() as banco:
        livros_antigos = banco.scalars(
            select(Livro).where(Livro.chave_catalografica.is_(None))
        ).all()
        for livro in livros_antigos:
            chave = gerar_chave_catalografica(
                livro.titulo,
                livro.autor,
                livro.editora,
                livro.data_publicacao,
                livro.edicao,
            )
            existente = banco.scalar(
                select(Livro).where(Livro.chave_catalografica == chave)
            )
            if existente is None:
                livro.chave_catalografica = chave
            else:
                existente.estoque += livro.estoque
                banco.delete(livro)
        banco.commit()
