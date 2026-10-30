"""Cartas consulta (Art. 23 LPH), asambleas y voto criptográfico ponderado por alícuota (Hito 11)

Revision ID: 0004_hito11_cartas_consulta
Revises: 0003_hito10_alicuotas_solvencia
Create Date: 2026-10-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_hito11_cartas_consulta"
down_revision: str | None = "0003_hito10_alicuotas_solvencia"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "contratos_ocupacion",
        sa.Column("puede_votar_asamblea", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )

    op.create_table(
        "consultas_comunitarias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("descripcion_legal", sa.String(), nullable=False),
        sa.Column("tipo_consulta", sa.String(length=30), nullable=False),
        sa.Column("regla_quorum", sa.String(length=30), nullable=False),
        sa.Column("quorum_minimo_alicuota", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("fecha_apertura", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("creada_por_id", sa.Integer(), nullable=False),
        sa.Column("acta_bitacora_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["creada_por_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["acta_bitacora_id"], ["bitacora_actas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_consultas_comunitarias_id"), "consultas_comunitarias", ["id"], unique=False)
    op.create_index(op.f("ix_consultas_comunitarias_estado"), "consultas_comunitarias", ["estado"], unique=False)

    op.create_table(
        "opciones_consulta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("consulta_id", sa.Integer(), nullable=False),
        sa.Column("etiqueta", sa.String(length=120), nullable=False),
        sa.Column("es_opcion_aprobatoria", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["consulta_id"], ["consultas_comunitarias.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_opciones_consulta_id"), "opciones_consulta", ["id"], unique=False)
    op.create_index(op.f("ix_opciones_consulta_consulta_id"), "opciones_consulta", ["consulta_id"], unique=False)

    op.create_table(
        "votos_consulta",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("consulta_id", sa.Integer(), nullable=False),
        sa.Column("unidad_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("opcion_id", sa.Integer(), nullable=False),
        sa.Column("alicuota_capturada", sa.Numeric(precision=7, scale=4), nullable=False),
        sa.Column("fecha_voto", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("firma_hmac", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["consulta_id"], ["consultas_comunitarias.id"]),
        sa.ForeignKeyConstraint(["unidad_id"], ["unidades.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.ForeignKeyConstraint(["opcion_id"], ["opciones_consulta.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consulta_id", "unidad_id", name="uq_voto_consulta_unidad"),
        sa.UniqueConstraint("firma_hmac", name="uq_voto_consulta_firma_hmac"),
    )
    op.create_index(op.f("ix_votos_consulta_id"), "votos_consulta", ["id"], unique=False)
    op.create_index(op.f("ix_votos_consulta_consulta_id"), "votos_consulta", ["consulta_id"], unique=False)
    op.create_index(op.f("ix_votos_consulta_unidad_id"), "votos_consulta", ["unidad_id"], unique=False)
    op.create_index(op.f("ix_votos_consulta_usuario_id"), "votos_consulta", ["usuario_id"], unique=False)
    op.create_index(op.f("ix_votos_consulta_opcion_id"), "votos_consulta", ["opcion_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_votos_consulta_opcion_id"), table_name="votos_consulta")
    op.drop_index(op.f("ix_votos_consulta_usuario_id"), table_name="votos_consulta")
    op.drop_index(op.f("ix_votos_consulta_unidad_id"), table_name="votos_consulta")
    op.drop_index(op.f("ix_votos_consulta_consulta_id"), table_name="votos_consulta")
    op.drop_index(op.f("ix_votos_consulta_id"), table_name="votos_consulta")
    op.drop_table("votos_consulta")

    op.drop_index(op.f("ix_opciones_consulta_consulta_id"), table_name="opciones_consulta")
    op.drop_index(op.f("ix_opciones_consulta_id"), table_name="opciones_consulta")
    op.drop_table("opciones_consulta")

    op.drop_index(op.f("ix_consultas_comunitarias_estado"), table_name="consultas_comunitarias")
    op.drop_index(op.f("ix_consultas_comunitarias_id"), table_name="consultas_comunitarias")
    op.drop_table("consultas_comunitarias")

    op.drop_column("contratos_ocupacion", "puede_votar_asamblea")
