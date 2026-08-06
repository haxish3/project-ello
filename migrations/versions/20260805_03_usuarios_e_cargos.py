"""adiciona usuários e cargos de acesso"""

import sqlalchemy as sa
from alembic import op

revision = "20260805_03"
down_revision = "20260805_02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cargos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cargos_nome", "cargos", ["nome"], unique=True)

    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nome", sa.String(length=200), nullable=False),
        sa.Column("login", sa.String(length=100), nullable=False),
        sa.Column("senha_hash", sa.String(length=500), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usuarios_login", "usuarios", ["login"], unique=True)

    op.create_table(
        "usuarios_cargos",
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("cargo_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["cargo_id"], ["cargos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("usuario_id", "cargo_id"),
    )

    cargos = sa.table("cargos", sa.column("nome", sa.String()))
    op.bulk_insert(cargos, [{"nome": "admin"}, {"nome": "biblioteca"}])


def downgrade():
    op.drop_table("usuarios_cargos")
    op.drop_index("ix_usuarios_login", table_name="usuarios")
    op.drop_table("usuarios")
    op.drop_index("ix_cargos_nome", table_name="cargos")
    op.drop_table("cargos")
