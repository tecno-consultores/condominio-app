"""Módulos operativos: incidencias, adhesiones, tareas, galería voceros, bitácora y comunicados (Hito 4)

Revision ID: 0002_hito4_operaciones
Revises: 0001_hito3_finanzas
Create Date: 2026-10-29

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002_hito4_operaciones"
down_revision: Union[str, None] = "0001_hito3_finanzas"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incidencias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_creador_id", sa.Integer(), nullable=False),
        sa.Column("area", sa.String(), nullable=False),
        sa.Column("descripcion", sa.String(), nullable=False),
        sa.Column("url_foto", sa.String(), nullable=True),
        sa.Column("estado", sa.String(), nullable=False),
        sa.Column("adhesiones_count", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_creador_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_incidencias_id"), "incidencias", ["id"], unique=False)
    op.create_index(op.f("ix_incidencias_usuario_creador_id"), "incidencias", ["usuario_creador_id"], unique=False)
    op.create_index(op.f("ix_incidencias_area"), "incidencias", ["area"], unique=False)
    op.create_index(op.f("ix_incidencias_estado"), "incidencias", ["estado"], unique=False)

    op.create_table(
        "incidencias_adhesiones",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("incidencia_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["incidencia_id"], ["incidencias.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("incidencia_id", "usuario_id", name="uq_incidencia_usuario_adhesion"),
    )
    op.create_index(op.f("ix_incidencias_adhesiones_id"), "incidencias_adhesiones", ["id"], unique=False)
    op.create_index(
        op.f("ix_incidencias_adhesiones_incidencia_id"), "incidencias_adhesiones", ["incidencia_id"], unique=False
    )
    op.create_index(
        op.f("ix_incidencias_adhesiones_usuario_id"), "incidencias_adhesiones", ["usuario_id"], unique=False
    )

    op.create_table(
        "plantillas_tareas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("area", sa.String(), nullable=False),
        sa.Column("frecuencia", sa.String(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_plantillas_tareas_id"), "plantillas_tareas", ["id"], unique=False)

    op.create_table(
        "tareas_diarias",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plantilla_id", sa.Integer(), nullable=True),
        sa.Column("incidencia_id", sa.Integer(), nullable=True),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("area", sa.String(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("completada", sa.Boolean(), nullable=False),
        sa.Column("url_evidencia", sa.String(), nullable=True),
        sa.Column("completada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["plantilla_id"], ["plantillas_tareas.id"]),
        sa.ForeignKeyConstraint(["incidencia_id"], ["incidencias.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tareas_diarias_id"), "tareas_diarias", ["id"], unique=False)
    op.create_index(op.f("ix_tareas_diarias_fecha"), "tareas_diarias", ["fecha"], unique=False)

    op.create_table(
        "fotos_voceros",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.Column("periodo", sa.String(length=7), nullable=False),
        sa.Column("area", sa.String(), nullable=False),
        sa.Column("comentario", sa.String(), nullable=False),
        sa.Column("url_foto", sa.String(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fotos_voceros_id"), "fotos_voceros", ["id"], unique=False)
    op.create_index(op.f("ix_fotos_voceros_usuario_id"), "fotos_voceros", ["usuario_id"], unique=False)
    op.create_index(op.f("ix_fotos_voceros_periodo"), "fotos_voceros", ["periodo"], unique=False)
    op.create_index(op.f("ix_fotos_voceros_area"), "fotos_voceros", ["area"], unique=False)

    op.create_table(
        "bitacora_actas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("hora", sa.String(), nullable=False),
        sa.Column("ubicacion", sa.String(), nullable=False),
        sa.Column("contenido", sa.String(), nullable=False),
        sa.Column("autor_id", sa.Integer(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["autor_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bitacora_actas_id"), "bitacora_actas", ["id"], unique=False)
    op.create_index(op.f("ix_bitacora_actas_fecha"), "bitacora_actas", ["fecha"], unique=False)

    op.create_table(
        "comunicados",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("titulo", sa.String(), nullable=False),
        sa.Column("contenido", sa.String(), nullable=False),
        sa.Column("enlace_externo", sa.String(), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("creado_en", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_comunicados_id"), "comunicados", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_comunicados_id"), table_name="comunicados")
    op.drop_table("comunicados")

    op.drop_index(op.f("ix_bitacora_actas_fecha"), table_name="bitacora_actas")
    op.drop_index(op.f("ix_bitacora_actas_id"), table_name="bitacora_actas")
    op.drop_table("bitacora_actas")

    op.drop_index(op.f("ix_fotos_voceros_area"), table_name="fotos_voceros")
    op.drop_index(op.f("ix_fotos_voceros_periodo"), table_name="fotos_voceros")
    op.drop_index(op.f("ix_fotos_voceros_usuario_id"), table_name="fotos_voceros")
    op.drop_index(op.f("ix_fotos_voceros_id"), table_name="fotos_voceros")
    op.drop_table("fotos_voceros")

    op.drop_index(op.f("ix_tareas_diarias_fecha"), table_name="tareas_diarias")
    op.drop_index(op.f("ix_tareas_diarias_id"), table_name="tareas_diarias")
    op.drop_table("tareas_diarias")

    op.drop_index(op.f("ix_plantillas_tareas_id"), table_name="plantillas_tareas")
    op.drop_table("plantillas_tareas")

    op.drop_index(op.f("ix_incidencias_adhesiones_usuario_id"), table_name="incidencias_adhesiones")
    op.drop_index(op.f("ix_incidencias_adhesiones_incidencia_id"), table_name="incidencias_adhesiones")
    op.drop_index(op.f("ix_incidencias_adhesiones_id"), table_name="incidencias_adhesiones")
    op.drop_table("incidencias_adhesiones")

    op.drop_index(op.f("ix_incidencias_estado"), table_name="incidencias")
    op.drop_index(op.f("ix_incidencias_area"), table_name="incidencias")
    op.drop_index(op.f("ix_incidencias_usuario_creador_id"), table_name="incidencias")
    op.drop_index(op.f("ix_incidencias_id"), table_name="incidencias")
    op.drop_table("incidencias")
