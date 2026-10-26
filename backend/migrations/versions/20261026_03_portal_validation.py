"""Estado de validação de suporte por URL cadastrada."""

import sqlalchemy as sa
from alembic import op

revision = "20261026_03"
down_revision = "20261026_02"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "portal_validations",
        sa.Column("company_id", sa.String(36), primary_key=True),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("request_token", sa.String(36), nullable=False),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("requested_at", sa.Float(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
    )


def downgrade():
    op.drop_table("portal_validations")
