# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
"""Pruebas unitarias e integración PostgreSQL 17 RLS para el CLI de bootstrap Día 0."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.future import select

from src import bootstrap as bootstrap_mod
from src.bootstrap import BootstrapConfig, bootstrap_initial_admin, main
from src.database import Base
from src.models import ContratoOcupacion, Estructura, Unidad, Usuario
from src.security import get_password_hash, verify_password


async def _crear_motor_sqlite(tmp_path: Path, db_name: str = "bootstrap.db") -> tuple[AsyncEngine, Any]:
    db_file = tmp_path / db_name
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


def test_cli_tty_anti_hang_sin_argumentos(capsys: pytest.CaptureFixture[str]) -> None:
    """Sin argumentos imprime ayuda inmediatamente y retorna 0 (QA-CLI-TTY-01)."""
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "python -m src.bootstrap" in captured.out


def test_cli_from_env_omitido_cuando_no_hay_correo(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("BOOTSTRAP_ADMIN_CORREO", raising=False)
    assert main(["--from-env"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "skipped"


def test_cli_fail_fast_en_produccion_con_secret_inseguro(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "qa-blueprint-11x-secret-key-super-secure-32bytes")
    code = main(["--correo", "presidente@condominio.test", "--password", "ClaveRobusta123!"])
    assert code == 1
    assert "Error de bootstrap" in capsys.readouterr().err


@pytest.mark.parametrize(
    "config_kwargs, expected_msg",
    [
        ({"condominio_id": 0}, "condominio_id"),
        ({"nombre": "   "}, "obligatorios"),
        ({"correo": "correo-invalido"}, "correo electrónico inválido"),
        ({"password": "corta"}, "al menos 12"),
        ({"password": "CAMBIAR_PLACEHOLDER_GENERAR_CON_OPENSSL"}, "placeholder"),
        ({"password": "admin1234567"}, "placeholder"),
        ({"rol": "FANTASMA"}, "Rol de bootstrap"),
        ({"estructura_tipo": "RANCHO"}, "Tipo de estructura"),
    ],
)
@pytest.mark.asyncio
async def test_bootstrap_rechaza_parametros_invalidos(
    tmp_path: Path,
    config_kwargs: dict[str, Any],
    expected_msg: str,
) -> None:
    engine, factory = await _crear_motor_sqlite(tmp_path, "invalid.db")
    try:
        base_kwargs: dict[str, Any] = {
            "correo": "admin@condominio.test",
            "password": "ClaveSeguraBootstrap2026!",
        }
        base_kwargs.update(config_kwargs)
        with pytest.raises(ValueError, match=expected_msg):
            await bootstrap_initial_admin(
                BootstrapConfig(**base_kwargs),
                session_factory=factory,
                target_engine=engine,
            )
    finally:
        await engine.dispose()


def test_from_env_rechaza_condominio_id_no_numerico(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", "no-entero")
    with pytest.raises(ValueError, match="entero positivo"):
        BootstrapConfig.from_env()


@pytest.mark.asyncio
async def test_bootstrap_creacion_idempotencia_unidad_y_actualizacion(tmp_path: Path) -> None:
    engine, factory = await _crear_motor_sqlite(tmp_path, "idempotente.db")
    try:
        cfg = BootstrapConfig(
            condominio_id=1,
            nombre="María Presidenta",
            cedula="V-10203040",
            correo="Maria.Presidenta@Condominio.Test",
            telefono="+584121234567",
            password="ClaveSeguraBootstrap2026!",
            rol="PRESIDENTE",
            estructura_nombre="Torre Ávila",
            estructura_tipo="TORRE",
            unidad_inicial="A-101",
        )
        res1 = await bootstrap_initial_admin(cfg, session_factory=factory, target_engine=engine)
        assert res1.status == "created"
        assert res1.correo == "maria.presidenta@condominio.test"
        assert res1.rol == "PRESIDENTE"
        assert res1.unidad_id is not None

        res2 = await bootstrap_initial_admin(cfg, session_factory=factory, target_engine=engine)
        assert res2.status == "unchanged"
        assert res2.usuario_id == res1.usuario_id
        assert res2.unidad_id == res1.unidad_id

        cfg_rotado = BootstrapConfig(
            condominio_id=1,
            nombre="María Presidenta Actualizada",
            cedula="V-10203040",
            correo="maria.presidenta@condominio.test",
            telefono="+584129998877",
            password="NuevaClaveSeguraBootstrap2026!",
            rol="PRESIDENTE",
            estructura_nombre="Torre Ávila",
            estructura_tipo="TORRE",
            unidad_inicial="A-101",
            allow_update_existing=True,
        )
        res3 = await bootstrap_initial_admin(cfg_rotado, session_factory=factory, target_engine=engine)
        assert res3.status == "updated"

        async with factory() as session:
            user = (await session.execute(select(Usuario).where(Usuario.id == res1.usuario_id))).scalars().one()
            assert user.nombre == "María Presidenta Actualizada"
            assert user.telefono == "+584129998877"
            assert verify_password("NuevaClaveSeguraBootstrap2026!", user.password_hash)
            contratos = (await session.execute(select(ContratoOcupacion))).scalars().all()
            assert len(contratos) == 1
            assert contratos[0].es_activo is True
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_bootstrap_promueve_fantasma_cierra_contrato_previo_y_detecta_conflictos(tmp_path: Path) -> None:
    engine, factory = await _crear_motor_sqlite(tmp_path, "promocion.db")
    try:
        async with factory() as session:
            est = Estructura(condominio_id=1, nombre="Torre Norte", tipo="TORRE")
            session.add(est)
            await session.flush()
            u1 = Unidad(condominio_id=1, identificador="N-01", estructura_id=est.id)
            u2 = Unidad(condominio_id=1, identificador="N-02", estructura_id=est.id)
            u_otro_tenant = Unidad(condominio_id=2, identificador="X-99", estructura_id=est.id)
            fantasma = Usuario(
                condominio_id=1,
                nombre="Vecino Fantasma",
                cedula="V-11112222",
                correo="fantasma@condominio.test",
                telefono="+584140001111",
                password_hash=get_password_hash("ClaveInicialBootstrap1!"),
                es_activo=False,
                rol="FANTASMA",
            )
            otro = Usuario(
                condominio_id=1,
                nombre="Otro Vecino",
                cedula="V-33334444",
                correo="otro@condominio.test",
                telefono="+584140002222",
                password_hash=get_password_hash("ClaveOtroBootstrap1!"),
                es_activo=True,
                rol="PROPIETARIO",
            )
            session.add_all([u1, u2, u_otro_tenant, fantasma, otro])
            await session.flush()
            session.add(
                ContratoOcupacion(
                    condominio_id=1,
                    usuario_id=fantasma.id,
                    unidad_id=u1.id,
                    tipo_ocupante="PROPIETARIO",
                    es_activo=True,
                )
            )
            await session.commit()

        cfg_promocion = BootstrapConfig(
            condominio_id=1,
            nombre="Vecino Fantasma",
            cedula="V-11112222",
            correo="fantasma@condominio.test",
            telefono="+584140001111",
            password="ClaveInicialBootstrap1!",
            rol="TESORERO",
            unidad_inicial="N-02",
        )
        res = await bootstrap_initial_admin(cfg_promocion, session_factory=factory, target_engine=engine)
        assert res.status == "updated"
        assert res.rol == "TESORERO"

        async with factory() as session:
            contratos = (
                (
                    await session.execute(
                        select(ContratoOcupacion)
                        .where(ContratoOcupacion.usuario_id == res.usuario_id)
                        .order_by(ContratoOcupacion.id.asc())
                    )
                )
                .scalars()
                .all()
            )
            assert len(contratos) == 2
            assert contratos[0].es_activo is False and contratos[0].fecha_fin is not None
            assert contratos[1].es_activo is True

        with pytest.raises(ValueError, match="Conflicto de identidad"):
            await bootstrap_initial_admin(
                BootstrapConfig(
                    condominio_id=1,
                    correo="fantasma@condominio.test",
                    cedula="V-33334444",
                    password="ClaveInicialBootstrap1!",
                ),
                session_factory=factory,
                target_engine=engine,
            )

        with pytest.raises(ValueError, match="otro condominio_id"):
            await bootstrap_initial_admin(
                BootstrapConfig(
                    condominio_id=1,
                    correo="fantasma@condominio.test",
                    cedula="V-11112222",
                    password="ClaveInicialBootstrap1!",
                    unidad_inicial="X-99",
                ),
                session_factory=factory,
                target_engine=engine,
            )
    finally:
        await engine.dispose()


def test_cli_ejecuta_con_flags_y_sqlite_archivo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_file = tmp_path / "cli_run.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    test_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(bootstrap_mod, "engine", test_engine)
    monkeypatch.setattr(bootstrap_mod, "AsyncSessionLocal", test_factory)
    monkeypatch.setenv("APP_ENV", "qa_unit")

    exit_code = main(
        [
            "--correo",
            "cli.presi@condominio.test",
            "--password",
            "ClaveCliSegura2026!",
            "--cedula",
            "V-99887766",
            "--nombre",
            "Presidente CLI",
            "--unidad-inicial",
            "PH-1",
            "--estructura-nombre",
            "Torre Central",
        ]
    )
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "created"
    assert payload["rol"] == "PRESIDENTE"
    assert payload["unidad_id"] is not None

    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", "1")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_CORREO", "cli.presi@condominio.test")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ClaveCliRotada2026!")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_CEDULA", "V-99887766")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_NOMBRE", "Presidente CLI Env")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_TELEFONO", "+584129990000")
    assert main(["--from-env", "--allow-update-existing"]) == 0
    payload_env = json.loads(capsys.readouterr().out)
    assert payload_env["status"] == "updated"


@pytest.mark.asyncio
async def test_bootstrap_aislamiento_rls_postgresql_17() -> None:
    """Valida inserción e invisibilidad cross-tenant del usuario bootstrap bajo RLS PG17."""
    pg_url = os.getenv("POSTGRES_TEST_URL")
    if not pg_url:
        pytest.skip("POSTGRES_TEST_URL no definido; prueba RLS omitida fuera de qa-parity/CI.")

    engine = create_async_engine(pg_url, echo=False)
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    sufijo = uuid.uuid4().hex[:8]
    email = f"rls.bootstrap.{sufijo}@condominio.test"
    cedula = f"V-RLS-{sufijo}"
    created_id: int | None = None

    try:
        res = await bootstrap_initial_admin(
            BootstrapConfig(
                condominio_id=2,
                nombre="Admin Tenant Dos",
                cedula=cedula,
                correo=email,
                telefono="+584125550202",
                password="ClaveRlsBootstrap2026!",
                rol="PRESIDENTE",
            ),
            session_factory=factory,
            target_engine=engine,
        )
        assert res.status == "created"
        created_id = res.usuario_id

        async with factory() as s1:
            s1.sync_session.info["tenant_id"] = "1"
            s1.sync_session.info["is_superadmin"] = False
            await s1.execute(text("SET LOCAL ROLE condominio_app_runtime"))
            visto_t1 = (await s1.execute(select(Usuario).where(Usuario.id == created_id))).scalars().first()
            assert visto_t1 is None
            await s1.rollback()

        async with factory() as s2:
            s2.sync_session.info["tenant_id"] = "2"
            s2.sync_session.info["is_superadmin"] = False
            await s2.execute(text("SET LOCAL ROLE condominio_app_runtime"))
            visto_t2 = (await s2.execute(select(Usuario).where(Usuario.id == created_id))).scalars().first()
            assert visto_t2 is not None
            assert visto_t2.rol == "PRESIDENTE"
            await s2.rollback()
    finally:
        if created_id is not None:
            async with factory() as sclean:
                sclean.sync_session.info["is_superadmin"] = True
                user_obj = await sclean.get(Usuario, created_id)
                if user_obj is not None:
                    await sclean.delete(user_obj)
                await sclean.commit()
        await engine.dispose()


@pytest.fixture(autouse=True)
def _acelerar_pbkdf2_wiring_bootstrap(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Acelera tests de cableado SQLite/CLI reduciendo iteraciones PBKDF2 excepto en el test real de 100k."""
    if request.node.name != "test_bootstrap_pbkdf2_iteraciones_reales":
        monkeypatch.setattr("src.security.PBKDF2_ITERATIONS", 1)


