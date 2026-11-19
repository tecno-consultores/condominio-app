# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
"""Pruebas unitarias e integración PostgreSQL 17 RLS para el CLI de bootstrap Día 0."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src import bootstrap as bootstrap_mod
from src.bootstrap import (
    _CLI_OVERRIDE_FIELDS,
    _MIN_PASSWORD_LEN,
    _PASSWORDS_PROHIBIDOS,
    ROLES_BOOTSTRAP_PERMITIDOS,
    TIPOS_ESTRUCTURA_PERMITIDOS,
    BootstrapConfig,
    BootstrapResult,
    _activar_y_asignar_rol,
    _actualizar_perfil_usuario,
    _aplicar_actualizacion_usuario,
    _asegurar_contrato_inicial,
    _asegurar_esquema_sqlite,
    _build_cli_parser,
    _buscar_usuario_existente,
    _cerrar_transaccion_bootstrap,
    _crear_o_actualizar_usuario,
    _debe_omitir_bootstrap,
    _env_int_pos,
    _env_str,
    _normalizar_texto_opcional,
    _resolve_cli_config,
    _resolver_argv_efectivo,
    _sincronizar_campo_usuario,
    _validar_campos_obligatorios,
    _validar_config,
    _validar_en_catalogo,
    _validar_password_bootstrap,
    bootstrap_initial_admin,
    main,
)
from src.database import Base
from src.models import ContratoOcupacion, Estructura, Unidad, Usuario
from src.security import PBKDF2_ITERATIONS, get_password_hash, verify_password

_BOOTSTRAP_ENV_KEYS: tuple[str, ...] = (
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
)

_ERR_PLACEHOLDER = r"^La contraseña de bootstrap no puede usar valores placeholder o triviales\.$"
_ERR_REVOCADO = (
    r"^No se permite reactivar mediante bootstrap una cuenta revocada o deshabilitada administrativamente\.$"
)

_EXPECTED_PARSER_HELPS: dict[str, str] = {
    "--from-env": "Lee la configuración desde BOOTSTRAP_*.",
    "--condominio-id": "Identificador entero del tenant/condominio.",
    "--nombre": "Nombre completo del administrador inicial.",
    "--cedula": "Cédula o documento único.",
    "--correo": "Correo electrónico del administrador inicial.",
    "--telefono": "Teléfono de contacto.",
    "--rol": "Rol inicial de Junta (PRESIDENTE/VICEPRESIDENTE/TESORERO).",
    "--estructura-nombre": "Nombre de estructura inicial opcional.",
    "--estructura-tipo": "Tipo de estructura inicial (TORRE, EDIFICIO, etc.).",
    "--unidad-inicial": "Identificador de unidad inicial opcional.",
    "--allow-update-existing": "Permite actualizar nombre, teléfono y contraseña si el usuario ya existe.",
}


async def _crear_motor_sqlite_memoria(*, crear_esquema: bool = False) -> tuple[AsyncEngine, Any]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    if crear_esquema:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return engine, factory


def _listar_tablas(sync_conn: Connection) -> list[str]:
    return inspect(sync_conn).get_table_names()


@pytest.fixture(autouse=True)
def _acelerar_pbkdf2_wiring_bootstrap(monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest) -> None:
    """Acelera tests de cableado SQLite/CLI reduciendo iteraciones PBKDF2 excepto en el test real de 600k."""
    if request.node.name != "test_bootstrap_pbkdf2_iteraciones_reales":
        monkeypatch.setattr("src.security.PBKDF2_ITERATIONS", 1)


def test_bootstrap_dataclasses_slots_frozen_defaults_y_constantes() -> None:
    """Valida slots, inmutabilidad, defaults y catálogos cerrados sin tocar base de datos."""
    assert ROLES_BOOTSTRAP_PERMITIDOS == ("PRESIDENTE", "VICEPRESIDENTE", "TESORERO", "SECRETARIO")
    assert TIPOS_ESTRUCTURA_PERMITIDOS == ("EDIFICIO", "TORRE", "BLOQUE", "MANZANA", "CALLE")
    assert _PASSWORDS_PROHIBIDOS == frozenset({"changeme", "password1234", "123456789012", "admin1234567"})
    assert _MIN_PASSWORD_LEN == 12
    assert _CLI_OVERRIDE_FIELDS == (
        "condominio_id",
        "nombre",
        "cedula",
        "correo",
        "telefono",
        "rol",
        "estructura_nombre",
        "estructura_tipo",
        "unidad_inicial",
    )

    assert hasattr(BootstrapConfig, "__slots__")
    assert hasattr(BootstrapResult, "__slots__")

    cfg = BootstrapConfig(correo="def@condo.test", password="ClaveDefaultSegura2026!")
    assert not hasattr(cfg, "__dict__")
    assert cfg.condominio_id == 1
    assert cfg.nombre == "Presidente Junta Inicial"
    assert cfg.cedula == "V-00000001"
    assert cfg.telefono == "+584120000000"
    assert cfg.rol == "PRESIDENTE"
    assert cfg.estructura_nombre is None
    assert cfg.estructura_tipo == "TORRE"
    assert cfg.unidad_inicial is None
    assert cfg.allow_update_existing is False
    with pytest.raises(FrozenInstanceError):
        setattr(cfg, "rol", "TESORERO")

    res = BootstrapResult(status="created", usuario_id=None, correo="a@b.com", rol="PRESIDENTE", condominio_id=1)
    assert not hasattr(res, "__dict__")
    assert res.unidad_id is None
    with pytest.raises(FrozenInstanceError):
        setattr(res, "condominio_id", 2)


def test_bootstrap_env_helpers_y_from_env_completo(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida _env_str, _env_int_pos y BootstrapConfig.from_env en estados vacío, parcial y completo."""
    for env_key in _BOOTSTRAP_ENV_KEYS:
        monkeypatch.delenv(env_key, raising=False)

    assert _env_str("BOOTSTRAP_ADMIN_CORREO") == ""
    assert _env_str("BOOTSTRAP_ADMIN_CORREO", "fallback") == "fallback"
    monkeypatch.setenv("BOOTSTRAP_ADMIN_CORREO", "   ")
    assert _env_str("BOOTSTRAP_ADMIN_CORREO", "fallback") == "fallback"
    monkeypatch.setenv("BOOTSTRAP_ADMIN_CORREO", "  valor  ")
    assert _env_str("BOOTSTRAP_ADMIN_CORREO", "fallback") == "valor"
    monkeypatch.delenv("BOOTSTRAP_ADMIN_CORREO", raising=False)

    assert _env_int_pos("BOOTSTRAP_CONDOMINIO_ID", 5) == 5
    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", "   ")
    assert _env_int_pos("BOOTSTRAP_CONDOMINIO_ID", 5) == 5
    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", " 9 ")
    assert _env_int_pos("BOOTSTRAP_CONDOMINIO_ID", 5) == 9
    monkeypatch.delenv("BOOTSTRAP_CONDOMINIO_ID", raising=False)

    cfg_vacio = BootstrapConfig.from_env()
    assert cfg_vacio == BootstrapConfig(correo="", password="")

    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", " 7 ")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_NOMBRE", "  Ana Env  ")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_CEDULA", "  V-88776655  ")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_CORREO", "  Ana.Env@Condo.Test  ")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_TELEFONO", "  +584141112233  ")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "  ClaveRawEnv123!  ")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_ROL", "  tesorero  ")
    monkeypatch.setenv("BOOTSTRAP_ESTRUCTURA_NOMBRE", "  Torre Este  ")
    monkeypatch.setenv("BOOTSTRAP_ESTRUCTURA_TIPO", "  edificio  ")
    monkeypatch.setenv("BOOTSTRAP_UNIDAD_INICIAL", "  PH-9  ")
    for truthy in (" 1 ", " TRUE ", " YeS "):
        monkeypatch.setenv("BOOTSTRAP_ALLOW_UPDATE", truthy)
        cfg_full = BootstrapConfig.from_env()
        assert cfg_full == BootstrapConfig(
            condominio_id=7,
            nombre="Ana Env",
            cedula="V-88776655",
            correo="ana.env@condo.test",
            telefono="+584141112233",
            password="  ClaveRawEnv123!  ",
            rol="TESORERO",
            estructura_nombre="Torre Este",
            estructura_tipo="EDIFICIO",
            unidad_inicial="PH-9",
            allow_update_existing=True,
        )

    for falsy in ("0", "false", "no", "   "):
        monkeypatch.setenv("BOOTSTRAP_ALLOW_UPDATE", falsy)
        assert BootstrapConfig.from_env().allow_update_existing is False

    monkeypatch.setenv("BOOTSTRAP_ESTRUCTURA_NOMBRE", "   ")
    monkeypatch.setenv("BOOTSTRAP_UNIDAD_INICIAL", "   ")
    cfg_blanks = BootstrapConfig.from_env()
    assert cfg_blanks.estructura_nombre is None
    assert cfg_blanks.unidad_inicial is None

    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", "no-entero")
    with pytest.raises(ValueError, match=r"^BOOTSTRAP_CONDOMINIO_ID debe ser un entero positivo\.$"):
        BootstrapConfig.from_env()

    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", "0")
    assert BootstrapConfig.from_env().condominio_id == 0


