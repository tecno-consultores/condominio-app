"""Integridad de reservas, JTI anti-replay y políticas RLS multi-tenant PG17 (Hito 17.4)

Revision ID: 0008_hito17_integridad_y_rls
Revises: 0007_hito17_unicidad_finanzas
Create Date: 2026-11-13

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0008_hito17_integridad_y_rls"
down_revision: str | None = "0007_hito17_unicidad_finanzas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES: tuple[str, ...] = (
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

_POLICY_EXPR = (
    "COALESCE(current_setting('app.is_superadmin', true), 'false') = 'true' "
    "OR condominio_id = NULLIF(current_setting('app.current_tenant_id', true), '')::integer"
)


def _add_jti_column_with_backfill(table_name: str, is_pg: bool) -> None:
    op.add_column(table_name, sa.Column("jti", sa.String(length=36), nullable=True))
    if is_pg:
        op.execute(f"UPDATE {table_name} SET jti = gen_random_uuid()::text WHERE jti IS NULL")
    else:
        op.execute(f"UPDATE {table_name} SET jti = lower(hex(randomblob(16))) WHERE jti IS NULL")
    with op.batch_alter_table(table_name) as batch_op:
        batch_op.alter_column("jti", existing_type=sa.String(length=36), nullable=False)
    op.create_index(f"ix_{table_name}_jti", table_name, ["jti"], unique=True)


def upgrade() -> None:
    dialect_name = op.get_bind().dialect.name
    is_pg = dialect_name == "postgresql"

    for table_name in TENANT_TABLES:
        op.add_column(
            table_name,
            sa.Column("condominio_id", sa.Integer(), server_default="1", nullable=False),
        )
        op.create_index(f"ix_{table_name}_condominio_id", table_name, ["condominio_id"], unique=False)

    _add_jti_column_with_backfill("certificados_solvencia", is_pg)
    _add_jti_column_with_backfill("votos_consulta", is_pg)

    with op.batch_alter_table("reservas_areas_sociales") as batch_op:
        batch_op.drop_constraint("uq_reserva_area_fecha", type_="unique")

    op.create_index(
        "uq_reserva_area_fecha_activa",
        "reservas_areas_sociales",
        ["area_id", "fecha_evento"],
        unique=True,
        postgresql_where=sa.text("estado != 'CANCELADA'"),
        sqlite_where=sa.text("estado != 'CANCELADA'"),
    )

    if is_pg:
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'condominio_app_runtime') THEN
                    CREATE ROLE condominio_app_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
                END IF;
            END
            $$;
            """
        )
        op.execute("GRANT USAGE ON SCHEMA public TO condominio_app_runtime")
        op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO condominio_app_runtime")
        op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO condominio_app_runtime")
        op.execute("GRANT condominio_app_runtime TO CURRENT_USER")

        for table_name in TENANT_TABLES:
            op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
            op.execute(
                f"CREATE POLICY tenant_isolation_policy ON {table_name} AS PERMISSIVE FOR ALL "
                f"USING ({_POLICY_EXPR}) WITH CHECK ({_POLICY_EXPR})"
            )


def downgrade() -> None:
    is_pg = op.get_bind().dialect.name == "postgresql"

    if is_pg:
        for table_name in reversed(TENANT_TABLES):
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {table_name}")
            op.execute(f"ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY")
            op.execute(f"ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY")
        op.execute("REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM condominio_app_runtime")
        op.execute("REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM condominio_app_runtime")
        op.execute("REVOKE USAGE ON SCHEMA public FROM condominio_app_runtime")
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'condominio_app_runtime') THEN
                    REVOKE condominio_app_runtime FROM CURRENT_USER;
                    DROP ROLE condominio_app_runtime;
                END IF;
            END
            $$;
            """
        )

    op.drop_index("uq_reserva_area_fecha_activa", table_name="reservas_areas_sociales")
    with op.batch_alter_table("reservas_areas_sociales") as batch_op:
        batch_op.create_unique_constraint("uq_reserva_area_fecha", ["area_id", "fecha_evento"])

    for table_name in ("votos_consulta", "certificados_solvencia"):
        op.drop_index(f"ix_{table_name}_jti", table_name=table_name)
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("jti")

    for table_name in reversed(TENANT_TABLES):
        op.drop_index(f"ix_{table_name}_condominio_id", table_name=table_name)
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_column("condominio_id")
