"""Restricciones compuestas por condominio_id, índices en FK, CheckConstraints y WORM PG17 (Hito 20.1)

Revision ID: 0010_rls_multitenant_worm_checks
Revises: 0009_hito18_tarea_diaria_unica
Create Date: 2026-11-17

"""

import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0010_rls_multitenant_worm_checks"
down_revision: str | None = "0009_hito18_tarea_diaria_unica"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ALL_TABLES: tuple[str, ...] = (
    "usuarios",
    "estructuras",
    "unidades",
    "contratos_ocupacion",
    "tasas_cambio",
    "recibos",
    "pagos_reportados",
    "egresos",
    "auditoria_recibos",
    "reportes_mensuales",
    "incidencias",
    "incidencias_adhesiones",
    "plantillas_tareas",
    "tareas_diarias",
    "fotos_voceros",
    "bitacora_actas",
    "comunicados",
    "fondos_condominio",
    "recibos_items",
    "certificados_solvencia",
    "consultas_comunitarias",
    "opciones_consulta",
    "votos_consulta",
    "pases_visita",
    "paquetes_recibidos",
    "areas_sociales",
    "reservas_areas_sociales",
)

_FK_INDEXES: tuple[tuple[str, str], ...] = (
    ("unidades", "estructura_id"),
    ("contratos_ocupacion", "usuario_id"),
    ("contratos_ocupacion", "unidad_id"),
    ("recibos", "unidad_id"),
    ("pagos_reportados", "recibo_id"),
    ("pagos_reportados", "usuario_id"),
    ("egresos", "incidencia_id"),
    ("auditoria_recibos", "pago_id"),
    ("auditoria_recibos", "usuario_id"),
    ("tareas_diarias", "plantilla_id"),
    ("tareas_diarias", "incidencia_id"),
    ("bitacora_actas", "autor_id"),
    ("certificados_solvencia", "emitido_por_id"),
    ("consultas_comunitarias", "creada_por_id"),
    ("consultas_comunitarias", "acta_bitacora_id"),
    ("pases_visita", "creado_por_id"),
    ("pases_visita", "verificado_por_id"),
    ("paquetes_recibidos", "recibido_por_id"),
    ("paquetes_recibidos", "retirado_por_id"),
    ("reservas_areas_sociales", "solicitante_id"),
    ("reservas_areas_sociales", "tarea_inspeccion_id"),
)

_UNIQUE_INDEX_REPLACEMENTS: tuple[tuple[str, str, str], ...] = (
    ("usuarios", "ix_usuarios_cedula", "cedula"),
    ("usuarios", "ix_usuarios_correo", "correo"),
    ("unidades", "ix_unidades_identificador", "identificador"),
    ("tasas_cambio", "ix_tasas_cambio_fecha", "fecha"),
    ("reportes_mensuales", "ix_reportes_mensuales_periodo", "periodo"),
    ("fondos_condominio", "ix_fondos_condominio_nombre", "nombre"),
    ("certificados_solvencia", "ix_certificados_solvencia_folio", "folio"),
)

_WORM_TABLES: tuple[str, ...] = ("auditoria_recibos", "votos_consulta")