def test_bootstrap_pbkdf2_iteraciones_reales(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Garantiza que sin parche el bootstrap aplica PBKDF2 completo (100_000 iteraciones)."""
    import asyncio
    import hashlib

    from sqlalchemy import select as _select

    from src.models import Usuario as _Usuario
    from src.security import PBKDF2_ITERATIONS
    from src.security import verify_password as _verify

    iteraciones_observadas: list[int] = []
    pbkdf2_real = hashlib.pbkdf2_hmac

    def _spy_pbkdf2(hash_name: str, password: bytes, salt: bytes, iterations: int, dklen: int | None = None) -> bytes:
        iteraciones_observadas.append(iterations)
        return pbkdf2_real(hash_name, password, salt, 1, dklen)

    monkeypatch.setattr(hashlib, "pbkdf2_hmac", _spy_pbkdf2)

    db_file = tmp_path / "real_pbkdf2.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async def _run() -> None:
        cfg = BootstrapConfig(correo="real@condo.test", password="ClaveReal123!Seguro")
        res = await bootstrap_initial_admin(cfg, session_factory=sf, target_engine=engine)
        assert res.status == "created"
        async with sf() as s:
            u = (await s.execute(_select(_Usuario).where(_Usuario.correo == "real@condo.test"))).scalars().first()
            assert u is not None
            assert u.password_hash.startswith("pbkdf2_sha256$")
            assert len(u.password_hash.split("$")) == 3
            assert _verify("ClaveReal123!Seguro", u.password_hash) is True
        await engine.dispose()

    asyncio.run(_run())
    assert iteraciones_observadas == [PBKDF2_ITERATIONS, PBKDF2_ITERATIONS]
    assert PBKDF2_ITERATIONS == 100_000


def test_bootstrap_cli_argumentos_ayuda_y_errores(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Valida flags CLI directos, errores de configuración en stderr y from_env con valores booleanos."""
    db_file = tmp_path / "cli_args.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    test_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(bootstrap_mod, "engine", test_engine)
    monkeypatch.setattr(bootstrap_mod, "AsyncSessionLocal", test_factory)
    monkeypatch.setenv("APP_ENV", "qa_unit")

    assert main([]) == 0
    assert "usage:" in capsys.readouterr().out.lower()

    rc_err = main(["--correo", "bad@condo.test", "--password", "corta", "--rol", "PRESIDENTE"])
    assert rc_err == 1
    assert "Error de bootstrap Día 0:" in capsys.readouterr().err

    rc_ok = main(
        [
            "--correo",
            "cli_admin@condo.test",
            "--password",
            "ClaveCliSegura123!",
            "--nombre",
            "Admin CLI",
            "--cedula",
            "V-99887766",
            "--telefono",
            "+584121112233",
            "--condominio-id",
            "1",
            "--rol",
            "PRESIDENTE",
            "--estructura-nombre",
            "Torre Norte",
            "--estructura-tipo",
            "torre",
            "--unidad-inicial",
            "N-01",
            "--allow-update-existing",
        ]
    )
    assert rc_ok == 0
    out = capsys.readouterr().out
    assert '"status": "created"' in out
    assert '"unidad_id": 1' in out

    # from_env: valores por defecto, booleano truthy ("YES") vs falsy ("0"), y condominio inválido
    monkeypatch.setenv("BOOTSTRAP_ADMIN_CORREO", "env_yes@condo.test")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ClaveEnvSegura123!")
    monkeypatch.delenv("BOOTSTRAP_CONDOMINIO_ID", raising=False)
    monkeypatch.setenv("BOOTSTRAP_ALLOW_UPDATE", "yes")
    cfg_yes = BootstrapConfig.from_env()
    assert cfg_yes.correo == "env_yes@condo.test"
    assert cfg_yes.condominio_id == 1
    assert cfg_yes.rol == "PRESIDENTE"
    assert cfg_yes.estructura_tipo == "TORRE"
    assert cfg_yes.allow_update_existing is True

    monkeypatch.setenv("BOOTSTRAP_ALLOW_UPDATE", "0")
    assert BootstrapConfig.from_env().allow_update_existing is False

    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", "no_entero")
    with pytest.raises(ValueError, match="BOOTSTRAP_CONDOMINIO_ID"):
        BootstrapConfig.from_env()

    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", "0")
    cfg_cero = BootstrapConfig.from_env()
    assert cfg_cero.condominio_id == 0

    with pytest.raises(SystemExit) as exc_help:
        main(["--help"])
    assert exc_help.value.code == 0


def test_bootstrap_constantes_inmutables_claves_prohibidas_y_torre_default(tmp_path: Path) -> None:
    """Valida inmutabilidad de dataclasses, listas blancas/negras y torre por defecto en Día 0."""
    import asyncio
    from dataclasses import FrozenInstanceError

    from sqlalchemy import select as _select

    from src.bootstrap import (
        ROLES_BOOTSTRAP_PERMITIDOS,
        TIPOS_ESTRUCTURA_PERMITIDOS,
        BootstrapResult,
        _PASSWORDS_PROHIBIDOS,
    )
    from src.models import ContratoOcupacion as _Contrato
    from src.models import Estructura as _Estructura
    from src.models import Usuario as _Usuario

    assert ROLES_BOOTSTRAP_PERMITIDOS == ("PRESIDENTE", "VICEPRESIDENTE", "TESORERO", "SECRETARIO")
    assert TIPOS_ESTRUCTURA_PERMITIDOS == ("EDIFICIO", "TORRE", "BLOQUE", "MANZANA", "CALLE")
    assert _PASSWORDS_PROHIBIDOS == frozenset({"changeme", "password1234", "123456789012", "admin1234567"})

    cfg = BootstrapConfig(correo="torre@condo.test", password="ClaveTorreSegura2026!", unidad_inicial="U-1")
    with pytest.raises(FrozenInstanceError):
        setattr(cfg, "rol", "TESORERO")
    res_dummy = BootstrapResult(status="created", usuario_id=1, correo="a@b.com", rol="PRESIDENTE", condominio_id=1)
    with pytest.raises(FrozenInstanceError):
        setattr(res_dummy, "condominio_id", 2)

    db_file = tmp_path / "torre_def.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}")
    sf = async_sessionmaker(engine, expire_on_commit=False)

    async def _run() -> None:
        with pytest.raises(ValueError, match="12 caracteres|placeholder"):
            await bootstrap_initial_admin(
                BootstrapConfig(correo="weak@condo.test", password="changeme"),
                session_factory=sf,
                target_engine=engine,
            )
        for weak in ("password1234", "123456789012", "admin1234567"):
            with pytest.raises(ValueError, match="placeholder|insegura"):
                await bootstrap_initial_admin(
                    BootstrapConfig(correo="weak@condo.test", password=weak),
                    session_factory=sf,
                    target_engine=engine,
                )

        res = await bootstrap_initial_admin(cfg, session_factory=sf, target_engine=engine)
        assert res.status == "created"
        assert res.unidad_id is not None
        async with sf() as s:
            est = (await s.execute(_select(_Estructura))).scalars().first()
            assert est is not None
            assert est.nombre == "Torre Principal"
            assert est.tipo == "TORRE"
            u = (await s.execute(_select(_Usuario).where(_Usuario.correo == "torre@condo.test"))).scalars().first()
            assert u is not None and u.es_activo is True
            cto = (await s.execute(_select(_Contrato).where(_Contrato.usuario_id == u.id))).scalars().first()
            assert cto is not None
            assert cto.tipo_ocupante == "PROPIETARIO"
            assert cto.puede_votar_asamblea is True
        await engine.dispose()

    asyncio.run(_run())