def test_bootstrap_validacion_pura_y_limites() -> None:
    """Cubre validaciones, normalizaciones y límites exactos sin overhead de SQLite."""
    assert _normalizar_texto_opcional(None) is None
    assert _normalizar_texto_opcional("   ") is None
    assert _normalizar_texto_opcional("  Torre A  ") == "Torre A"

    assert _validar_password_bootstrap("ClaveValida1") == "ClaveValida1"
    assert _validar_password_bootstrap("  ClaveEspacio1  ") == "  ClaveEspacio1  "
    with pytest.raises(ValueError, match=r"^La contraseña de bootstrap debe tener al menos 12 caracteres\.$"):
        _validar_password_bootstrap("ClaveValid1")

    for trivial in (
        "  CHANGEME  ",
        "password1234",
        "123456789012",
        "admin1234567",
        "Mi_CAMBIAR_PLACEHOLDER_Clave",
    ):
        with pytest.raises(ValueError, match=_ERR_PLACEHOLDER):
            _validar_password_bootstrap(trivial)
    with pytest.raises(ValueError, match=r"^La contraseña de bootstrap debe tener al menos 12 caracteres\.$"):
        _validar_password_bootstrap("changeme")

    assert _validar_en_catalogo("  tesorero  ", ROLES_BOOTSTRAP_PERMITIDOS, "Rol de bootstrap") == "TESORERO"
    for rol in ROLES_BOOTSTRAP_PERMITIDOS:
        assert _validar_en_catalogo(rol.lower(), ROLES_BOOTSTRAP_PERMITIDOS, "Rol de bootstrap") == rol
    for tipo in TIPOS_ESTRUCTURA_PERMITIDOS:
        assert _validar_en_catalogo(tipo.lower(), TIPOS_ESTRUCTURA_PERMITIDOS, "Tipo de estructura") == tipo

    invalid_cases: list[tuple[dict[str, Any], str]] = [
        ({"condominio_id": 0}, r"^condominio_id debe ser mayor o igual a 1\.$"),
        ({"condominio_id": -2}, r"^condominio_id debe ser mayor o igual a 1\.$"),
        ({"nombre": "   "}, r"^nombre, cedula y telefono son obligatorios\.$"),
        ({"cedula": "   "}, r"^nombre, cedula y telefono son obligatorios\.$"),
        ({"telefono": "   "}, r"^nombre, cedula y telefono son obligatorios\.$"),
        ({"correo": "correo-invalido"}, "correo electrónico inválido"),
        ({"password": "corta"}, r"^La contraseña de bootstrap debe tener al menos 12 caracteres\.$"),
        (
            {"password": "password1234"},
            _ERR_PLACEHOLDER,
        ),
        ({"rol": "FANTASMA"}, r"^Rol de bootstrap inválido: FANTASMA$"),
        ({"estructura_tipo": "RANCHO"}, r"^Tipo de estructura inválido: RANCHO$"),
    ]
    for overrides, pattern in invalid_cases:
        base_kwargs: dict[str, Any] = {
            "correo": "admin@condominio.test",
            "password": "ClaveSeguraBootstrap2026!",
        }
        base_kwargs.update(overrides)
        with pytest.raises(ValueError, match=pattern):
            _validar_config(BootstrapConfig(**base_kwargs))

    ok_obligatorios = _validar_campos_obligatorios(
        BootstrapConfig(
            condominio_id=1,
            nombre="  Ana  ",
            cedula="  V-123  ",
            correo="a@b.test",
            telefono="  +58412  ",
            password="ClaveSeguraBootstrap2026!",
        )
    )
    assert ok_obligatorios == ("Ana", "V-123", "+58412")

    norm = _validar_config(
        BootstrapConfig(
            condominio_id=1,
            nombre="  Ana Presidenta  ",
            cedula="  V-123456  ",
            correo="  Ana.Presi@Condominio.Test  ",
            telefono="  +584121234567  ",
            password="ClaveSeguraBootstrap2026!",
            rol=" vicepresidente ",
            estructura_nombre="  Torre Norte  ",
            estructura_tipo=" edificio ",
            unidad_inicial="  A-10  ",
            allow_update_existing=True,
        )
    )
    assert norm == BootstrapConfig(
        condominio_id=1,
        nombre="Ana Presidenta",
        cedula="V-123456",
        correo="ana.presi@condominio.test",
        telefono="+584121234567",
        password="ClaveSeguraBootstrap2026!",
        rol="VICEPRESIDENTE",
        estructura_nombre="Torre Norte",
        estructura_tipo="EDIFICIO",
        unidad_inicial="A-10",
        allow_update_existing=True,
    )


