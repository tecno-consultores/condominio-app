"""Control de acceso peatonal/vehicular (pases QR firmados) y paquetería en garita (Hito 12)

Revision ID: 0005_hito12_accesos_paqueteria
Revises: 0004_hito11_cartas_consulta
Create Date: 2026-10-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005_hito12_accesos_paqueteria"
down_revision: str | None = "0004_hito11_cartas_consulta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pases_visita",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(length=36), nullable=False),
        sa.Column("unidad_id", sa.Integer(), nullable=False),
        sa.Column("creado_por_id", sa.Integer(), nullable=False),
        sa.Column("nombre_visitante", sa.String(length=120), nullable=False),
        sa.Column("cedula_visitante", sa.String(length=25), nullable=False),
        sa.Column("placa_vehiculo", sa.String(length=20), nullable=True),
        sa.Column("modalidad", sa.String(length=20), nullable=False),
        sa.Column("valido_desde", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valido_hasta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("usado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verificado_por_id", sa.Integer(), nullable=True),
        sa.Column("firma_hmac", sa.String(length=64), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["unidad_id"], ["unidades.id"]),
        sa.ForeignKeyConstraint(["creado_por_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["verificado_por_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti", name="uq_pase_visita_jti"),
    )
    op.create_index(op.f("ix_pases_visita_id"), "pases_visita", ["id"], unique=False)
    op.create_index(op.f("ix_pases_visita_jti"), "pases_visita", ["jti"], unique=True)
    op.create_index(op.f("ix_pases_visita_unidad_id"), "pases_visita", ["unidad_id"], unique=False)
    op.create_index(op.f("ix_pases_visita_estado"), "pases_visita", ["estado"], unique=False)

    op.create_table(
        "paquetes_recibidos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("unidad_id", sa.Integer(), nullable=False),
        sa.Column("recibido_por_id", sa.Integer(), nullable=False),
        sa.Column("empresa_envio", sa.String(length=60), nullable=False),
        sa.Column("descripcion", sa.String(length=200), nullable=False),
        sa.Column("url_foto_evidencia", sa.String(length=500), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("fecha_recepcion", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fecha_entrega", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retirado_por_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["unidad_id"], ["unidades.id"]),
        sa.ForeignKeyConstraint(["recibido_por_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["retirado_por_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_paquetes_recibidos_id"), "paquetes_recibidos", ["id"], unique=False)
    op.create_index(op.f("ix_paquetes_recibidos_unidad_id"), "paquetes_recibidos", ["unidad_id"], unique=False)
    op.create_index(op.f("ix_paquetes_recibidos_estado"), "paquetes_recibidos", ["estado"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_paquetes_recibidos_estado"), table_name="paquetes_recibidos")
    op.drop_index(op.f("ix_paquetes_recibidos_unidad_id"), table_name="paquetes_recibidos")
    op.drop_index(op.f("ix_paquetes_recibidos_id"), table_name="paquetes_recibidos")
    op.drop_table("paquetes_recibidos")

    op.drop_index(op.f("ix_pases_visita_estado"), table_name="pases_visita")
    op.drop_index(op.f("ix_pases_visita_unidad_id"), table_name="pases_visita")
    op.drop_index(op.f("ix_pases_visita_jti"), table_name="pases_visita")
    op.drop_index(op.f("ix_pases_visita_id"), table_name="pases_visita")
    op.drop_table("pases_visita")
