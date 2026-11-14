# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Condominio App Contributors
"""CLI idempotente de bootstrap Día 0 para inicializar el primer administrador y condominio."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Literal, cast

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.future import select

from src.database import AsyncSessionLocal, Base, engine
from src.models import ContratoOcupacion, Estructura, Unidad, Usuario
from src.schemas import _validar_correo
from src.security import get_password_hash, validate_production_security_settings, verify_password

ROLES_BOOTSTRAP_PERMITIDOS: tuple[str, ...] = ("PRESIDENTE", "VICEPRESIDENTE", "TESORERO", "SECRETARIO")
TIPOS_ESTRUCTURA_PERMITIDOS: tuple[str, ...] = ("EDIFICIO", "TORRE", "BLOQUE", "MANZANA", "CALLE")
_PASSWORDS_PROHIBIDOS: frozenset[str] = frozenset({"changeme", "password1234", "123456789012", "admin1234567"})
_MIN_PASSWORD_LEN = 12


_CLI_OVERRIDE_FIELDS: tuple[str, ...] = (
    "condominio_id",
    "nombre",
    "cedula",
    "correo",
    "telefono",
    "password",
    "rol",
    "estructura_nombre",
    "estructura_tipo",
    "unidad_inicial",
)


def _env_str(name: str, default: str = "") -> str:
    valor = os.getenv(name, "").strip()
    return valor if valor else default


def _env_int_pos(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un entero positivo.") from exc


@dataclass(frozen=True, slots=True)
class BootstrapConfig:
    """Parámetros tipados para inicializar un administrador de condominio en Día 0."""

    correo: str
    password: str
    condominio_id: int = 1
    nombre: str = "Presidente Junta Inicial"
    cedula: str = "V-00000001"
    telefono: str = "+584120000000"
    rol: str = "PRESIDENTE"
    estructura_nombre: str | None = None
    estructura_tipo: str = "TORRE"
    unidad_inicial: str | None = None
    allow_update_existing: bool = False

    @classmethod
    def from_env(cls) -> BootstrapConfig:
        """Construye la configuración leyendo variables de entorno BOOTSTRAP_*."""
        return cls(
            condominio_id=_env_int_pos("BOOTSTRAP_CONDOMINIO_ID", 1),
            nombre=_env_str("BOOTSTRAP_ADMIN_NOMBRE", "Presidente Junta Inicial"),
            cedula=_env_str("BOOTSTRAP_ADMIN_CEDULA", "V-00000001"),
            correo=_env_str("BOOTSTRAP_ADMIN_CORREO").lower(),
            telefono=_env_str("BOOTSTRAP_ADMIN_TELEFONO", "+584120000000"),
            password=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", ""),
            rol=_env_str("BOOTSTRAP_ADMIN_ROL", "PRESIDENTE").upper(),
            estructura_nombre=_env_str("BOOTSTRAP_ESTRUCTURA_NOMBRE") or None,
            estructura_tipo=_env_str("BOOTSTRAP_ESTRUCTURA_TIPO", "TORRE").upper(),
            unidad_inicial=_env_str("BOOTSTRAP_UNIDAD_INICIAL") or None,
            allow_update_existing=os.getenv("BOOTSTRAP_ALLOW_UPDATE", "").strip().lower() in {"1", "true", "yes"},
        )


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """Resultado estructurado de la operación idempotente de bootstrap."""

    status: Literal["created", "updated", "unchanged", "skipped"]
    usuario_id: int | None
    correo: str
    rol: str
    condominio_id: int
    unidad_id: int | None = None


def _validar_password_bootstrap(password: str) -> str:
    if len(password) < _MIN_PASSWORD_LEN:
        raise ValueError("La contraseña de bootstrap debe tener al menos 12 caracteres.")
    lower = password.strip().lower()
    if "cambiar_placeholder" in lower or lower in _PASSWORDS_PROHIBIDOS:
        raise ValueError("La contraseña de bootstrap no puede usar valores placeholder o triviales.")
    return password


def _validar_config(cfg: BootstrapConfig) -> BootstrapConfig:
    if cfg.condominio_id < 1:
        raise ValueError("condominio_id debe ser mayor o igual a 1.")
    nombre = cfg.nombre.strip()
    cedula = cfg.cedula.strip()
    telefono = cfg.telefono.strip()
    if not nombre or not cedula or not telefono:
        raise ValueError("nombre, cedula y telefono son obligatorios.")
    correo_norm = _validar_correo(cfg.correo.strip().lower()).lower()
    password_val = _validar_password_bootstrap(cfg.password)
    rol_norm = cfg.rol.strip().upper()
    if rol_norm not in ROLES_BOOTSTRAP_PERMITIDOS:
        raise ValueError(f"Rol de bootstrap inválido: {rol_norm}")
    tipo_norm = cfg.estructura_tipo.strip().upper()
    if tipo_norm not in TIPOS_ESTRUCTURA_PERMITIDOS:
        raise ValueError(f"Tipo de estructura inválido: {tipo_norm}")
    unidad_norm = cfg.unidad_inicial.strip() if cfg.unidad_inicial else None
    est_norm = cfg.estructura_nombre.strip() if cfg.estructura_nombre else None
    return BootstrapConfig(
        condominio_id=cfg.condominio_id,
        nombre=nombre,
        cedula=cedula,
        correo=correo_norm,
        telefono=telefono,
        password=password_val,
        rol=rol_norm,
        estructura_nombre=est_norm,
        estructura_tipo=tipo_norm,
        unidad_inicial=unidad_norm or None,
        allow_update_existing=cfg.allow_update_existing,
    )


async def _asegurar_esquema_sqlite(target_engine: AsyncEngine) -> None:
    if target_engine.dialect.name != "sqlite":
        return
    async with target_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def _buscar_usuario_existente(
    session: AsyncSession,
    correo: str,
    cedula: str,
) -> Usuario | None:
    res_correo = await session.execute(select(Usuario).where(Usuario.correo == correo))
    user_correo = res_correo.scalars().first()
    res_cedula = await session.execute(select(Usuario).where(Usuario.cedula == cedula))
    user_cedula = res_cedula.scalars().first()
    if user_correo is not None and user_cedula is not None and user_correo.id != user_cedula.id:
        raise ValueError("Conflicto de identidad: correo y cédula pertenecen a registros distintos.")
    return user_correo or user_cedula


async def _asegurar_estructura_y_unidad(
    session: AsyncSession,
    cfg: BootstrapConfig,
) -> Unidad | None:
    if cfg.unidad_inicial is None:
        return None
    res_unidad = await session.execute(select(Unidad).where(Unidad.identificador == cfg.unidad_inicial))
    unidad = res_unidad.scalars().first()
    if unidad is not None:
        if unidad.condominio_id != cfg.condominio_id:
            raise ValueError("La unidad inicial pertenece a otro condominio_id.")
        return unidad

    est_nombre = cfg.estructura_nombre or "Torre Principal"
    res_est = await session.execute(
        select(Estructura).where(
            Estructura.condominio_id == cfg.condominio_id,
            Estructura.nombre == est_nombre,
            Estructura.tipo == cfg.estructura_tipo,
        )
    )
    estructura = res_est.scalars().first()
    if estructura is None:
        estructura = Estructura(condominio_id=cfg.condominio_id, nombre=est_nombre, tipo=cfg.estructura_tipo)
        session.add(estructura)
        await session.flush()

    unidad = Unidad(
        condominio_id=cfg.condominio_id,
        identificador=cfg.unidad_inicial,
        estructura_id=estructura.id,
        alicuota=Decimal("0.0000"),
        cuota_fija_usd=None,
        credito_disponible_usd=Decimal("0.00"),
    )
    session.add(unidad)
    await session.flush()
    return unidad


async def _asegurar_contrato_inicial(
    session: AsyncSession,
    usuario: Usuario,
    unidad: Unidad | None,
    condominio_id: int,
) -> bool:
    if unidad is None:
        return False
    res = await session.execute(
        select(ContratoOcupacion).where(
            ContratoOcupacion.usuario_id == usuario.id,
            ContratoOcupacion.unidad_id == unidad.id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.fecha_fin.is_(None),
        )
    )
    if res.scalars().first() is not None:
        return False

    res_prev = await session.execute(
        select(ContratoOcupacion).where(
            ContratoOcupacion.usuario_id == usuario.id,
            ContratoOcupacion.es_activo.is_(True),
            ContratoOcupacion.fecha_fin.is_(None),
        )
    )
    ahora = datetime.now(UTC)
    for previo in res_prev.scalars().all():
        previo.es_activo = False
        previo.fecha_fin = ahora

    session.add(
        ContratoOcupacion(
            condominio_id=condominio_id,
            usuario_id=usuario.id,
            unidad_id=unidad.id,
            tipo_ocupante="PROPIETARIO",
            es_activo=True,
            puede_votar_asamblea=True,
        )
    )
    return True


def _aplicar_actualizacion_usuario(user: Usuario, cfg: BootstrapConfig) -> bool:
    changed = False
    if not user.es_activo:
        user.es_activo = True
        changed = True
    if user.rol != cfg.rol:
        user.rol = cfg.rol
        changed = True
    if not cfg.allow_update_existing:
        return changed
    if user.nombre != cfg.nombre:
        user.nombre = cfg.nombre
        changed = True
    if user.telefono != cfg.telefono:
        user.telefono = cfg.telefono
        changed = True
    if not verify_password(cfg.password, user.password_hash):
        user.password_hash = get_password_hash(cfg.password)
        changed = True
    return changed


async def _persistir_bootstrap(session: AsyncSession, cfg: BootstrapConfig) -> BootstrapResult:
    user = await _buscar_usuario_existente(session, cfg.correo, cfg.cedula)
    created = False
    changed = False

    if user is None:
        user = Usuario(
            condominio_id=cfg.condominio_id,
            nombre=cfg.nombre,
            cedula=cfg.cedula,
            correo=cfg.correo,
            telefono=cfg.telefono,
            password_hash=get_password_hash(cfg.password),
            es_activo=True,
            rol=cfg.rol,
        )
        session.add(user)
        await session.flush()
        created = True
    else:
        changed = _aplicar_actualizacion_usuario(user, cfg)

    unidad = await _asegurar_estructura_y_unidad(session, cfg)
    contrato_creado = await _asegurar_contrato_inicial(session, user, unidad, cfg.condominio_id)

    usuario_id = user.id
    correo_usuario = user.correo
    rol_usuario = user.rol
    unidad_id = unidad.id if unidad is not None else None

    if created or changed or contrato_creado:
        await session.commit()
        status: Literal["created", "updated", "unchanged"] = "created" if created else "updated"
    else:
        await session.rollback()
        status = "unchanged"

    return BootstrapResult(
        status=status,
        usuario_id=usuario_id,
        correo=correo_usuario,
        rol=rol_usuario,
        condominio_id=cfg.condominio_id,
        unidad_id=unidad_id,
    )


async def bootstrap_initial_admin(
    cfg: BootstrapConfig,
    *,
    session_factory: Callable[[], AsyncSession] | None = None,
    target_engine: AsyncEngine | None = None,
) -> BootstrapResult:
    """Ejecuta el bootstrap idempotente del administrador Día 0 bajo aislamiento RLS."""
    validate_production_security_settings()
    clean_cfg = _validar_config(cfg)

    active_engine = target_engine or engine
    active_factory = session_factory or cast(Callable[[], AsyncSession], AsyncSessionLocal)
    await _asegurar_esquema_sqlite(active_engine)

    async with active_factory() as session:
        session.sync_session.info["tenant_id"] = str(clean_cfg.condominio_id)
        session.sync_session.info["is_superadmin"] = False
        return await _persistir_bootstrap(session, clean_cfg)


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m src.bootstrap",
        description="Inicialización idempotente Día 0 de administrador/presidente de condominio.",
    )
    parser.add_argument("--from-env", action="store_true", help="Lee la configuración desde BOOTSTRAP_*.")
    parser.add_argument("--condominio-id", type=int, default=None, help="Identificador entero del tenant/condominio.")
    parser.add_argument("--nombre", default=None, help="Nombre completo del administrador inicial.")
    parser.add_argument("--cedula", default=None, help="Cédula o documento único.")
    parser.add_argument("--correo", default=None, help="Correo electrónico del administrador inicial.")
    parser.add_argument("--telefono", default=None, help="Teléfono de contacto.")
    parser.add_argument("--password", default=None, help="Contraseña inicial (o BOOTSTRAP_ADMIN_PASSWORD).")
    parser.add_argument("--rol", default=None, help="Rol inicial de Junta (PRESIDENTE/VICEPRESIDENTE/TESORERO).")
    parser.add_argument("--estructura-nombre", default=None, help="Nombre de estructura inicial opcional.")
    parser.add_argument("--estructura-tipo", default=None, help="Tipo de estructura inicial (TORRE, EDIFICIO, etc.).")
    parser.add_argument("--unidad-inicial", default=None, help="Identificador de unidad inicial opcional.")
    parser.add_argument(
        "--allow-update-existing",
        action="store_true",
        help="Permite actualizar nombre, teléfono y contraseña si el usuario ya existe.",
    )
    return parser


def _resolve_cli_config(args: argparse.Namespace) -> BootstrapConfig:
    if args.from_env:
        base = BootstrapConfig.from_env()
    else:
        base = BootstrapConfig(
            correo=os.getenv("BOOTSTRAP_ADMIN_CORREO", "").strip().lower(),
            password=os.getenv("BOOTSTRAP_ADMIN_PASSWORD", ""),
        )
    overrides: dict[str, Any] = {
        field: getattr(args, field) for field in _CLI_OVERRIDE_FIELDS if getattr(args, field) is not None
    }
    if args.allow_update_existing:
        overrides["allow_update_existing"] = True
    return replace(base, **overrides)


async def _execute_cli_bootstrap(cfg: BootstrapConfig) -> BootstrapResult:
    try:
        return await bootstrap_initial_admin(cfg)
    finally:
        await engine.dispose()


def main(argv: Sequence[str] | None = None) -> int:
    """Punto de entrada CLI seguro (cumple contrato QA-CLI-TTY-01 sin lectura bloqueante)."""
    effective_argv = list(sys.argv[1:] if argv is None else argv)
    parser = _build_cli_parser()
    if not effective_argv:
        parser.print_help()
        return 0

    args = parser.parse_args(effective_argv)
    if args.from_env and not (args.correo or os.getenv("BOOTSTRAP_ADMIN_CORREO", "").strip()):
        print(json.dumps({"status": "skipped", "reason": "BOOTSTRAP_ADMIN_CORREO no definido"}, ensure_ascii=False))
        return 0

    try:
        cfg = _resolve_cli_config(args)
        result = asyncio.run(_execute_cli_bootstrap(cfg))
    except (ValueError, RuntimeError) as exc:
        print(f"Error de bootstrap Día 0: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(asdict(result), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