@pytest.mark.asyncio
async def test_bootstrap_rechaza_antes_de_tocar_bd_y_respeta_dialecto() -> None:
    """Comprueba que bootstrap_initial_admin valida antes de crear esquema y omite DDL en no-SQLite."""

    class _FakeDialect:
        name = "postgresql"

    class _NonSqliteEngine:
        dialect = _FakeDialect()

        def begin(self) -> Any:
            raise AssertionError("No debe ejecutar create_all fuera de sqlite.")

    await _asegurar_esquema_sqlite(cast(AsyncEngine, _NonSqliteEngine()))

    engine, factory = await _crear_motor_sqlite_memoria(crear_esquema=False)
    try:
        with pytest.raises(ValueError, match=r"^condominio_id debe ser mayor o igual a 1\.$"):
            await bootstrap_initial_admin(
                BootstrapConfig(condominio_id=0, correo="admin@condo.test", password="ClaveSeguraBootstrap2026!"),
                session_factory=factory,
                target_engine=engine,
            )
        async with engine.begin() as conn:
            assert await conn.run_sync(_listar_tablas) == []
    finally:
        await engine.dispose()


def test_cli_tty_anti_hang_sin_argumentos(capsys: pytest.CaptureFixture[str]) -> None:
    """Sin argumentos imprime ayuda inmediatamente y retorna 0 (QA-CLI-TTY-01)."""
    assert main([]) == 0
    captured = capsys.readouterr()
    assert "python -m src.bootstrap" in captured.out
    assert "Inicialización idempotente Día 0 de administrador/presidente de condominio." in captured.out
    assert captured.err == ""


def test_cli_from_env_omitido_cuando_no_hay_correo(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Con --from-env y sin BOOTSTRAP_ADMIN_CORREO (o solo espacios), omite sin error ni DB."""
    monkeypatch.delenv("BOOTSTRAP_ADMIN_CORREO", raising=False)
    assert main(["--from-env"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "status": "skipped",
        "reason": "BOOTSTRAP_ADMIN_CORREO no definido",
    }

    monkeypatch.setenv("BOOTSTRAP_ADMIN_CORREO", "   ")
    monkeypatch.setattr(sys, "argv", ["python -m src.bootstrap", "--from-env"])
    assert main() == 0
    assert json.loads(capsys.readouterr().out) == {
        "status": "skipped",
        "reason": "BOOTSTRAP_ADMIN_CORREO no definido",
    }


def test_cli_fail_fast_en_produccion_con_secret_inseguro(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """En APP_ENV=production con SECRET_KEY por defecto falla con exit code 1 y stderr exacto."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "qa-blueprint-11x-secret-key-super-secure-32bytes")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ClaveRobusta123!")
    code = main(["--correo", "presidente@condominio.test"])
    assert code == 1
    captured = capsys.readouterr()
    assert "Error de bootstrap Día 0:" in captured.err
    assert captured.out == ""


