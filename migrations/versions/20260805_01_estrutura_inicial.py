"""estrutura inicial de alunos e livros"""

import sqlalchemy as sa
from alembic import op

revision = "20260805_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "alunos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("matricula", sa.String(length=50), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("turma", sa.String(length=100), nullable=False),
        sa.Column("telefone", sa.String(length=30), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alunos_matricula", "alunos", ["matricula"], unique=True)

    op.create_table(
        "livros",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cdu", sa.String(length=100), nullable=False),
        sa.Column("titulo", sa.String(length=300), nullable=False),
        sa.Column("autor", sa.String(length=300), nullable=True),
        sa.Column("editora", sa.String(length=200), nullable=True),
        sa.Column("data_publicacao", sa.String(length=50), nullable=True),
        sa.Column("edicao", sa.String(length=50), nullable=True),
        sa.Column("colecao_serie", sa.String(length=200), nullable=True),
        sa.Column("numero_paginas", sa.Integer(), nullable=True),
        sa.Column("estoque", sa.Integer(), nullable=False),
        sa.Column("chave_catalografica", sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_livros_cdu", "livros", ["cdu"], unique=False)
    op.create_index("ix_livros_titulo", "livros", ["titulo"], unique=False)
    op.create_index(
        "ix_livros_chave_catalografica",
        "livros",
        ["chave_catalografica"],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_livros_chave_catalografica", table_name="livros")
    op.drop_index("ix_livros_titulo", table_name="livros")
    op.drop_index("ix_livros_cdu", table_name="livros")
    op.drop_table("livros")
    op.drop_index("ix_alunos_matricula", table_name="alunos")
    op.drop_table("alunos")
