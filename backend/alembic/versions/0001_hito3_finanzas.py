"""Esquema inicial: usuarios, estructura, contratos y finanzas (Hito 1-3)

Revision ID: 0001_hito3_finanzas
Revises:
Create Date: 2026-10-12

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_hito3_finanzas"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("cedula", sa.String(), nullable=False),
        sa.Column("correo", sa.String(), nullable=False),
        sa.Column("telefono", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("es_activo", sa.Boolean(), nullable=False),
        sa.Column("rol", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_usuarios_id"), "usuarios", ["id"], unique=False)
    op.create_index(op.f("ix_usuarios_nombre"), "usuarios", ["nombre"], unique=False)
    op.create_index(op.f("ix_usuarios_cedula"), "usuarios", ["cedula"], unique=True)
    op.create_index(op.f("ix_usuarios_correo"), "usuarios", ["correo"], unique=True)

    op.create_table(
        "estructuras",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("nombre", sa.String(), nullable=False),
        sa.Column("tipo", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_estructuras_id"), "estructuras", ["id"], unique=False)

    op.create_table(
        "unidades",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("identificador", sa.String(), nullable=False),
        sa.Column("estructura_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["estructura_id"], ["estructuras.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_unidades_id"), "unidades", ["id"], unique=False)
    op.create_index(op.f("ix_unidades_identificador"), "unidades", ["identificador"], unique=True)

    op.create_table(
        "contratos_ocupacion",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("unidad_id", sa.Integer(), nullable=False),
        sa.Column("tipo_ocupante", sa.String(), nullable=False),
        sa.Column("es_activo", sa.Boolean(), nullable=False),
        sa.Column("fecha_inicio", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fecha_fin", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["unidad_id"], ["unidades.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_contratos_ocupacion_id"), "contratos_ocupacion", ["id"], unique=False)

    op.create_table(
        "tasas_cambio",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("tasa_usd_ves", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tasas_cambio_id"), "tasas_cambio", ["id"], unique=False)
    op.create_index(op.f("ix_tasas_cambio_fecha"), "tasas_cambio", ["fecha"], unique=True)

    op.create_table(
        "recibos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("unidad_id", sa.Integer(), nullable=False),
        sa.Column("periodo", sa.String(length=7), nullable=False),
        sa.Column("monto_usd", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("monto_pagado_usd", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("bloqueado", sa.Boolean(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["unidad_id"], ["unidades.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recibos_id"), "recibos", ["id"], unique=False)
    op.create_index(op.f("ix_recibos_periodo"), "recibos", ["periodo"], unique=False)

    op.create_table(
        "pagos_reportados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recibo_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("monto", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("monto_usd", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tasa_cambio", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("metodo_pago", sa.String(), nullable=False),
        sa.Column("numero_referencia", sa.String(), nullable=True),
        sa.Column("url_comprobante", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recibo_id"], ["recibos.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pagos_reportados_id"), "pagos_reportados", ["id"], unique=False)

    op.create_table(
        "egresos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("periodo", sa.String(length=7), nullable=False),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=False),
        sa.Column("monto", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("moneda", sa.String(length=3), nullable=False),
        sa.Column("monto_usd", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tasa_cambio", sa.Numeric(precision=14, scale=4), nullable=False),
        sa.Column("url_factura", sa.String(), nullable=True),
        sa.Column("bloqueado", sa.Boolean(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_egresos_id"), "egresos", ["id"], unique=False)
    op.create_index(op.f("ix_egresos_periodo"), "egresos", ["periodo"], unique=False)

    op.create_table(
        "auditoria_recibos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("recibo_id", sa.Integer(), nullable=False),
        sa.Column("pago_id", sa.Integer(), nullable=True),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("estado_viejo", sa.String(), nullable=False),
        sa.Column("estado_nuevo", sa.String(), nullable=False),
        sa.Column("motivo", sa.String(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recibo_id"], ["recibos.id"]),
        sa.ForeignKeyConstraint(["pago_id"], ["pagos_reportados.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auditoria_recibos_id"), "auditoria_recibos", ["id"], unique=False)
    op.create_index(op.f("ix_auditoria_recibos_recibo_id"), "auditoria_recibos", ["recibo_id"], unique=False)

    op.create_table(
        "reportes_mensuales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("periodo", sa.String(length=7), nullable=False),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("url_pdf", sa.String(), nullable=True),
        sa.Column("cerrado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reportes_mensuales_id"), "reportes_mensuales", ["id"], unique=False)
    op.create_index(op.f("ix_reportes_mensuales_periodo"), "reportes_mensuales", ["periodo"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_reportes_mensuales_periodo"), table_name="reportes_mensuales")
    op.drop_index(op.f("ix_reportes_mensuales_id"), table_name="reportes_mensuales")
    op.drop_table("reportes_mensuales")

    op.drop_index(op.f("ix_auditoria_recibos_recibo_id"), table_name="auditoria_recibos")
    op.drop_index(op.f("ix_auditoria_recibos_id"), table_name="auditoria_recibos")
    op.drop_table("auditoria_recibos")

    op.drop_index(op.f("ix_egresos_periodo"), table_name="egresos")
    op.drop_index(op.f("ix_egresos_id"), table_name="egresos")
    op.drop_table("egresos")

    op.drop_index(op.f("ix_pagos_reportados_id"), table_name="pagos_reportados")
    op.drop_table("pagos_reportados")

    op.drop_index(op.f("ix_recibos_periodo"), table_name="recibos")
    op.drop_index(op.f("ix_recibos_id"), table_name="recibos")
    op.drop_table("recibos")

    op.drop_index(op.f("ix_tasas_cambio_fecha"), table_name="tasas_cambio")
    op.drop_index(op.f("ix_tasas_cambio_id"), table_name="tasas_cambio")
    op.drop_table("tasas_cambio")

    op.drop_index(op.f("ix_contratos_ocupacion_id"), table_name="contratos_ocupacion")
    op.drop_table("contratos_ocupacion")

    op.drop_index(op.f("ix_unidades_identificador"), table_name="unidades")
    op.drop_index(op.f("ix_unidades_id"), table_name="unidades")
    op.drop_table("unidades")

    op.drop_index(op.f("ix_estructuras_id"), table_name="estructuras")
    op.drop_table("estructuras")

    op.drop_index(op.f("ix_usuarios_correo"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_cedula"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_nombre"), table_name="usuarios")
    op.drop_index(op.f("ix_usuarios_id"), table_name="usuarios")
    op.drop_table("usuarios")
