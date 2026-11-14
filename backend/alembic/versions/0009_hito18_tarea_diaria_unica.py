"""Restricción única por plantilla y fecha en tareas_diarias (Hito 18.2)

Revision ID: 0009_hito18_tarea_diaria_unica
Revises: 0008_hito17_integridad_y_rls
Create Date: 2026-11-14

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0009_hito18_tarea_diaria_unica"
down_revision: str | None = "0008_hito17_integridad_y_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tareas_diarias") as batch_op:
        batch_op.create_unique_constraint("uq_tarea_diaria_plantilla_fecha", ["plantilla_id", "fecha"])


def downgrade() -> None:
    with op.batch_alter_table("tareas_diarias") as batch_op:
        batch_op.drop_constraint("uq_tarea_diaria_plantilla_fecha", type_="unique")