def test_cli_parser_resolucion_config_y_main_sin_db(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Valida metadata exacta de argparse, flags, defaults, resolución CLI/env y salida UTF-8 sin DB."""
    for env_key in _BOOTSTRAP_ENV_KEYS:
        monkeypatch.delenv(env_key, raising=False)

    parser = _build_cli_parser()
    assert parser.prog == "python -m src.bootstrap"
    assert parser.description == "Inicialización idempotente Día 0 de administrador/presidente de condominio."

    helps_by_opt = {
        opt: action.help for action in parser._actions for opt in action.option_strings if opt not in {"-h", "--help"}
    }
    assert helps_by_opt == _EXPECTED_PARSER_HELPS
    assert "--password" not in helps_by_opt

    args_empty = parser.parse_args([])
    assert args_empty.from_env is False
    assert args_empty.allow_update_existing is False
    for field in _CLI_OVERRIDE_FIELDS:
        assert getattr(args_empty, field) is None

    args_full = parser.parse_args(
        [
            "--from-env",
            "--condominio-id",
            "42",
            "--nombre",
            "Nombre CLI",
            "--cedula",
            "V-424242",
            "--correo",
            "cli@condo.test",
            "--telefono",
            "+584120004242",
            "--rol",
            "TESORERO",
            "--estructura-nombre",
            "Torre 42",
            "--estructura-tipo",
            "EDIFICIO",
            "--unidad-inicial",
            "P-42",
            "--allow-update-existing",
        ]
    )
    assert args_full.from_env is True
    assert args_full.allow_update_existing is True
    assert isinstance(args_full.condominio_id, int)
    assert args_full.condominio_id == 42
    assert args_full.nombre == "Nombre CLI"
    assert args_full.cedula == "V-424242"
    assert args_full.correo == "cli@condo.test"
    assert args_full.telefono == "+584120004242"
    assert args_full.rol == "TESORERO"
    assert args_full.estructura_nombre == "Torre 42"
    assert args_full.estructura_tipo == "EDIFICIO"
    assert args_full.unidad_inicial == "P-42"

    with pytest.raises(SystemExit) as exc_bad_int:
        parser.parse_args(["--condominio-id", "no_int"])
    assert exc_bad_int.value.code == 2
    capsys.readouterr()

    with pytest.raises(SystemExit) as exc_unknown:
        parser.parse_args(["--flag-inexistente"])
    assert exc_unknown.value.code == 2
    capsys.readouterr()

    with pytest.raises(SystemExit) as exc_help:
        main(["--help"])
    assert exc_help.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert parser.prog in help_text
    assert parser.description in help_text
    for opt, help_msg in _EXPECTED_PARSER_HELPS.items():
        assert opt in help_text
        assert help_msg in help_text

    # _resolver_argv_efectivo y _debe_omitir_bootstrap
    orig_argv = ["prog", "--correo", "a@b.test"]
    monkeypatch.setattr(sys, "argv", orig_argv)
    assert _resolver_argv_efectivo(None) == ["--correo", "a@b.test"]
    assert _resolver_argv_efectivo(["--from-env"]) == ["--from-env"]
    assert orig_argv == ["prog", "--correo", "a@b.test"]

    assert _debe_omitir_bootstrap(argparse.Namespace(from_env=False, correo=None)) is False
    monkeypatch.setenv("BOOTSTRAP_ADMIN_CORREO", "   ")
    assert _debe_omitir_bootstrap(argparse.Namespace(from_env=True, correo=None)) is True
    assert _debe_omitir_bootstrap(argparse.Namespace(from_env=True, correo="cli@condo.test")) is False
    monkeypatch.setenv("BOOTSTRAP_ADMIN_CORREO", "  Env.User@Condo.Test  ")
    assert _debe_omitir_bootstrap(argparse.Namespace(from_env=True, correo=None)) is False

    # _resolve_cli_config sin --from-env vs con --from-env
    monkeypatch.setenv("BOOTSTRAP_CONDOMINIO_ID", "9")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_NOMBRE", "Nombre Solo Env")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ClaveCliEnv2026!")
    monkeypatch.setenv("BOOTSTRAP_ALLOW_UPDATE", "1")

    cfg_no_env = _resolve_cli_config(parser.parse_args(["--nombre", "Nombre CLI"]))
    assert cfg_no_env.condominio_id == 1
    assert cfg_no_env.nombre == "Nombre CLI"
    assert cfg_no_env.correo == "env.user@condo.test"
    assert cfg_no_env.password == "ClaveCliEnv2026!"
    assert cfg_no_env.allow_update_existing is False

    cfg_with_env = _resolve_cli_config(parser.parse_args(["--from-env", "--rol", "SECRETARIO"]))
    assert cfg_with_env.condominio_id == 9
    assert cfg_with_env.nombre == "Nombre Solo Env"
    assert cfg_with_env.rol == "SECRETARIO"
    assert cfg_with_env.allow_update_existing is True

    monkeypatch.setenv("BOOTSTRAP_ALLOW_UPDATE", "0")
    cfg_flag_update = _resolve_cli_config(parser.parse_args(["--from-env", "--allow-update-existing"]))
    assert cfg_flag_update.allow_update_existing is True

    # Error ValueError en main() sin tocar SQLite
    monkeypatch.setenv("APP_ENV", "qa_unit")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "corta")
    assert main(["--correo", "bad@condo.test"]) == 1
    assert (
        capsys.readouterr().err.strip()
        == "Error de bootstrap Día 0: La contraseña de bootstrap debe tener al menos 12 caracteres."
    )

    # Salida JSON ensure_ascii=False en main() y reenvío exacto de BootstrapConfig
    seen_cfgs: list[BootstrapConfig] = []

    async def _fake_exec(cfg: BootstrapConfig) -> BootstrapResult:
        seen_cfgs.append(cfg)
        return BootstrapResult(
            status="created",
            usuario_id=3,
            correo=cfg.correo,
            rol=cfg.rol,
            condominio_id=cfg.condominio_id,
            unidad_id=None,
        )

    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ClaveCliEnv2026!")
    monkeypatch.setattr(bootstrap_mod, "_execute_cli_bootstrap", _fake_exec)
    assert main(["--correo", "inés.peña@condo.test"]) == 0
    assert seen_cfgs == [BootstrapConfig(correo="inés.peña@condo.test", password="ClaveCliEnv2026!")]
    raw_json = capsys.readouterr().out.strip()
    assert "inés.peña@condo.test" in raw_json
    assert "\\u00" not in raw_json
    assert json.loads(raw_json) == {
        "status": "created",
        "usuario_id": 3,
        "correo": "inés.peña@condo.test",
        "rol": "PRESIDENTE",
        "condominio_id": 1,
        "unidad_id": None,
    }


def test_bootstrap_helpers_actualizacion_sin_db() -> None:
    """Cubre aislamiento de flags booleanos en _activar_y_asignar_rol, _actualizar_perfil y _aplicar_actualizacion."""
    # _activar_y_asignar_rol: 4 combinaciones
    u_inactivo_mismo_rol = Usuario(
        condominio_id=1,
        nombre="A",
        cedula="V-1",
        correo="a@c.test",
        telefono="+58412",
        password_hash="h",
        es_activo=False,
        rol="PRESIDENTE",
    )
    assert _activar_y_asignar_rol(u_inactivo_mismo_rol, "PRESIDENTE") is True
    assert u_inactivo_mismo_rol.es_activo is True
    assert u_inactivo_mismo_rol.rol == "PRESIDENTE"

    u_activo_otro_rol = Usuario(
        condominio_id=1,
        nombre="A",
        cedula="V-1",
        correo="a@c.test",
        telefono="+58412",
        password_hash="h",
        es_activo=True,
        rol="PROPIETARIO",
    )
    assert _activar_y_asignar_rol(u_activo_otro_rol, "PRESIDENTE") is True
    assert u_activo_otro_rol.es_activo is True
    assert u_activo_otro_rol.rol == "PRESIDENTE"
    assert _activar_y_asignar_rol(u_activo_otro_rol, "PRESIDENTE") is False

    # _sincronizar_campo_usuario
    assert _sincronizar_campo_usuario(u_activo_otro_rol, "nombre", "A") is False
    assert _sincronizar_campo_usuario(u_activo_otro_rol, "nombre", "B") is True
    assert u_activo_otro_rol.nombre == "B"

    # _actualizar_perfil_usuario: solo password, solo nombre, solo telefono, sin cambios, allow_update=False
    hash_orig = get_password_hash("ClaveInicialOriginal123!")
    u_perfil = Usuario(
        condominio_id=1,
        nombre="Ana",
        cedula="V-2",
        correo="ana@c.test",
        telefono="+584120001111",
        password_hash=hash_orig,
        es_activo=True,
        rol="PRESIDENTE",
    )
    cfg_base = BootstrapConfig(
        condominio_id=1,
        nombre="Ana",
        cedula="V-2",
        correo="ana@c.test",
        telefono="+584120001111",
        password="ClaveInicialOriginal123!",
        rol="PRESIDENTE",
        allow_update_existing=False,
    )
    assert (
        _actualizar_perfil_usuario(
            u_perfil,
            BootstrapConfig(
                condominio_id=1,
                nombre="Otro",
                cedula="V-2",
                correo="ana@c.test",
                telefono="+584129999999",
                password="ClaveSeguraDiferente1!",
                allow_update_existing=False,
            ),
        )
        is False
    )
    assert u_perfil.nombre == "Ana"
    assert u_perfil.password_hash == hash_orig

    cfg_allow = BootstrapConfig(
        condominio_id=1,
        nombre="Ana",
        cedula="V-2",
        correo="ana@c.test",
        telefono="+584120001111",
        password="ClaveInicialOriginal123!",
        rol="PRESIDENTE",
        allow_update_existing=True,
    )
    assert _actualizar_perfil_usuario(u_perfil, cfg_allow) is False
    assert u_perfil.password_hash == hash_orig

    cfg_solo_nombre = BootstrapConfig(
        condominio_id=1,
        nombre="Ana Renombrada",
        cedula="V-2",
        correo="ana@c.test",
        telefono="+584120001111",
        password="ClaveInicialOriginal123!",
        rol="PRESIDENTE",
        allow_update_existing=True,
    )
    assert _actualizar_perfil_usuario(u_perfil, cfg_solo_nombre) is True
    assert u_perfil.nombre == "Ana Renombrada"
    assert u_perfil.telefono == "+584120001111"
    assert u_perfil.password_hash == hash_orig

    cfg_solo_tel = BootstrapConfig(
        condominio_id=1,
        nombre="Ana Renombrada",
        cedula="V-2",
        correo="ana@c.test",
        telefono="+584129991111",
        password="ClaveInicialOriginal123!",
        rol="PRESIDENTE",
        allow_update_existing=True,
    )
    assert _actualizar_perfil_usuario(u_perfil, cfg_solo_tel) is True
    assert u_perfil.nombre == "Ana Renombrada"
    assert u_perfil.telefono == "+584129991111"
    assert u_perfil.password_hash == hash_orig

    cfg_solo_pwd = BootstrapConfig(
        condominio_id=1,
        nombre="Ana Renombrada",
        cedula="V-2",
        correo="ana@c.test",
        telefono="+584129991111",
        password="ClaveSeguraRotada2026!",
        rol="PRESIDENTE",
        allow_update_existing=True,
    )
    assert _actualizar_perfil_usuario(u_perfil, cfg_solo_pwd) is True
    assert u_perfil.password_hash != hash_orig
    assert verify_password("ClaveSeguraRotada2026!", u_perfil.password_hash) is True

    # _aplicar_actualizacion_usuario: revocado con distintos roles no-FANTASMA, FANTASMA, solo base, solo perfil, noop
    for rol_revocado in ("PROPIETARIO", "PRESIDENTE"):
        u_rev = Usuario(
            condominio_id=1,
            nombre="Rev",
            cedula="V-3",
            correo="rev@c.test",
            telefono="+58412",
            password_hash="h",
            es_activo=False,
            rol=rol_revocado,
        )
        with pytest.raises(ValueError, match=_ERR_REVOCADO):
            _aplicar_actualizacion_usuario(u_rev, cfg_base)

    u_fan = Usuario(
        condominio_id=1,
        nombre="Fan",
        cedula="V-4",
        correo="fan@c.test",
        telefono="+58412",
        password_hash=hash_orig,
        es_activo=False,
        rol="FANTASMA",
    )
    assert _aplicar_actualizacion_usuario(u_fan, cfg_base) is True
    assert u_fan.es_activo is True
    assert u_fan.rol == "PRESIDENTE"
    assert u_fan.nombre == "Fan"

    assert _aplicar_actualizacion_usuario(u_perfil, cfg_solo_pwd) is False
    assert (
        _aplicar_actualizacion_usuario(
            u_perfil,
            BootstrapConfig(
                condominio_id=1,
                nombre="Ana Renombrada",
                cedula="V-2",
                correo="ana@c.test",
                telefono="+584129991111",
                password="ClaveSeguraNueva2026!",
                rol="PRESIDENTE",
                allow_update_existing=True,
            ),
        )
        is True
    )


@pytest.mark.asyncio
async def test_cerrar_transaccion_bootstrap_commit_y_rollback() -> None:
    """Verifica llamadas exactas a commit y rollback en _cerrar_transaccion_bootstrap."""

    class _SpySession:
        def __init__(self) -> None:
            self.commits = 0
            self.rollbacks = 0

        async def commit(self) -> None:
            self.commits += 1

        async def rollback(self) -> None:
            self.rollbacks += 1

    s1 = _SpySession()
    assert await _cerrar_transaccion_bootstrap(cast(AsyncSession, s1), True, False) == "created"
    assert (s1.commits, s1.rollbacks) == (1, 0)

    s2 = _SpySession()
    assert await _cerrar_transaccion_bootstrap(cast(AsyncSession, s2), True, True) == "created"
    assert (s2.commits, s2.rollbacks) == (1, 0)

    s3 = _SpySession()
    assert await _cerrar_transaccion_bootstrap(cast(AsyncSession, s3), False, True) == "updated"
    assert (s3.commits, s3.rollbacks) == (1, 0)

    s4 = _SpySession()
    assert await _cerrar_transaccion_bootstrap(cast(AsyncSession, s4), False, False) == "unchanged"
    assert (s4.commits, s4.rollbacks) == (0, 1)


@pytest.mark.asyncio
async def test_bootstrap_creacion_idempotencia_unidad_y_actualizacion() -> None:
    """Valida creación inicial, idempotencia, rotación individual/total y unidad en SQLite memoria."""
    engine, factory = await _crear_motor_sqlite_memoria(crear_esquema=False)
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
        assert res1 == BootstrapResult(
            status="created",
            usuario_id=res1.usuario_id,
            correo="maria.presidenta@condominio.test",
            rol="PRESIDENTE",
            condominio_id=1,
            unidad_id=res1.unidad_id,
        )
        assert res1.usuario_id is not None
        assert res1.unidad_id is not None

        res2 = await bootstrap_initial_admin(cfg, session_factory=factory, target_engine=engine)
        assert res2 == BootstrapResult(
            status="unchanged",
            usuario_id=res1.usuario_id,
            correo="maria.presidenta@condominio.test",
            rol="PRESIDENTE",
            condominio_id=1,
            unidad_id=res1.unidad_id,
        )

        # Rotación SOLO de contraseña (aisla pwd_changed=True en flujo completo)
        cfg_solo_pwd = BootstrapConfig(
            condominio_id=1,
            nombre="María Presidenta",
            cedula="V-10203040",
            correo="maria.presidenta@condominio.test",
            telefono="+584121234567",
            password="ClaveSeguraSoloPwd2026!",
            rol="PRESIDENTE",
            estructura_nombre="Torre Ávila",
            estructura_tipo="TORRE",
            unidad_inicial="A-101",
            allow_update_existing=True,
        )
        res_pwd = await bootstrap_initial_admin(cfg_solo_pwd, session_factory=factory, target_engine=engine)
        assert res_pwd.status == "updated"

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
        assert res3 == BootstrapResult(
            status="updated",
            usuario_id=res1.usuario_id,
            correo="maria.presidenta@condominio.test",
            rol="PRESIDENTE",
            condominio_id=1,
            unidad_id=res1.unidad_id,
        )

        async with factory() as session:
            user = (await session.execute(select(Usuario).where(Usuario.id == res1.usuario_id))).scalars().one()
            assert user.nombre == "María Presidenta Actualizada"
            assert user.telefono == "+584129998877"
            assert verify_password("NuevaClaveSeguraBootstrap2026!", user.password_hash) is True
            unidad = (await session.execute(select(Unidad).where(Unidad.id == res1.unidad_id))).scalars().one()
            assert unidad.alicuota == Decimal("0.0000")
            assert unidad.cuota_fija_usd is None
            assert unidad.credito_disponible_usd == Decimal("0.00")
            contratos = (await session.execute(select(ContratoOcupacion))).scalars().all()
            assert len(contratos) == 1
            assert contratos[0].es_activo is True
            assert contratos[0].tipo_ocupante == "PROPIETARIO"
            assert contratos[0].puede_votar_asamblea is True
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_bootstrap_promueve_fantasma_cierra_contrato_previo_y_detecta_conflictos() -> None:
    """Cubre promoción de Fantasma, cierre de contrato previo activo, conflictos y búsqueda directa."""
    engine, factory = await _crear_motor_sqlite_memoria(crear_esquema=True)
    fecha_cerrado = datetime(2025, 1, 15, 12, 0, tzinfo=UTC)
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
                password_hash=get_password_hash("ClaveInicialOtroBootstrap1!"),
                es_activo=True,
                rol="PROPIETARIO",
            )
            session.add_all([u1, u2, u_otro_tenant, fantasma, otro])
            await session.flush()
            session.add_all(
                [
                    ContratoOcupacion(
                        condominio_id=1,
                        usuario_id=fantasma.id,
                        unidad_id=u1.id,
                        tipo_ocupante="PROPIETARIO",
                        es_activo=False,
                        fecha_fin=fecha_cerrado,
                    ),
                    ContratoOcupacion(
                        condominio_id=1,
                        usuario_id=fantasma.id,
                        unidad_id=u1.id,
                        tipo_ocupante="PROPIETARIO",
                        es_activo=True,
                    ),
                ]
            )
            await session.commit()
            fantasma_id = fantasma.id
            otro_id = otro.id
            u2_id = u2.id

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
        assert res == BootstrapResult(
            status="updated",
            usuario_id=fantasma_id,
            correo="fantasma@condominio.test",
            rol="TESORERO",
            condominio_id=1,
            unidad_id=u2_id,
        )

        # Re-ejecutar promoción sobre usuario activo con rol distinto y unidad_inicial=None
        res_rol = await bootstrap_initial_admin(
            BootstrapConfig(
                condominio_id=1,
                nombre="Otro Vecino",
                cedula="V-33334444",
                correo="otro@condominio.test",
                telefono="+584140002222",
                password="ClaveInicialOtroBootstrap1!",
                rol="SECRETARIO",
                unidad_inicial=None,
                allow_update_existing=False,
            ),
            session_factory=factory,
            target_engine=engine,
        )
        assert res_rol.status == "updated"
        assert res_rol.rol == "SECRETARIO"
        assert res_rol.unidad_id is None

        # Existente sin cambios y unidad_inicial=None -> unchanged (mata L235 return False -> True)
        res_none_unchanged = await bootstrap_initial_admin(
            BootstrapConfig(
                condominio_id=1,
                nombre="Otro Vecino",
                cedula="V-33334444",
                correo="otro@condominio.test",
                telefono="+584140002222",
                password="ClaveInicialOtroBootstrap1!",
                rol="SECRETARIO",
                unidad_inicial=None,
                allow_update_existing=True,
            ),
            session_factory=factory,
            target_engine=engine,
        )
        assert res_none_unchanged.status == "unchanged"
        assert res_none_unchanged.unidad_id is None

        async with factory() as session:
            contratos = (
                (
                    await session.execute(
                        select(ContratoOcupacion)
                        .where(ContratoOcupacion.usuario_id == fantasma_id)
                        .order_by(ContratoOcupacion.id.asc())
                    )
                )
                .scalars()
                .all()
            )
            assert len(contratos) == 3
            assert contratos[0].es_activo is False
            assert contratos[0].fecha_fin is not None
            assert contratos[0].fecha_fin.replace(tzinfo=None) == fecha_cerrado.replace(tzinfo=None)
            assert contratos[1].es_activo is False
            assert contratos[1].fecha_fin is not None
            assert contratos[1].fecha_fin.replace(tzinfo=None) > fecha_cerrado.replace(tzinfo=None)
            assert contratos[2].es_activo is True and contratos[2].unidad_id == u2_id

            # Verificación directa de _buscar_usuario_existente y _asegurar_contrato_inicial
            assert await _buscar_usuario_existente(session, "no@existe.test", "V-0000") is None
            match_correo = await _buscar_usuario_existente(session, "fantasma@condominio.test", "V-INEXISTENTE")
            assert match_correo is not None and match_correo.id == fantasma_id
            match_cedula = await _buscar_usuario_existente(session, "inexistente@c.test", "V-33334444")
            assert match_cedula is not None and match_cedula.id == otro_id
            match_ambos = await _buscar_usuario_existente(session, "fantasma@condominio.test", "V-11112222")
            assert match_ambos is not None and match_ambos.id == fantasma_id

            u2_obj = (await session.execute(select(Unidad).where(Unidad.id == u2_id))).scalars().one()
            assert await _asegurar_contrato_inicial(session, match_ambos, None, 1) is False
            assert await _asegurar_contrato_inicial(session, match_ambos, u2_obj, 1) is False

        with pytest.raises(
            ValueError,
            match=r"^Conflicto de identidad: correo y cédula pertenecen a registros distintos\.$",
        ):
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

        with pytest.raises(ValueError, match=r"^La unidad inicial pertenece a otro condominio_id\.$"):
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


@pytest.mark.asyncio
async def test_bootstrap_contratos_tupla_creacion_rls_estructura_y_revocado() -> None:
    """Cubre tupla (user, created, updated), RLS session.info, Torre Principal, distractores y revocado."""
    engine, factory = await _crear_motor_sqlite_memoria(crear_esquema=False)
    try:
        seen_infos: list[dict[str, Any]] = []

        def _tracked_factory() -> AsyncSession:
            s = factory()
            s.sync_session.info["is_superadmin"] = True
            seen_infos.append(s.sync_session.info)
            return s

        # Torre Principal por defecto + verificación de session.sync_session.info
        r_t7 = await bootstrap_initial_admin(
            BootstrapConfig(
                condominio_id=7,
                nombre="Admin Siete",
                cedula="V-70000007",
                correo="siete@condo.test",
                telefono="+584127770007",
                password="ClaveTenantSiete2026!",
                estructura_nombre=None,
                estructura_tipo="TORRE",
                unidad_inicial="S-01",
            ),
            session_factory=_tracked_factory,
            target_engine=engine,
        )
        assert r_t7.status == "created"
        assert seen_infos[0]["tenant_id"] == "7"
        assert seen_infos[0]["is_superadmin"] is False

        # Reutilización exacta con distractores (condominio_id !=, nombre !=, tipo !=)
        async with factory() as s:
            s.add_all(
                [
                    Estructura(condominio_id=99, nombre="Torre Principal", tipo="TORRE"),
                    Estructura(condominio_id=7, nombre="Torre Principal", tipo="EDIFICIO"),
                    Estructura(condominio_id=7, nombre="Torre Luna", tipo="TORRE"),
                ]
            )
            await s.commit()

        r_s2 = await bootstrap_initial_admin(
            BootstrapConfig(
                condominio_id=7,
                nombre="Admin Siete",
                cedula="V-70000007",
                correo="siete@condo.test",
                telefono="+584127770007",
                password="ClaveTenantSiete2026!",
                estructura_nombre=None,
                estructura_tipo="TORRE",
                unidad_inicial="S-02",
                allow_update_existing=True,
            ),
            session_factory=factory,
            target_engine=engine,
        )
        assert r_s2.status == "updated"

        async with factory() as s:
            ests_match = (
                (
                    await s.execute(
                        select(Estructura).where(
                            Estructura.condominio_id == 7,
                            Estructura.nombre == "Torre Principal",
                            Estructura.tipo == "TORRE",
                        )
                    )
                )
                .scalars()
                .all()
            )
            assert len(ests_match) == 1
            u_s2 = (await s.execute(select(Unidad).where(Unidad.identificador == "S-02"))).scalars().one()
            assert u_s2.estructura_id == ests_match[0].id

            # Tupla exacta de _crear_o_actualizar_usuario (L323 y L336)
            cfg_nuevo = BootstrapConfig(
                condominio_id=7,
                nombre="Nuevo Directo",
                cedula="V-70000077",
                correo="nuevo.directo@condo.test",
                telefono="+584120007777",
                password="ClaveInicialNuevoDirecto1!",
                rol="VICEPRESIDENTE",
            )
            u_new, created_new, updated_new = await _crear_o_actualizar_usuario(s, cfg_nuevo)
            assert created_new is True
            assert updated_new is False
            assert u_new.id is not None
            assert u_new.es_activo is True
            assert u_new.rol == "VICEPRESIDENTE"
            assert u_new.condominio_id == 7
            assert verify_password("ClaveInicialNuevoDirecto1!", u_new.password_hash) is True

            u_same, created_same, updated_same = await _crear_o_actualizar_usuario(s, cfg_nuevo)
            assert u_same.id == u_new.id
            assert created_same is False
            assert updated_same is False

            cfg_upd = BootstrapConfig(
                condominio_id=7,
                nombre="Nuevo Directo Editado",
                cedula="V-70000077",
                correo="nuevo.directo@condo.test",
                telefono="+584120007777",
                password="ClaveInicialNuevoDirecto1!",
                rol="VICEPRESIDENTE",
                allow_update_existing=True,
            )
            u_upd, created_upd, updated_upd = await _crear_o_actualizar_usuario(s, cfg_upd)
            assert u_upd.id == u_new.id
            assert created_upd is False
            assert updated_upd is True

            # Cuenta revocada administrativamente (es_activo=False y rol != FANTASMA)
            s.add(
                Usuario(
                    condominio_id=7,
                    nombre="Revocado Admin",
                    cedula="V-77771111",
                    correo="revocado.admin@condo.test",
                    telefono="+584140000000",
                    password_hash="h",
                    es_activo=False,
                    rol="PROPIETARIO",
                )
            )
            await s.commit()

        with pytest.raises(ValueError, match=_ERR_REVOCADO):
            await bootstrap_initial_admin(
                BootstrapConfig(
                    condominio_id=7,
                    correo="revocado.admin@condo.test",
                    cedula="V-77771111",
                    password="ClaveSeguraReactivar1!",
                    rol="PRESIDENTE",
                    allow_update_existing=True,
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
    """Valida ejecución E2E real de main() -> _execute_cli_bootstrap -> SQLite archivo + engine.dispose()."""
    db_file = tmp_path / "cli_run.db"
    test_engine = create_async_engine(f"sqlite+aiosqlite:///{db_file}", echo=False)
    test_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    monkeypatch.setattr(bootstrap_mod, "engine", test_engine)
    monkeypatch.setattr(bootstrap_mod, "AsyncSessionLocal", test_factory)
    monkeypatch.setenv("APP_ENV", "qa_unit")
    monkeypatch.setenv("BOOTSTRAP_ADMIN_PASSWORD", "ClaveCliSegura2026!")

    exit_code = main(
        [
            "--correo",
            "cli.presi@condominio.test",
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

    conn = sqlite3.connect(db_file)
    try:
        row = conn.execute(
            "SELECT nombre, telefono, password_hash FROM usuarios WHERE correo = ?",
            ("cli.presi@condominio.test",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "Presidente CLI Env"
    assert row[1] == "+584129990000"
    assert verify_password("ClaveCliRotada2026!", row[2]) is True


@pytest.mark.asyncio
async def test_bootstrap_pbkdf2_iteraciones_reales(monkeypatch: pytest.MonkeyPatch) -> None:
    """Garantiza que sin parche el bootstrap aplica PBKDF2 completo (600_000 iteraciones)."""
    iteraciones_observadas: list[int] = []
    pbkdf2_real = hashlib.pbkdf2_hmac

    def _spy_pbkdf2(hash_name: str, password: bytes, salt: bytes, iterations: int, dklen: int | None = None) -> bytes:
        iteraciones_observadas.append(iterations)
        return pbkdf2_real(hash_name, password, salt, 1, dklen)

    monkeypatch.setattr(hashlib, "pbkdf2_hmac", _spy_pbkdf2)

    engine, sf = await _crear_motor_sqlite_memoria(crear_esquema=False)
    try:
        cfg = BootstrapConfig(correo="real@condo.test", password="ClaveReal123!Seguro")
        res = await bootstrap_initial_admin(cfg, session_factory=sf, target_engine=engine)
        assert res.status == "created"
        async with sf() as s:
            u = (await s.execute(select(Usuario).where(Usuario.correo == "real@condo.test"))).scalars().first()
            assert u is not None
            assert u.password_hash.startswith("pbkdf2_sha256$")
            assert len(u.password_hash.split("$")) == 3
            assert verify_password("ClaveReal123!Seguro", u.password_hash) is True
    finally:
        await engine.dispose()

    assert iteraciones_observadas == [PBKDF2_ITERATIONS, PBKDF2_ITERATIONS]
    assert PBKDF2_ITERATIONS == 600_000


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
