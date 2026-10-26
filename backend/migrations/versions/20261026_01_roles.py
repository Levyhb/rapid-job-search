"""Cria cadastro de cargos e variações."""

import sqlalchemy as sa
from alembic import op

revision = "20261026_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("nome", sa.String(120), nullable=False),
        sa.Column("normalized_name", sa.String(240), nullable=False),
        sa.Column("variacoes", sa.JSON(), nullable=False),
        sa.Column("selecionado", sa.Boolean(), nullable=False),
        sa.UniqueConstraint("normalized_name", name="uq_roles_normalized_name"),
    )


def downgrade():
    op.drop_table("roles")
