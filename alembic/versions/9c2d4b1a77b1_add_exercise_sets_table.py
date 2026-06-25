"""add exercise sets table

Revision ID: 9c2d4b1a77b1
Revises: ee594e83907a
Create Date: 2026-06-01 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9c2d4b1a77b1"
down_revision: Union[str, Sequence[str], None] = "ee594e83907a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "exercise_sets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exercise_id", sa.Integer(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["exercise_id"], ["exercises.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exercise_sets_id"), "exercise_sets", ["id"], unique=False)

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, sets, reps, weight FROM exercises")).fetchall()
    for row in rows:
        set_count = row.sets or 0
        for _ in range(set_count):
            conn.execute(
                sa.text(
                    """
                    INSERT INTO exercise_sets (exercise_id, reps, weight)
                    VALUES (:exercise_id, :reps, :weight)
                    """
                ),
                {
                    "exercise_id": row.id,
                    "reps": row.reps,
                    "weight": row.weight,
                },
            )

    op.drop_column("exercises", "sets")
    op.drop_column("exercises", "reps")
    op.drop_column("exercises", "weight")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column("exercises", sa.Column("sets", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("exercises", sa.Column("reps", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("exercises", sa.Column("weight", sa.Float(), nullable=False, server_default="0"))

    conn = op.get_bind()
    rows = conn.execute(
        sa.text(
            """
            SELECT exercise_id,
                   COUNT(*) AS set_count,
                   COALESCE(MAX(reps), 0) AS reps,
                   COALESCE(MAX(weight), 0) AS weight
            FROM exercise_sets
            GROUP BY exercise_id
            """
        )
    ).fetchall()

    for row in rows:
        conn.execute(
            sa.text(
                """
                UPDATE exercises
                SET sets = :sets,
                    reps = :reps,
                    weight = :weight
                WHERE id = :exercise_id
                """
            ),
            {
                "exercise_id": row.exercise_id,
                "sets": row.set_count,
                "reps": row.reps,
                "weight": row.weight,
            },
        )

    op.alter_column("exercises", "sets", server_default=None)
    op.alter_column("exercises", "reps", server_default=None)
    op.alter_column("exercises", "weight", server_default=None)

    op.drop_index(op.f("ix_exercise_sets_id"), table_name="exercise_sets")
    op.drop_table("exercise_sets")
