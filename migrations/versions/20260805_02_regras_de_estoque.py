"""garante chave catalográfica e estoque válido"""

import sqlalchemy as sa
from alembic import op

revision = "20260805_02"
down_revision = "20260805_01"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("livros") as lote:
        lote.alter_column(
            "chave_catalografica",
            existing_type=sa.String(length=1000),
            nullable=False,
        )
        lote.create_check_constraint("ck_livros_estoque", "estoque >= 0")


def downgrade():
    with op.batch_alter_table("livros") as lote:
        lote.drop_constraint("ck_livros_estoque", type_="check")
        lote.alter_column(
            "chave_catalografica",
            existing_type=sa.String(length=1000),
            nullable=True,
        )