def _apply_batch_upgrades() -> None:
    with op.batch_alter_table("usuarios") as batch_op:
        batch_op.create_unique_constraint("uq_usuario_condominio_cedula", ["condominio_id", "cedula"])
        batch_op.create_unique_constraint("uq_usuario_condominio_correo", ["condominio_id", "correo"])

    with op.batch_alter_table("unidades") as batch_op:
        batch_op.create_unique_constraint("uq_unidad_condominio_identificador", ["condominio_id", "identificador"])
        batch_op.create_check_constraint("ck_unidades_alicuota_rango", "alicuota >= 0 AND alicuota <= 100")
        batch_op.create_check_constraint("ck_unidades_credito_no_neg", "credito_disponible_usd >= 0")
        batch_op.create_check_constraint(
            "ck_unidades_cuota_fija_no_neg", "cuota_fija_usd IS NULL OR cuota_fija_usd >= 0"
        )

    with op.batch_alter_table("tasas_cambio") as batch_op:
        batch_op.create_unique_constraint("uq_tasa_cambio_condominio_fecha", ["condominio_id", "fecha"])
        batch_op.create_check_constraint("ck_tasas_cambio_positiva", "tasa_usd_ves > 0")

    with op.batch_alter_table("recibos") as batch_op:
        batch_op.drop_constraint("uq_recibo_unidad_periodo", type_="unique")
        batch_op.create_unique_constraint("uq_recibo_unidad_periodo", ["condominio_id", "unidad_id", "periodo"])
        batch_op.create_check_constraint("ck_recibos_monto_no_neg", "monto_usd >= 0")
        batch_op.create_check_constraint("ck_recibos_pagado_no_neg", "monto_pagado_usd >= 0")

    with op.batch_alter_table("pagos_reportados") as batch_op:
        batch_op.create_check_constraint("ck_pagos_montos_positivos", "monto > 0 AND monto_usd > 0 AND tasa_cambio > 0")

    with op.batch_alter_table("egresos") as batch_op:
        batch_op.create_check_constraint(
            "ck_egresos_montos_positivos", "monto > 0 AND monto_usd > 0 AND tasa_cambio > 0"
        )

    with op.batch_alter_table("reportes_mensuales") as batch_op:
        batch_op.create_unique_constraint("uq_reporte_mensual_condominio_periodo", ["condominio_id", "periodo"])

    with op.batch_alter_table("incidencias_adhesiones") as batch_op:
        batch_op.drop_constraint("uq_incidencia_usuario_adhesion", type_="unique")
        batch_op.create_unique_constraint(
            "uq_incidencia_usuario_adhesion", ["condominio_id", "incidencia_id", "usuario_id"]
        )

    with op.batch_alter_table("tareas_diarias") as batch_op:
        batch_op.drop_constraint("uq_tarea_diaria_plantilla_fecha", type_="unique")
        batch_op.create_unique_constraint("uq_tarea_diaria_plantilla_fecha", ["condominio_id", "plantilla_id", "fecha"])

    with op.batch_alter_table("fondos_condominio") as batch_op:
        batch_op.create_unique_constraint("uq_fondo_condominio_nombre", ["condominio_id", "nombre"])
        batch_op.create_check_constraint(
            "ck_fondos_recargo_rango", "porcentaje_recargo >= 0 AND porcentaje_recargo <= 100"
        )
        batch_op.create_check_constraint("ck_fondos_saldo_no_neg", "saldo_actual_usd >= 0")

    with op.batch_alter_table("recibos_items") as batch_op:
        batch_op.create_check_constraint(
            "ck_recibos_items_monto_valido",
            "(tipo_item = 'ABONO_CREDITO_PREVIO' AND monto_usd <= 0) OR monto_usd >= 0",
        )

    with op.batch_alter_table("certificados_solvencia") as batch_op:
        batch_op.create_unique_constraint("uq_certificado_solvencia_condominio_folio", ["condominio_id", "folio"])
        batch_op.create_check_constraint("ck_solvencia_deuda_no_neg", "deuda_verificada_usd >= 0")

    with op.batch_alter_table("consultas_comunitarias") as batch_op:
        batch_op.create_check_constraint(
            "ck_consultas_quorum_rango", "quorum_minimo_alicuota >= 0 AND quorum_minimo_alicuota <= 100"
        )

    with op.batch_alter_table("auditoria_recibos") as batch_op:
        batch_op.add_column(sa.Column("prev_hash", sa.String(length=64), server_default="0" * 64, nullable=False))
        batch_op.add_column(sa.Column("record_hash", sa.String(length=64), server_default="", nullable=False))

    with op.batch_alter_table("votos_consulta") as batch_op:
        batch_op.drop_constraint("uq_voto_consulta_unidad", type_="unique")
        batch_op.create_unique_constraint("uq_voto_consulta_unidad", ["condominio_id", "consulta_id", "unidad_id"])
        batch_op.create_check_constraint(
            "ck_votos_alicuota_rango", "alicuota_capturada >= 0 AND alicuota_capturada <= 100"
        )
        batch_op.add_column(sa.Column("prev_hash", sa.String(length=64), server_default="0" * 64, nullable=False))
        batch_op.add_column(sa.Column("record_hash", sa.String(length=64), server_default="", nullable=False))

    with op.batch_alter_table("areas_sociales") as batch_op:
        batch_op.drop_constraint("uq_area_social_nombre", type_="unique")
        batch_op.create_unique_constraint("uq_area_social_condominio_nombre", ["condominio_id", "nombre"])
        batch_op.create_check_constraint(
            "ck_areas_sociales_valores",
            "aforo_maximo > 0 AND costo_uso_usd >= 0 AND deposito_garantia_usd >= 0",
        )


