"""Unicidad de facturación mensual por unidad e índice único parcial de referencias activas (Hito 17.3)

Revision ID: 0007_hito17_unicidad_finanzas
Revises: 0006_hito13_reservas_areas
Create Date: 2026-11-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0007_hito17_unicidad_finanzas"
down_revision: str | None = "0006_hito13_reservas_areas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("recibos") as batch_op:
        batch_op.create_unique_constraint("uq_recibo_unidad_periodo", ["unidad_id", "periodo"])

    op.create_index(
        "uq_pagos_metodo_ref_activo",
        "pagos_reportados",
        ["metodo_pago", "numero_referencia"],
        unique=True,
        postgresql_where=sa.text("numero_referencia IS NOT NULL AND estado != 'RECHAZADO'"),
        sqlite_where=sa.text("numero_referencia IS NOT NULL AND estado != 'RECHAZADO'"),
    )


def downgrade() -> None:
    op.drop_index("uq_pagos_metodo_ref_activo", table_name="pagos_reportados")

    with op.batch_alter_table("recibos") as batch_op:
        batch_op.drop_constraint("uq_recibo_unidad_periodo", type_="unique")
