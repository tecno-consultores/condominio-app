"""Reserva de áreas sociales vinculada a solvencia e inspección post-evento (Hito 13)

Revision ID: 0006_hito13_reservas_areas
Revises: 0005_hito12_accesos_paqueteria
Create Date: 2026-10-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0006_hito13_reservas_areas"
down_revision: str | None = "0005_hito12_accesos_paqueteria"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "areas_sociales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("aforo_maximo", sa.Integer(), nullable=False),
        sa.Column("costo_uso_usd", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("deposito_garantia_usd", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("requiere_solvencia_estricta", sa.Boolean(), nullable=False),
        sa.Column("es_activa", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre", name="uq_area_social_nombre"),
    )
    op.create_index(op.f("ix_areas_sociales_id"), "areas_sociales", ["id"], unique=False)

    op.create_table(
        "reservas_areas_sociales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=False),
        sa.Column("unidad_id", sa.Integer(), nullable=False),
        sa.Column("solicitante_id", sa.Integer(), nullable=False),
        sa.Column("fecha_evento", sa.Date(), nullable=False),
        sa.Column("motivo_evento", sa.String(length=160), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("tarea_inspeccion_id", sa.Integer(), nullable=True),
        sa.Column("observaciones_inspeccion", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["area_id"], ["areas_sociales.id"]),
        sa.ForeignKeyConstraint(["unidad_id"], ["unidades.id"]),
        sa.ForeignKeyConstraint(["solicitante_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["tarea_inspeccion_id"], ["tareas_diarias.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("area_id", "fecha_evento", name="uq_reserva_area_fecha"),
    )
    op.create_index(op.f("ix_reservas_areas_sociales_id"), "reservas_areas_sociales", ["id"], unique=False)
    op.create_index(op.f("ix_reservas_areas_sociales_area_id"), "reservas_areas_sociales", ["area_id"], unique=False)
    op.create_index(
        op.f("ix_reservas_areas_sociales_unidad_id"), "reservas_areas_sociales", ["unidad_id"], unique=False
    )
    op.create_index(
        op.f("ix_reservas_areas_sociales_fecha_evento"), "reservas_areas_sociales", ["fecha_evento"], unique=False
    )
    op.create_index(op.f("ix_reservas_areas_sociales_estado"), "reservas_areas_sociales", ["estado"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_reservas_areas_sociales_estado"), table_name="reservas_areas_sociales")
    op.drop_index(op.f("ix_reservas_areas_sociales_fecha_evento"), table_name="reservas_areas_sociales")
    op.drop_index(op.f("ix_reservas_areas_sociales_unidad_id"), table_name="reservas_areas_sociales")
    op.drop_index(op.f("ix_reservas_areas_sociales_area_id"), table_name="reservas_areas_sociales")
    op.drop_index(op.f("ix_reservas_areas_sociales_id"), table_name="reservas_areas_sociales")
    op.drop_table("reservas_areas_sociales")

    op.drop_index(op.f("ix_areas_sociales_id"), table_name="areas_sociales")
    op.drop_table("areas_sociales")