def _apply_batch_downgrades() -> None:
    with op.batch_alter_table("areas_sociales") as batch_op:
        batch_op.drop_constraint("ck_areas_sociales_valores", type_="check")
        batch_op.drop_constraint("uq_area_social_condominio_nombre", type_="unique")
        batch_op.create_unique_constraint("uq_area_social_nombre", ["nombre"])

    with op.batch_alter_table("votos_consulta") as batch_op:
        batch_op.drop_column("record_hash")
        batch_op.drop_column("prev_hash")
        batch_op.drop_constraint("ck_votos_alicuota_rango", type_="check")
        batch_op.drop_constraint("uq_voto_consulta_unidad", type_="unique")
        batch_op.create_unique_constraint("uq_voto_consulta_unidad", ["consulta_id", "unidad_id"])

    with op.batch_alter_table("auditoria_recibos") as batch_op:
        batch_op.drop_column("record_hash")
        batch_op.drop_column("prev_hash")

    with op.batch_alter_table("consultas_comunitarias") as batch_op:
        batch_op.drop_constraint("ck_consultas_quorum_rango", type_="check")

    with op.batch_alter_table("certificados_solvencia") as batch_op:
        batch_op.drop_constraint("ck_solvencia_deuda_no_neg", type_="check")
        batch_op.drop_constraint("uq_certificado_solvencia_condominio_folio", type_="unique")

    with op.batch_alter_table("recibos_items") as batch_op:
        batch_op.drop_constraint("ck_recibos_items_monto_valido", type_="check")

    with op.batch_alter_table("fondos_condominio") as batch_op:
        batch_op.drop_constraint("ck_fondos_saldo_no_neg", type_="check")
        batch_op.drop_constraint("ck_fondos_recargo_rango", type_="check")
        batch_op.drop_constraint("uq_fondo_condominio_nombre", type_="unique")

    with op.batch_alter_table("tareas_diarias") as batch_op:
        batch_op.drop_constraint("uq_tarea_diaria_plantilla_fecha", type_="unique")
        batch_op.create_unique_constraint("uq_tarea_diaria_plantilla_fecha", ["plantilla_id", "fecha"])

    with op.batch_alter_table("incidencias_adhesiones") as batch_op:
        batch_op.drop_constraint("uq_incidencia_usuario_adhesion", type_="unique")
        batch_op.create_unique_constraint("uq_incidencia_usuario_adhesion", ["incidencia_id", "usuario_id"])

    with op.batch_alter_table("reportes_mensuales") as batch_op:
        batch_op.drop_constraint("uq_reporte_mensual_condominio_periodo", type_="unique")

    with op.batch_alter_table("egresos") as batch_op:
        batch_op.drop_constraint("ck_egresos_montos_positivos", type_="check")

    with op.batch_alter_table("pagos_reportados") as batch_op:
        batch_op.drop_constraint("ck_pagos_montos_positivos", type_="check")

    with op.batch_alter_table("recibos") as batch_op:
        batch_op.drop_constraint("ck_recibos_pagado_no_neg", type_="check")
        batch_op.drop_constraint("ck_recibos_monto_no_neg", type_="check")
        batch_op.drop_constraint("uq_recibo_unidad_periodo", type_="unique")
        batch_op.create_unique_constraint("uq_recibo_unidad_periodo", ["unidad_id", "periodo"])

    with op.batch_alter_table("tasas_cambio") as batch_op:
        batch_op.drop_constraint("ck_tasas_cambio_positiva", type_="check")
        batch_op.drop_constraint("uq_tasa_cambio_condominio_fecha", type_="unique")

    with op.batch_alter_table("unidades") as batch_op:
        batch_op.drop_constraint("ck_unidades_cuota_fija_no_neg", type_="check")
        batch_op.drop_constraint("ck_unidades_credito_no_neg", type_="check")
        batch_op.drop_constraint("ck_unidades_alicuota_rango", type_="check")
        batch_op.drop_constraint("uq_unidad_condominio_identificador", type_="unique")

    with op.batch_alter_table("usuarios") as batch_op:
        batch_op.drop_constraint("uq_usuario_condominio_correo", type_="unique")
        batch_op.drop_constraint("uq_usuario_condominio_cedula", type_="unique")


