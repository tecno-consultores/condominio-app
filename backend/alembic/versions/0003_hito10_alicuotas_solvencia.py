"""Alícuotas, cuota fija, saldo a favor, fondos patrimoniales, desglose de recibos y solvencia digital (Hito 10)

Revision ID: 0003_hito10_alicuotas_solvencia
Revises: 0002_hito4_operaciones
Create Date: 2026-10-30

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0003_hito10_alicuotas_solvencia"
down_revision: Union[str, None] = "0002_hito4_operaciones"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "unidades",
        sa.Column("alicuota", sa.Numeric(precision=7, scale=4), server_default="0.0000", nullable=False),
    )
    op.add_column(
        "unidades",
        sa.Column("cuota_fija_usd", sa.Numeric(precision=12, scale=2), nullable=True),
    )
    op.add_column(
        "unidades",
        sa.Column("credito_disponible_usd", sa.Numeric(precision=12, scale=2), server_default="0.00", nullable=False),
    )

    op.add_column(
        "egresos",
        sa.Column("incidencia_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "egresos",
        sa.Column("es_gasto_comun", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_foreign_key(
        "fk_egresos_incidencia_id_incidencias",
        "egresos",
        "incidencias",
        ["incidencia_id"],
        ["id"],
    )

    op.create_table(
        "fondos_condominio",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("porcentaje_recargo", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("saldo_actual_usd", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("es_activo", sa.Boolean(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fondos_condominio_id"), "fondos_condominio", ["id"], unique=False)
    op.create_index(op.f("ix_fondos_condominio_nombre"), "fondos_condominio", ["nombre"], unique=True)

    op.create_table(
        "recibos_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recibo_id", sa.Integer(), nullable=False),
        sa.Column("tipo_item", sa.String(length=30), nullable=False),
        sa.Column("descripcion", sa.String(length=255), nullable=False),
        sa.Column("monto_usd", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recibo_id"], ["recibos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recibos_items_id"), "recibos_items", ["id"], unique=False)
    op.create_index(op.f("ix_recibos_items_recibo_id"), "recibos_items", ["recibo_id"], unique=False)

    op.create_table(
        "certificados_solvencia",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("folio", sa.String(length=40), nullable=False),
        sa.Column("unidad_id", sa.Integer(), nullable=False),
        sa.Column("emitido_por_id", sa.Integer(), nullable=False),
        sa.Column("fecha_emision", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("deuda_verificada_usd", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("firma_hmac", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["unidad_id"], ["unidades.id"]),
        sa.ForeignKeyConstraint(["emitido_por_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_certificados_solvencia_id"), "certificados_solvencia", ["id"], unique=False)
    op.create_index(op.f("ix_certificados_solvencia_folio"), "certificados_solvencia", ["folio"], unique=True)
    op.create_index(op.f("ix_certificados_solvencia_unidad_id"), "certificados_solvencia", ["unidad_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_certificados_solvencia_unidad_id"), table_name="certificados_solvencia")
    op.drop_index(op.f("ix_certificados_solvencia_folio"), table_name="certificados_solvencia")
    op.drop_index(op.f("ix_certificados_solvencia_id"), table_name="certificados_solvencia")
    op.drop_table("certificados_solvencia")

    op.drop_index(op.f("ix_recibos_items_recibo_id"), table_name="recibos_items")
    op.drop_index(op.f("ix_recibos_items_id"), table_name="recibos_items")
    op.drop_table("recibos_items")

    op.drop_index(op.f("ix_fondos_condominio_nombre"), table_name="fondos_condominio")
    op.drop_index(op.f("ix_fondos_condominio_id"), table_name="fondos_condominio")
    op.drop_table("fondos_condominio")

    op.drop_constraint("fk_egresos_incidencia_id_incidencias", "egresos", type_="foreignkey")
    op.drop_column("egresos", "es_gasto_comun")
    op.drop_column("egresos", "incidencia_id")

    op.drop_column("unidades", "credito_disponible_usd")
    op.drop_column("unidades", "cuota_fija_usd")
    op.drop_column("unidades", "alicuota")
