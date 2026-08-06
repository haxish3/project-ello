"""adiciona cargo de desenvolvimento"""

import sqlalchemy as sa
from alembic import op

revision = "20260805_04"
down_revision = "20260805_03"
branch_labels = None
depends_on = None


def upgrade():
    cargos = sa.table("cargos", sa.column("nome", sa.String()))
    op.bulk_insert(cargos, [{"nome": "dev"}])


def downgrade():
    op.execute(sa.text("DELETE FROM cargos WHERE nome = 'dev'"))
