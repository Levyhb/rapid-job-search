"""Execuções, snapshots e resultados de vagas."""

import sqlalchemy as sa
from alembic import op

revision = "20261026_02"
down_revision = "20261026_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "search_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("active_key", sa.String(20), nullable=True, unique=True),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.Float(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column("reports", sa.JSON(), nullable=False),
    )
    op.create_table(
        "search_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("run_id", sa.String(36), sa.ForeignKey("search_runs.id"), nullable=False),
        sa.Column("identity", sa.String(500), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("title", sa.String(1000), nullable=False),
        sa.Column("url", sa.String(4000), nullable=False),
        sa.Column("modality", sa.String(20), nullable=False),
        sa.Column("modality_original", sa.String(4000), nullable=False),
        sa.Column("location", sa.String(4000), nullable=False),
        sa.Column("matches", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.UniqueConstraint("run_id", "identity", name="uq_run_identity"),
    )
    op.create_index("ix_search_jobs_run_id", "search_jobs", ["run_id"])


def downgrade():
    op.drop_table("search_jobs")
    op.drop_table("search_runs")