def test_bootstrap_supervivientes_contratos_cli_y_estados(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Cubre contratos exactos de defaults, env, errores ValueError, actualizaciones selectivas y ayuda CLI."""
    import asyncio
    import sys

    from sqlalchemy import select as _select

    from src.bootstrap import _CLI_OVERRIDE_FIELDS, BootstrapResult, _env_str
    from src.models import Estructura as _Estructura
    from src.models import Unidad as _Unidad
    from src.models import Usuario as _Usuario

    # 1. Defaults completos de BootstrapConfig, BootstrapResult, _env_str y override tuple
    assert len(_CLI_OVERRIDE_FIELDS) == 10
    monkeypatch.delenv("BOOTSTRAP_VAR_INEXISTENTE", raising=False)
    assert _env_str("BOOTSTRAP_VAR_INEXISTENTE") == ""

    cfg_def = BootstrapConfig(correo="def@condo.test", password="ClaveDefaultSegura2026!")
    assert cfg_def.condominio_id == 1
    assert cfg_def.nombre == "Presidente Junta Inicial"
    assert cfg_def.cedula == "V-00000001"
    assert cfg_def.telefono == "+584120000000"
    assert cfg_def.rol == "PRESIDENTE"
    assert cfg_def.estructura_nombre is None
    assert cfg_def.estructura_tipo == "TORRE"
    assert cfg_def.unidad_inicial is None
    assert cfg_def.allow_update_existing is False

    res_def = BootstrapResult(status="created", usuario_id=None, correo="x@y.com", rol="PRESIDENTE", condominio_id=1)
    assert res_def.unidad_id is None

    # 2. BootstrapConfig.from_env() completo sin opcionales y con espacios / booleanos
    for env_key in (
        "BOOTSTRAP_CONDOMINIO_ID",
        "BOOTSTRAP_ADMIN_NOMBRE",
        "BOOTSTRAP_ADMIN_CEDULA",
        "BOOTSTRAP_ADMIN_CORREO",
        "BOOTSTRAP_ADMIN_TELEFONO",
        "BOOTSTRAP_ADMIN_PASSWORD",
        "BOOTSTRAP_ADMIN_ROL",
        "BOOTSTRAP_ESTRUCTURA_NOMBRE",
        "BOOTSTRAP_ESTRUCTURA_TIPO",
        "BOOTSTRAP_UNIDAD_INICIAL",
        "BOOTSTRAP_ALLOW_UPDATE",
    ):
        monkeypatch.delenv(env_key, raising=False)

    cfg_vacio = BootstrapConfig.from_env()
    assert cfg_vacio.condominio_id == 1
    assert cfg_vacio.nombre == "Presidente Junta Inicial"
    assert cfg_vacio.cedula == "V-00000001"
    assert cfg_vacio.correo == ""
    assert cfg_vacio.telefono == "+584120000000"
    assert cfg_vacio.password == ""
    assert cfg_vacio.rol == "PRESIDENTE"
    assert cfg_vacio.estructura_nombre is None
    assert cfg_vacio.estructura_tipo == "TORRE"
    assert cfg_vacio.unidad_inicial is None
    assert cfg_vacio.allow_update_existing is False

    monkeypatch.setenv("BOOTSTRAP_ADMIN_CORREO", "  Ines.Pena@Condo.Test  ")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ClaveInesSegura2026!")
    monkeypatch.setenv("BOOTSTRAP_ESTRUCTURA_NOMBRE", "   ")
    monkeypatch.setenv("BOOTSTRAP_UNIDAD_INICIAL", "   ")
    for raw_flag in (" 1 ", " TRUE ", " YeS "):
        monkeypatch.setenv("BOOTSTRAP_ALLOW_UPDATE", raw_flag)
        cfg_flag = BootstrapConfig.from_env()
        assert cfg_flag.correo == "ines.pena@condo.test"
        assert cfg_flag.estructura_nombre is None
        assert cfg_flag.unidad_inicial is None
        assert cfg_flag.allow_update_existing is True

    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", "invalido")
    with pytest.raises(ValueError, match=r"^BOOTSTRAP_CONDOMINIO_ID debe ser un entero positivo\.$"):
        BootstrapConfig.from_env()
    monkeypatch.delenv("BOOTSTRAP_CONDOMINIO_ID", raising=False)

    # 3. CLI argv=None, --help completo, skipped exacto, stderr exacto y JSON ensure_ascii=False
    with pytest.raises(SystemExit) as exc_help:
        main(["--help"])
    assert exc_help.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert "Inicialización idempotente Día 0 de administrador/presidente de condominio." in help_text
    for fragment in (
        "--from-env",
        "Lee la configuración desde BOOTSTRAP_*.",
        "--condominio-id",
        "Identificador entero del tenant/condominio.",
        "Nombre completo del administrador inicial.",
        "Cédula o documento único.",
        "Correo electrónico del administrador inicial.",
        "Teléfono de contacto.",
        "Contraseña inicial (o BOOTSTRAP_ADMIN_PASSWORD).",
        "Rol inicial de Junta (PRESIDENTE/VICEPRESIDENTE/TESORERO).",
        "Nombre de estructura inicial opcional.",
        "Tipo de estructura inicial (TORRE, EDIFICIO, etc.).",
        "Identificador de unidad inicial opcional.",
        "Permite actualizar nombre, teléfono y contraseña si el usuario ya existe.",
    ):
        assert fragment in help_text

    monkeypatch.delenv("BOOTSTRAP_ADMIN_CORREO", raising=False)
    monkeypatch.setattr(sys, "argv", ["python -m src.bootstrap", "--from-env"])
    assert main() == 0
    raw_skip = capsys.readouterr().out.strip()
    assert json.loads(raw_skip) == {"status": "skipped", "reason": "BOOTSTRAP_ADMIN_CORREO no definido"}

    # Fallback de correo/password sin --from-env y salida JSON UTF-8 sin escapar tildes ni ñ
    db_cli = tmp_path / "cli_utf8.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_cli}", echo=False)
    test_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(bootstrap_mod, "engine", test_engine)
    monkeypatch.setattr(bootstrap_mod, "AsyncSessionLocal", test_factory)
    monkeypatch.setenv("APP_ENV", "qa_unit")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_CORREO", "  Ines.CLI@Condo.Test  ")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ClaveUtf8Segura2026!")

    assert main(["--nombre", "Inés Peña", "--cedula", "V-77889900"]) == 0
    raw_cli_out = capsys.readouterr().out.strip()
    assert json.loads(raw_cli_out) == {
        "status": "created",
        "usuario_id": 1,
        "correo": "ines.cli@condo.test",
        "rol": "PRESIDENTE",
        "condominio_id": 1,
        "unidad_id": None,
    }

    assert main(["--correo", "bad@condo.test", "--password", "corta"]) == 1
    assert (
        capsys.readouterr().err.strip()
        == "Error de bootstrap Día 0: La contraseña de bootstrap debe tener al menos 12 caracteres."
    )

    # 4. Flujos DB exactos: errores ValueError, RLS session.info, lookup solo correo / solo cédula,
    # reutilización de Estructura y deltas individuales (solo nombre / solo teléfono / nuevo contrato / sin cambios)
    db_file = tmp_path / "contracts_db.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    sf = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _run_db_contracts() -> None:
        try:
            # Mensajes exactos de validación
            invalid_cases: list[tuple[BootstrapConfig, str]] = [
                (
                    BootstrapConfig(condominio_id=0, correo="v@c.test", password="ClaveValida2026!"),
                    r"^condominio_id debe ser mayor o igual a 1\.$",
                ),
                (
                    BootstrapConfig(nombre="   ", correo="v@c.test", password="ClaveValida2026!"),
                    r"^nombre, cedula y telefono son obligatorios\.$",
                ),
                (
                    BootstrapConfig(correo="v@c.test", password="corta"),
                    r"^La contraseña de bootstrap debe tener al menos 12 caracteres\.$",
                ),
                (
                    BootstrapConfig(correo="v@c.test", password="password1234"),
                    r"^La contraseña de bootstrap no puede usar valores placeholder o triviales\.$",
                ),
                (
                    BootstrapConfig(correo="v@c.test", password="ClaveValida2026!", rol="FANTASMA"),
                    r"^Rol de bootstrap inválido: FANTASMA$",
                ),
                (
                    BootstrapConfig(correo="v@c.test", password="ClaveValida2026!", estructura_tipo="RANCHO"),
                    r"^Tipo de estructura inválido: RANCHO$",
                ),
            ]
            for bad_cfg, pattern in invalid_cases:
                with pytest.raises(ValueError, match=pattern):
                    await bootstrap_initial_admin(bad_cfg, session_factory=sf, target_engine=engine)

            # Verificar inyección explícita de session.sync_session.info (tenant_id e is_superadmin=False)
            seen_infos: list[dict[str, Any]] = []

            def _tracked_factory() -> AsyncSession:
                s = sf()
                s.sync_session.info["is_superadmin"] = True
                seen_infos.append(s.sync_session.info)
                return s

            r_t7 = await bootstrap_initial_admin(
                BootstrapConfig(
                    condominio_id=7,
                    nombre="Admin Siete",
                    cedula="V-70000007",
                    correo="siete@condo.test",
                    telefono="+584127770007",
                    password="ClaveTenantSiete2026!",
                    estructura_nombre="  Torre Sol  ",
                    estructura_tipo="TORRE",
                    unidad_inicial="S-01",
                ),
                session_factory=_tracked_factory,
                target_engine=engine,
            )
            assert r_t7.status == "created"
            assert seen_infos[0]["tenant_id"] == "7"
            assert seen_infos[0]["is_superadmin"] is False

            # Sin allow_update_existing y sin cambios -> unchanged
            r_same = await bootstrap_initial_admin(
                BootstrapConfig(
                    condominio_id=7,
                    nombre="Otro Nombre Ignorado",
                    cedula="V-70000007",
                    correo="siete@condo.test",
                    telefono="+584120000000",
                    password="ClaveTenantSiete2026!",
                    estructura_nombre="Torre Sol",
                    estructura_tipo="TORRE",
                    unidad_inicial="S-01",
                    allow_update_existing=False,
                ),
                session_factory=sf,
                target_engine=engine,
            )
            assert r_same.status == "unchanged"

            # Lookup por coincidencia única de correo (otra cédula) con cambio solo de nombre
            r_only_name = await bootstrap_initial_admin(
                BootstrapConfig(
                    condominio_id=7,
                    nombre="Admin Siete Renombrado",
                    cedula="V-70009999",
                    correo="siete@condo.test",
                    telefono="+584127770007",
                    password="ClaveTenantSiete2026!",
                    unidad_inicial="S-01",
                    allow_update_existing=True,
                ),
                session_factory=sf,
                target_engine=engine,
            )
            assert r_only_name.status == "updated"

            # Lookup por coincidencia única de cédula (otro correo) con cambio solo de teléfono
            r_only_tel = await bootstrap_initial_admin(
                BootstrapConfig(
                    condominio_id=7,
                    nombre="Admin Siete Renombrado",
                    cedula="V-70000007",
                    correo="otro.alias@condo.test",
                    telefono="+584129998811",
                    password="ClaveTenantSiete2026!",
                    unidad_inicial="S-01",
                    allow_update_existing=True,
                ),
                session_factory=sf,
                target_engine=engine,
            )
            assert r_only_tel.status == "updated"

            # allow_update_existing=True sin ningún cambio ni contrato nuevo -> unchanged
            r_noop = await bootstrap_initial_admin(
                BootstrapConfig(
                    condominio_id=7,
                    nombre="Admin Siete Renombrado",
                    cedula="V-70000007",
                    correo="siete@condo.test",
                    telefono="+584129998811",
                    password="ClaveTenantSiete2026!",
                    unidad_inicial="S-01",
                    allow_update_existing=True,
                ),
                session_factory=sf,
                target_engine=engine,
            )
            assert r_noop.status == "unchanged"

            # Distractores de Estructura + reutilización exacta + asignación de nueva unidad sin otros cambios
            async with sf() as s:
                s.add_all(
                    [
                        _Estructura(condominio_id=99, nombre="Torre Sol", tipo="TORRE"),
                        _Estructura(condominio_id=7, nombre="Torre Sol", tipo="EDIFICIO"),
                        _Estructura(condominio_id=7, nombre="Torre Luna", tipo="TORRE"),
                    ]
                )
                await s.commit()

            r_new_unit = await bootstrap_initial_admin(
                BootstrapConfig(
                    condominio_id=7,
                    nombre="Admin Siete Renombrado",
                    cedula="V-70000007",
                    correo="siete@condo.test",
                    telefono="+584129998811",
                    password="ClaveTenantSiete2026!",
                    estructura_nombre="Torre Sol",
                    estructura_tipo="TORRE",
                    unidad_inicial="S-02",
                    allow_update_existing=True,
                ),
                session_factory=sf,
                target_engine=engine,
            )
            assert r_new_unit.status == "updated"

            async with sf() as s:
                ests_match = (
                    (
                        await s.execute(
                            _select(_Estructura).where(
                                _Estructura.condominio_id == 7,
                                _Estructura.nombre == "Torre Sol",
                                _Estructura.tipo == "TORRE",
                            )
                        )
                    )
                    .scalars()
                    .all()
                )
                assert len(ests_match) == 1
                u_s2 = (await s.execute(_select(_Unidad).where(_Unidad.identificador == "S-02"))).scalars().one()
                assert u_s2.estructura_id == ests_match[0].id
                u_count = (await s.execute(_select(_Usuario))).scalars().all()
                assert len(u_count) == 1

            # Conflicto de identidad con segundo usuario y error exacto
            r_u2 = await bootstrap_initial_admin(
                BootstrapConfig(
                    condominio_id=7,
                    nombre="Segundo Admin",
                    cedula="V-80000008",
                    correo="ocho@condo.test",
                    password="ClaveTenantOcho2026!",
                ),
                session_factory=sf,
                target_engine=engine,
            )
            assert r_u2.status == "created"
            assert r_u2.unidad_id is None

            with pytest.raises(
                ValueError,
                match=r"^Conflicto de identidad: correo y cédula pertenecen a registros distintos\.$",
            ):
                await bootstrap_initial_admin(
                    BootstrapConfig(
                        condominio_id=7,
                        correo="siete@condo.test",
                        cedula="V-80000008",
                        password="ClaveTenantSiete2026!",
                    ),
                    session_factory=sf,
                    target_engine=engine,
                )

            with pytest.raises(ValueError, match=r"^La unidad inicial pertenece a otro condominio_id\.$"):
                await bootstrap_initial_admin(
                    BootstrapConfig(
                        condominio_id=9,
                        correo="nueve@condo.test",
                        cedula="V-90000009",
                        password="ClaveTenantNueve2026!",
                        unidad_inicial="S-01",
                    ),
                    session_factory=sf,
                    target_engine=engine,
                )
        finally:
            await engine.dispose()

    asyncio.run(_run_db_contracts())