def _apply_pg_app_password() -> None:
    app_password = os.getenv("POSTGRES_APP_PASSWORD", "").strip()
    if not app_password:
        return
    conn = op.get_bind()
    conn.execute(sa.text("SELECT set_config('app.migration_app_pwd', :pwd, true)"), {"pwd": app_password})
    conn.execute(
        sa.text(
            "DO $$ BEGIN "
            "EXECUTE format('ALTER ROLE condominio_app WITH PASSWORD %L', current_setting('app.migration_app_pwd')); "
            "END $$;"
        )
    )


def _apply_sqlite_worm_triggers() -> None:
    for tbl in _WORM_TABLES:
        op.execute(
            f"CREATE TRIGGER IF NOT EXISTS trg_{tbl}_worm_no_update BEFORE UPDATE ON {tbl} "
            "BEGIN SELECT RAISE(ABORT, 'WORM: tabla inmutable'); END;"
        )
        op.execute(
            f"CREATE TRIGGER IF NOT EXISTS trg_{tbl}_worm_no_delete BEFORE DELETE ON {tbl} "
            "BEGIN SELECT RAISE(ABORT, 'WORM: tabla inmutable'); END;"
        )


def upgrade() -> None:
    is_pg = op.get_bind().dialect.name == "postgresql"

    for table_name in ALL_TABLES:
        op.drop_index(op.f(f"ix_{table_name}_id"), table_name=table_name)
    for table_name, index_name, _col in _UNIQUE_INDEX_REPLACEMENTS:
        op.drop_index(op.f(index_name), table_name=table_name)

    op.drop_index("uq_pagos_metodo_ref_activo", table_name="pagos_reportados")
    op.drop_index("uq_reserva_area_fecha_activa", table_name="reservas_areas_sociales")

    _apply_batch_upgrades()

    for table_name, index_name, col in _UNIQUE_INDEX_REPLACEMENTS:
        op.create_index(op.f(index_name), table_name, [col], unique=False)
    op.create_index(op.f("ix_areas_sociales_nombre"), "areas_sociales", ["nombre"], unique=False)

    op.create_index(
        "uq_pagos_metodo_ref_activo",
        "pagos_reportados",
        ["condominio_id", "metodo_pago", "numero_referencia"],
        unique=True,
        postgresql_where=sa.text("numero_referencia IS NOT NULL AND estado != 'RECHAZADO'"),
        sqlite_where=sa.text("numero_referencia IS NOT NULL AND estado != 'RECHAZADO'"),
    )
    op.create_index(
        "uq_reserva_area_fecha_activa",
        "reservas_areas_sociales",
        ["condominio_id", "area_id", "fecha_evento"],
        unique=True,
        postgresql_where=sa.text("estado != 'CANCELADA'"),
        sqlite_where=sa.text("estado != 'CANCELADA'"),
    )
    for table_name, col in _FK_INDEXES:
        op.create_index(op.f(f"ix_{table_name}_{col}"), table_name, [col], unique=False)

    if is_pg:
        op.execute("UPDATE auditoria_recibos SET record_hash = md5(id::text) WHERE record_hash = ''")
        op.execute("UPDATE votos_consulta SET record_hash = firma_hmac WHERE record_hash = ''")
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'condominio_app') THEN
                    CREATE ROLE condominio_app WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
                END IF;
                GRANT condominio_app_runtime TO condominio_app;
            END
            $$;
            """
        )
        _apply_pg_app_password()
        op.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO condominio_app_runtime"
        )
        op.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO condominio_app_runtime"
        )
        op.execute("REVOKE UPDATE, DELETE ON TABLE auditoria_recibos, votos_consulta FROM condominio_app_runtime")
    else:
        op.execute("UPDATE auditoria_recibos SET record_hash = printf('genesis-%d', id) WHERE record_hash = ''")
        op.execute("UPDATE votos_consulta SET record_hash = firma_hmac WHERE record_hash = ''")
        _apply_sqlite_worm_triggers()


def downgrade() -> None:
    is_pg = op.get_bind().dialect.name == "postgresql"

    if is_pg:
        op.execute("GRANT UPDATE, DELETE ON TABLE auditoria_recibos, votos_consulta TO condominio_app_runtime")
        op.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE USAGE, SELECT ON SEQUENCES FROM condominio_app_runtime"
        )
        op.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM condominio_app_runtime"
        )
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'condominio_app') THEN
                    REVOKE condominio_app_runtime FROM condominio_app;
                    IF CURRENT_USER <> 'condominio_app' THEN
                        DROP ROLE condominio_app;
                    END IF;
                END IF;
            END
            $$;
            """
        )
    else:
        for tbl in _WORM_TABLES:
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_worm_no_delete")
            op.execute(f"DROP TRIGGER IF EXISTS trg_{tbl}_worm_no_update")

    for table_name, col in reversed(_FK_INDEXES):
        op.drop_index(op.f(f"ix_{table_name}_{col}"), table_name=table_name)

    op.drop_index("uq_reserva_area_fecha_activa", table_name="reservas_areas_sociales")
    op.drop_index("uq_pagos_metodo_ref_activo", table_name="pagos_reportados")
    op.drop_index(op.f("ix_areas_sociales_nombre"), table_name="areas_sociales")
    for table_name, index_name, _col in _UNIQUE_INDEX_REPLACEMENTS:
        op.drop_index(op.f(index_name), table_name=table_name)

    _apply_batch_downgrades()

    op.create_index(
        "uq_reserva_area_fecha_activa",
        "reservas_areas_sociales",
        ["area_id", "fecha_evento"],
        unique=True,
        postgresql_where=sa.text("estado != 'CANCELADA'"),
        sqlite_where=sa.text("estado != 'CANCELADA'"),
    )
    op.create_index(
        "uq_pagos_metodo_ref_activo",
        "pagos_reportados",
        ["metodo_pago", "numero_referencia"],
        unique=True,
        postgresql_where=sa.text("numero_referencia IS NOT NULL AND estado != 'RECHAZADO'"),
        sqlite_where=sa.text("numero_referencia IS NOT NULL AND estado != 'RECHAZADO'"),
    )
    for table_name, index_name, col in _UNIQUE_INDEX_REPLACEMENTS:
        op.create_index(op.f(index_name), table_name, [col], unique=True)
    for table_name in reversed(ALL_TABLES):
        op.create_index(op.f(f"ix_{table_name}_id"), table_name, ["id"], unique=False)
