# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
"""Pruebas HTTP de integración SQLite FK para el router de administración y Junta LPH."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from decimal import Decimal
from typing import cast

import httpx
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user
from src.main import app
from src.models import ContratoOcupacion, Estructura, Unidad, Usuario
from src.redis_client import get_redis_client, reset_local_security_state
from src.security import create_access_token, get_password_hash
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base


class _FakeAsyncRedis:
    """Stub mínimo en memoria para la dependencia Redis de idempotencia."""

    def __init__(self) -> None:
        self.kv: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.kv.get(key)

    async def set(
        self,
        key: str,
        value: str,
        *,
        nx: bool = False,
        ex: int | None = None,
    ) -> bool:
        del ex
        if nx and key in self.kv:
            return False
        self.kv[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if self.kv.pop(key, None) is not None:
                deleted += 1
        return deleted


async def _cargar_usuario(factory: async_sessionmaker[AsyncSession], user_id: int) -> Usuario:
    async with factory() as session:
        return (await session.execute(select(Usuario).where(Usuario.id == user_id))).scalar_one()


async def _crear_usuario_extra(
    factory: async_sessionmaker[AsyncSession],
    *,
    nombre: str,
    cedula: str,
    correo: str,
    rol: str,
    es_activo: bool,
) -> Usuario:
    async with factory() as session:
        user = Usuario(
            condominio_id=1,
            nombre=nombre,
            cedula=cedula,
            correo=correo,
            telefono="+584140009999",
            password_hash=get_password_hash("ClaveReal11X!"),
            es_activo=es_activo,
            rol=rol,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def _instalar_overrides(
    factory: async_sessionmaker[AsyncSession],
    fake_redis: _FakeAsyncRedis,
    usuario: Usuario | None = None,
) -> None:
    async def _override_db() -> AsyncGenerator[AsyncSession]:
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis_client] = lambda: cast(aioredis.Redis, fake_redis)
    if usuario is not None:
        app.dependency_overrides[get_current_user] = lambda: usuario


async def _listar_y_asegurar_rol(
    factory: async_sessionmaker[AsyncSession],
    ctx: SeededCondoContext,
) -> None:
    fake_redis = _FakeAsyncRedis()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
        # 1. Anónimo y no-Junta reciben DTO público sin datos financieros
        try:
            _instalar_overrides(factory, fake_redis, usuario=None)
            resp_anon = await client.get("/api/estructura/unidades")
            assert resp_anon.status_code == 200
            data_anon = resp_anon.json()
            assert len(data_anon) == 2
            assert set(data_anon[0].keys()) == {"id", "identificador", "estructura_id"}

            resp_pag = await client.get("/api/estructura/unidades", params={"limit": 1, "offset": 1})
            assert resp_pag.status_code == 200
            assert [u["identificador"] for u in resp_pag.json()] == ["1-B"]
        finally:
            app.dependency_overrides.clear()

        for uid in (ctx.propietario_id, ctx.inquilino_id, ctx.conserje_id):
            user = await _cargar_usuario(factory, uid)
            try:
                _instalar_overrides(factory, fake_redis, usuario=user)
                resp = await client.get("/api/estructura/unidades")
                assert resp.status_code == 200
                assert "alicuota" not in resp.json()[0]
            finally:
                app.dependency_overrides.clear()

        # 2. Usuario Fantasma inactivo en override cae en DTO público
        fantasma = await _crear_usuario_extra(
            factory,
            nombre="Fantasma",
            cedula="V-90000001",
            correo="fantasma@condo.test",
            rol="FANTASMA",
            es_activo=False,
        )
        try:
            _instalar_overrides(factory, fake_redis, usuario=fantasma)
            resp_fan = await client.get("/api/estructura/unidades")
            assert resp_fan.status_code == 200
            assert "alicuota" not in resp_fan.json()[0]
        finally:
            app.dependency_overrides.clear()

        # 3. Miembros de la Junta reciben DTO completo con alícuota y crédito
        for uid in (ctx.presidente_id, ctx.tesorero_id, ctx.secretario_id, ctx.vocero_id):
            junta_user = await _cargar_usuario(factory, uid)
            try:
                _instalar_overrides(factory, fake_redis, usuario=junta_user)
                resp_junta = await client.get("/api/estructura/unidades")
                assert resp_junta.status_code == 200
                assert "alicuota" in resp_junta.json()[0]
                assert "credito_disponible_usd" in resp_junta.json()[0]
            finally:
                app.dependency_overrides.clear()


async def test_listar_unidades_visibilidad_junta_vs_publico() -> None:
    """Valida proyección diferencial (UnidadResponse vs UnidadPublicaResponse) y paginación."""
    reset_local_security_state()
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        await _listar_y_asegurar_rol(factory, ctx)
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_generar_estructura_rbac_idempotencia_y_conflictos() -> None:
    """Prueba POST /api/estructura/generar con RBAC, deduplicación, replay, 409 y 422."""
    reset_local_security_state()
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        fake_redis = _FakeAsyncRedis()
        presidente = await _cargar_usuario(factory, ctx.presidente_id)
        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)
        vice = await _crear_usuario_extra(
            factory,
            nombre="Vera Vice",
            cedula="V-10000099",
            correo="vice@condo.test",
            rol="VICEPRESIDENTE",
            es_activo=True,
        )

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            # Sin autenticación -> 401
            try:
                _instalar_overrides(factory, fake_redis, usuario=None)
                resp_unauth = await client.post(
                    "/api/estructura/generar",
                    headers={"Idempotency-Key": "est-unauth-001"},
                    json={"nombre": "Torre B", "tipo": "TORRE", "identificadores": ["2-A"]},
                )
                assert resp_unauth.status_code == 401
            finally:
                app.dependency_overrides.clear()

            # Tesorero no autorizado -> 403
            try:
                _instalar_overrides(factory, fake_redis, usuario=tesorero)
                resp_forb = await client.post(
                    "/api/estructura/generar",
                    headers={"Idempotency-Key": "est-forb-001"},
                    json={"nombre": "Torre B", "tipo": "TORRE", "identificadores": ["2-A"]},
                )
                assert resp_forb.status_code == 403
            finally:
                app.dependency_overrides.clear()

            # Presidente crea estructura deduplicando identificadores + replay + conflicto
            payload = {
                "nombre": "Torre Este",
                "tipo": "TORRE",
                "identificadores": ["2-A", "2-B", "2-A", "   "],
            }
            try:
                _instalar_overrides(factory, fake_redis, usuario=presidente)
                resp_no_key = await client.post("/api/estructura/generar", json=payload)
                assert resp_no_key.status_code == 422

                resp_ok = await client.post(
                    "/api/estructura/generar",
                    headers={"Idempotency-Key": "est-create-001"},
                    json=payload,
                )
                assert resp_ok.status_code == 201
                body = resp_ok.json()
                assert body["unidades_creadas"] == 2
                assert [u["identificador"] for u in body["unidades"]] == ["2-A", "2-B"]

                resp_replay = await client.post(
                    "/api/estructura/generar",
                    headers={"Idempotency-Key": "est-create-001"},
                    json=payload,
                )
                assert resp_replay.status_code == 201
                assert resp_replay.headers.get("X-Idempotency-Replayed") == "true"

                resp_diff = await client.post(
                    "/api/estructura/generar",
                    headers={"Idempotency-Key": "est-create-001"},
                    json={"nombre": "Otra", "tipo": "EDIFICIO", "identificadores": ["9-A"]},
                )
                assert resp_diff.status_code == 409

                # Identificador duplicado con existente ("1-A") -> 409 y libera slot
                resp_dup_uni = await client.post(
                    "/api/estructura/generar",
                    headers={"Idempotency-Key": "est-dup-001"},
                    json={"nombre": "Torre Dup", "tipo": "TORRE", "identificadores": ["1-A"]},
                )
                assert resp_dup_uni.status_code == 409

                resp_invalid = await client.post(
                    "/api/estructura/generar",
                    headers={"Idempotency-Key": "est-bad-001"},
                    json={"nombre": "Torre Bad", "tipo": "CASTILLO", "identificadores": []},
                )
                assert resp_invalid.status_code == 422
            finally:
                app.dependency_overrides.clear()

            # Vicepresidente también autorizado; además reusa clave liberada tras 409
            try:
                _instalar_overrides(factory, fake_redis, usuario=vice)
                resp_vice = await client.post(
                    "/api/estructura/generar",
                    headers={"Idempotency-Key": "est-dup-001"},
                    json={"nombre": "Torre Oeste", "tipo": "EDIFICIO", "identificadores": ["3-A"]},
                )
                assert resp_vice.status_code == 201
            finally:
                app.dependency_overrides.clear()

        async with factory() as session:
            estructuras = (await session.execute(select(Estructura))).scalars().all()
            unidades = (await session.execute(select(Unidad))).scalars().all()
            assert len(estructuras) == 3
            assert len(unidades) == 5
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_listar_usuarios_pendientes_y_asignar_con_historico_lph() -> None:
    """Cubre /usuarios/pendientes, jerarquía directiva, regla propietario LPH e histórico de contratos."""
    reset_local_security_state()
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        fake_redis = _FakeAsyncRedis()
        presidente = await _cargar_usuario(factory, ctx.presidente_id)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        inquilino = await _cargar_usuario(factory, ctx.inquilino_id)
        vice = await _crear_usuario_extra(
            factory,
            nombre="Vera Vice",
            cedula="V-10000098",
            correo="vice2@condo.test",
            rol="VICEPRESIDENTE",
            es_activo=True,
        )
        fantasma = await _crear_usuario_extra(
            factory,
            nombre="Lucía Fantasma",
            cedula="V-20000001",
            correo="lucia@condo.test",
            rol="FANTASMA",
            es_activo=False,
        )

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            # 1. /usuarios/pendientes RBAC y resultados
            try:
                _instalar_overrides(factory, fake_redis, usuario=propietario)
                assert (await client.get("/api/usuarios/pendientes")).status_code == 403
            finally:
                app.dependency_overrides.clear()

            try:
                _instalar_overrides(factory, fake_redis, usuario=vice)
                resp_pend = await client.get("/api/usuarios/pendientes")
                assert resp_pend.status_code == 200
                assert [u["id"] for u in resp_pend.json()] == [fantasma.id]

                # 2. Jerarquía: VICEPRESIDENTE no puede asignar PRESIDENTE ni modificar al PRESIDENTE
                resp_esc = await client.put(
                    f"/api/usuarios/{fantasma.id}/asignar",
                    headers={"Idempotency-Key": "asig-esc-001"},
                    json={"unidad_id": ctx.unidad_a_id, "tipo_ocupante": "PROPIETARIO", "rol": "PRESIDENTE"},
                )
                assert resp_esc.status_code == 403

                resp_mod_pres = await client.put(
                    f"/api/usuarios/{presidente.id}/asignar",
                    headers={"Idempotency-Key": "asig-esc-002"},
                    json={"unidad_id": ctx.unidad_a_id, "tipo_ocupante": "PROPIETARIO", "rol": "VOCERO"},
                )
                assert resp_mod_pres.status_code == 403

                # 404 usuario y unidad inexistentes
                assert (
                    await client.put(
                        "/api/usuarios/99999/asignar",
                        headers={"Idempotency-Key": "asig-404-u"},
                        json={"unidad_id": ctx.unidad_a_id, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
                    )
                ).status_code == 404
                assert (
                    await client.put(
                        f"/api/usuarios/{fantasma.id}/asignar",
                        headers={"Idempotency-Key": "asig-404-uni"},
                        json={"unidad_id": 99999, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
                    )
                ).status_code == 404

                # 3. Regla LPH: inquilino sin contrato de propietario activo no puede ocupar cargo Junta
                resp_inq_junta = await client.put(
                    f"/api/usuarios/{inquilino.id}/asignar",
                    headers={"Idempotency-Key": "asig-lph-400"},
                    json={"unidad_id": ctx.unidad_b_id, "tipo_ocupante": "INQUILINO", "rol": "TESORERO"},
                )
                assert resp_inq_junta.status_code == 400

                # 4. Activación de Fantasma como PROPIETARIO en unidad_a
                resp_act = await client.put(
                    f"/api/usuarios/{fantasma.id}/asignar",
                    headers={"Idempotency-Key": "asig-act-001"},
                    json={"unidad_id": ctx.unidad_a_id, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
                )
                assert resp_act.status_code == 200
                assert resp_act.json()["es_activo"] is True
                assert resp_act.json()["rol"] == "PROPIETARIO"

                # Replay idempotente
                resp_act_replay = await client.put(
                    f"/api/usuarios/{fantasma.id}/asignar",
                    headers={"Idempotency-Key": "asig-act-001"},
                    json={"unidad_id": ctx.unidad_a_id, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
                )
                assert resp_act_replay.status_code == 200
                assert resp_act_replay.headers.get("X-Idempotency-Replayed") == "true"

                # 5. Usuario con contrato PROPIETARIO activo en unidad_a puede ser VOCERO en unidad_b
                resp_vocero_b = await client.put(
                    f"/api/usuarios/{propietario.id}/asignar",
                    headers={"Idempotency-Key": "asig-prop-b"},
                    json={
                        "unidad_id": ctx.unidad_b_id,
                        "tipo_ocupante": "INQUILINO",
                        "rol": "VOCERO",
                        "puede_votar_asamblea": False,
                    },
                )
                assert resp_vocero_b.status_code == 200
            finally:
                app.dependency_overrides.clear()

            # 6. Presidente reasigna a Fantasma en misma unidad con mismo tipo (reuso) y luego distinto tipo (cierre)
            try:
                _instalar_overrides(factory, fake_redis, usuario=presidente)
                resp_reuso = await client.put(
                    f"/api/usuarios/{fantasma.id}/asignar",
                    headers={"Idempotency-Key": "asig-reuso-001"},
                    json={
                        "unidad_id": ctx.unidad_a_id,
                        "tipo_ocupante": "PROPIETARIO",
                        "rol": "SECRETARIO",
                        "puede_votar_asamblea": False,
                    },
                )
                assert resp_reuso.status_code == 200

                resp_cambio_tipo = await client.put(
                    f"/api/usuarios/{fantasma.id}/asignar",
                    headers={"Idempotency-Key": "asig-tipo-002"},
                    json={"unidad_id": ctx.unidad_a_id, "tipo_ocupante": "INQUILINO", "rol": "INQUILINO"},
                )
                assert resp_cambio_tipo.status_code == 200
            finally:
                app.dependency_overrides.clear()

        async with factory() as session:
            contratos_fan = (
                (
                    await session.execute(
                        select(ContratoOcupacion)
                        .where(ContratoOcupacion.usuario_id == fantasma.id)
                        .order_by(ContratoOcupacion.id.asc())
                    )
                )
                .scalars()
                .all()
            )
            assert len(contratos_fan) == 2
            assert contratos_fan[0].es_activo is False
            assert contratos_fan[0].fecha_fin is not None
            assert contratos_fan[0].tipo_ocupante == "PROPIETARIO"
            assert contratos_fan[1].es_activo is True
            assert contratos_fan[1].tipo_ocupante == "INQUILINO"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_junta_cargos_alicuota_y_jwt_real() -> None:
    """Prueba PUT /api/junta/cargos, PUT /api/estructura/unidades/{id}/alicuota y auth JWT real."""
    reset_local_security_state()
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        fake_redis = _FakeAsyncRedis()
        presidente = await _cargar_usuario(factory, ctx.presidente_id)
        tesorero = await _cargar_usuario(factory, ctx.tesorero_id)
        secretario = await _cargar_usuario(factory, ctx.secretario_id)
        fantasma = await _crear_usuario_extra(
            factory,
            nombre="Inactivo",
            cedula="V-30000001",
            correo="inactivo@condo.test",
            rol="FANTASMA",
            es_activo=False,
        )
        vice = await _crear_usuario_extra(
            factory,
            nombre="Vice Test",
            cedula="V-30000002",
            correo="vice3@condo.test",
            rol="VICEPRESIDENTE",
            es_activo=True,
        )

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            # Solo PRESIDENTE puede asignar cargos de Junta
            try:
                _instalar_overrides(factory, fake_redis, usuario=vice)
                resp_vice_junta = await client.put(
                    "/api/junta/cargos",
                    headers={"Idempotency-Key": "junta-forb-001"},
                    json={"usuario_id": ctx.propietario_id, "cargo": "TESORERO"},
                )
                assert resp_vice_junta.status_code == 403
            finally:
                app.dependency_overrides.clear()

            try:
                _instalar_overrides(factory, fake_redis, usuario=presidente)
                assert (
                    await client.put(
                        "/api/junta/cargos",
                        headers={"Idempotency-Key": "junta-404-001"},
                        json={"usuario_id": 99999, "cargo": "VOCERO"},
                    )
                ).status_code == 404

                assert (
                    await client.put(
                        "/api/junta/cargos",
                        headers={"Idempotency-Key": "junta-400-inact"},
                        json={"usuario_id": fantasma.id, "cargo": "VOCERO"},
                    )
                ).status_code == 400

                assert (
                    await client.put(
                        "/api/junta/cargos",
                        headers={"Idempotency-Key": "junta-400-inq"},
                        json={"usuario_id": ctx.inquilino_id, "cargo": "TESORERO"},
                    )
                ).status_code == 400

                assert (
                    await client.put(
                        "/api/junta/cargos",
                        headers={"Idempotency-Key": "junta-422-cargo"},
                        json={"usuario_id": ctx.propietario_id, "cargo": "CARGO_INEXISTENTE"},
                    )
                ).status_code == 422

                resp_cargo = await client.put(
                    "/api/junta/cargos",
                    headers={"Idempotency-Key": "junta-ok-001"},
                    json={"usuario_id": ctx.propietario_id, "cargo": "TESORERO"},
                )
                assert resp_cargo.status_code == 200
                assert resp_cargo.json()["rol"] == "TESORERO"
            finally:
                app.dependency_overrides.clear()

            # Alícuotas: secretario prohibido (403); tesorero permitido; 404 y 422
            try:
                _instalar_overrides(factory, fake_redis, usuario=secretario)
                assert (
                    await client.put(
                        f"/api/estructura/unidades/{ctx.unidad_a_id}/alicuota",
                        headers={"Idempotency-Key": "alic-forb-001"},
                        json={"alicuota": "50.0000"},
                    )
                ).status_code == 403
            finally:
                app.dependency_overrides.clear()

            try:
                _instalar_overrides(factory, fake_redis, usuario=tesorero)
                assert (
                    await client.put(
                        "/api/estructura/unidades/99999/alicuota",
                        headers={"Idempotency-Key": "alic-404-001"},
                        json={"alicuota": "50.0000"},
                    )
                ).status_code == 404

                assert (
                    await client.put(
                        f"/api/estructura/unidades/{ctx.unidad_a_id}/alicuota",
                        headers={"Idempotency-Key": "alic-422-001"},
                        json={"alicuota": "100.0001"},
                    )
                ).status_code == 422

                resp_alic = await client.put(
                    f"/api/estructura/unidades/{ctx.unidad_a_id}/alicuota",
                    headers={"Idempotency-Key": "alic-ok-001"},
                    json={"alicuota": "55.12349", "cuota_fija_usd": "125.556"},
                )
                assert resp_alic.status_code == 200
                assert Decimal(resp_alic.json()["alicuota"]) == Decimal("55.1235")
                assert Decimal(resp_alic.json()["cuota_fija_usd"]) == Decimal("125.56")

                # Limpiar cuota_fija_usd con None
                resp_clear = await client.put(
                    f"/api/estructura/unidades/{ctx.unidad_a_id}/alicuota",
                    headers={"Idempotency-Key": "alic-ok-002"},
                    json={"alicuota": "60.0000", "cuota_fija_usd": None},
                )
                assert resp_clear.status_code == 200
                assert resp_clear.json()["cuota_fija_usd"] is None
            finally:
                app.dependency_overrides.clear()

            # Validación real de JWT Bearer sin override de get_current_user
            token_tes = create_access_token({"sub": tesorero.correo, "condominio_id": 1, "sid": "sid-real-1"})
            try:
                _instalar_overrides(factory, fake_redis, usuario=None)
                resp_jwt = await client.get(
                    "/api/estructura/unidades",
                    headers={"Authorization": f"Bearer {token_tes}"},
                )
                assert resp_jwt.status_code == 200
                assert "alicuota" in resp_jwt.json()[0]
            finally:
                app.dependency_overrides.clear()
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
