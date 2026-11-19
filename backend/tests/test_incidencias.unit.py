# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Jesús Palencia <sinfallas@gmail.com> (Creado en Tecno Consultores)
"""Pruebas HTTP de integración SQLite FK para el router de incidencias vecinales."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator
from typing import cast

import httpx
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select

from src.database import get_db
from src.dependencies import get_current_user
from src.main import app
from src.models import Incidencia, IncidenciaAdhesion, Usuario
from src.redis_client import get_redis_client, reset_local_security_state
from src.security import create_access_token, get_password_hash
from tests._sqlite_helpers import create_sqlite_fk_factory, seed_condo_base


class _FakeAsyncRedis:
    """Stub mínimo en memoria para idempotencia y cola de notificaciones KeyDB."""

    def __init__(self) -> None:
        self.kv: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}

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

    async def rpush(self, key: str, *values: str) -> int:
        bucket = self.lists.setdefault(key, [])
        bucket.extend(values)
        return len(bucket)


async def _cargar_usuario(factory: async_sessionmaker[AsyncSession], user_id: int) -> Usuario:
    async with factory() as session:
        return (await session.execute(select(Usuario).where(Usuario.id == user_id))).scalar_one()


async def _crear_fantasma(factory: async_sessionmaker[AsyncSession]) -> Usuario:
    async with factory() as session:
        user = Usuario(
            condominio_id=1,
            nombre="Pendiente Vecino",
            cedula="V-77700001",
            correo="fantasma.inc@condo.test",
            telefono="+584140008888",
            password_hash=get_password_hash("ClaveReal11X!"),
            es_activo=False,
            rol="FANTASMA",
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


async def test_listar_incidencias_abiertas_filtros_orden_y_rbac() -> None:
    """Valida GET /api/incidencias/abiertas: 401/403, filtro de estado, orden por adhesiones y paginación."""
    reset_local_security_state()
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        fake_redis = _FakeAsyncRedis()
        fantasma = await _crear_fantasma(factory)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        conserje = await _cargar_usuario(factory, ctx.conserje_id)
        inquilino = await _cargar_usuario(factory, ctx.inquilino_id)

        async with factory() as session:
            inc_menor = Incidencia(
                condominio_id=1,
                usuario_creador_id=ctx.propietario_id,
                area="Pasillo Piso 1",
                descripcion="Bombillo quemado",
                estado="ABIERTO",
                adhesiones_count=1,
            )
            inc_mayor = Incidencia(
                condominio_id=1,
                usuario_creador_id=ctx.inquilino_id,
                area="Ascensor",
                descripcion="Ruido en polea",
                estado="EN_PROCESO",
                adhesiones_count=5,
            )
            inc_cerrada = Incidencia(
                condominio_id=1,
                usuario_creador_id=ctx.conserje_id,
                area="Portón",
                descripcion="Reparado ayer",
                estado="CERRADO",
                adhesiones_count=20,
            )
            session.add_all([inc_menor, inc_mayor, inc_cerrada])
            await session.commit()

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            try:
                _instalar_overrides(factory, fake_redis, usuario=None)
                assert (await client.get("/api/incidencias/abiertas")).status_code == 401
            finally:
                app.dependency_overrides.clear()

            try:
                _instalar_overrides(factory, fake_redis, usuario=fantasma)
                assert (await client.get("/api/incidencias/abiertas")).status_code == 403
            finally:
                app.dependency_overrides.clear()

            for user in (propietario, conserje, inquilino):
                try:
                    _instalar_overrides(factory, fake_redis, usuario=user)
                    resp = await client.get("/api/incidencias/abiertas")
                    assert resp.status_code == 200
                    areas = [item["area"] for item in resp.json()]
                    assert areas == ["Ascensor", "Pasillo Piso 1"]
                finally:
                    app.dependency_overrides.clear()

            try:
                _instalar_overrides(factory, fake_redis, usuario=propietario)
                resp_pag = await client.get("/api/incidencias/abiertas", params={"limit": 1, "offset": 1})
                assert resp_pag.status_code == 200
                assert [item["area"] for item in resp_pag.json()] == ["Pasillo Piso 1"]
                assert (await client.get("/api/incidencias/abiertas", params={"limit": 0})).status_code == 422
            finally:
                app.dependency_overrides.clear()
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_crear_incidencia_idempotencia_validaciones_notificacion_y_error_fk() -> None:
    """Cubre POST /api/incidencias/crear: 201, cola KeyDB, idempotencia, 403, 422, 500 y JWT real."""
    reset_local_security_state()
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        fake_redis = _FakeAsyncRedis()
        fantasma = await _crear_fantasma(factory)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        conserje = await _cargar_usuario(factory, ctx.conserje_id)

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            # 401 sin token
            try:
                _instalar_overrides(factory, fake_redis, usuario=None)
                assert (
                    await client.post(
                        "/api/incidencias/crear",
                        headers={"Idempotency-Key": "inc-unauth-001"},
                        json={"area": "Jardín", "descripcion": "Fuga de agua"},
                    )
                ).status_code == 401
            finally:
                app.dependency_overrides.clear()

            # 403 usuario fantasma
            try:
                _instalar_overrides(factory, fake_redis, usuario=fantasma)
                assert (
                    await client.post(
                        "/api/incidencias/crear",
                        headers={"Idempotency-Key": "inc-fan-001"},
                        json={"area": "Jardín", "descripcion": "Fuga de agua"},
                    )
                ).status_code == 403
            finally:
                app.dependency_overrides.clear()

            # Creación válida + cola de correo + replay + conflicto + validaciones 422
            payload = {
                "area": "Cuarto de Bombas",
                "descripcion": "Bomba auxiliar presenta vibración continua.",
                "url_foto": "https://cdn.condo.test/evidencia.avif",
            }
            try:
                _instalar_overrides(factory, fake_redis, usuario=propietario)
                assert (await client.post("/api/incidencias/crear", json=payload)).status_code == 422
                assert (
                    await client.post(
                        "/api/incidencias/crear",
                        headers={"Idempotency-Key": "corta"},
                        json=payload,
                    )
                ).status_code == 422

                resp_ok = await client.post(
                    "/api/incidencias/crear",
                    headers={"Idempotency-Key": "inc-create-001"},
                    json=payload,
                )
                assert resp_ok.status_code == 201
                body = resp_ok.json()
                assert body["estado"] == "ABIERTO"
                assert body["adhesiones_count"] == 1
                assert body["usuario_creador_id"] == propietario.id

                notif_queue = fake_redis.lists.get("queue:notifications", [])
                assert len(notif_queue) == 1
                evento = json.loads(notif_queue[0])
                assert evento["destinatarios"] == ["junta@condominio.local"]
                assert "Cuarto de Bombas" in evento["asunto"]

                # Replay idempotente no duplica fila ni correo
                resp_rep = await client.post(
                    "/api/incidencias/crear",
                    headers={"Idempotency-Key": "inc-create-001"},
                    json=payload,
                )
                assert resp_rep.status_code == 201
                assert resp_rep.headers.get("X-Idempotency-Replayed") == "true"
                assert len(fake_redis.lists["queue:notifications"]) == 1

                # Misma key con distinto body -> 409
                resp_conf = await client.post(
                    "/api/incidencias/crear",
                    headers={"Idempotency-Key": "inc-create-001"},
                    json={"area": "Azotea", "descripcion": "Cambio distinto"},
                )
                assert resp_conf.status_code == 409

                # URL insegura Anti-XSS -> 422
                resp_xss = await client.post(
                    "/api/incidencias/crear",
                    headers={"Idempotency-Key": "inc-xss-001"},
                    json={"area": "Lobby", "descripcion": "Prueba", "url_foto": "javascript:alert(1)"},
                )
                assert resp_xss.status_code == 422
            finally:
                app.dependency_overrides.clear()

            # Otro usuario puede usar exactamente la misma Idempotency-Key (aislamiento por usuario)
            try:
                _instalar_overrides(factory, fake_redis, usuario=conserje)
                resp_otro = await client.post(
                    "/api/incidencias/crear",
                    headers={"Idempotency-Key": "inc-create-001"},
                    json={"area": "Garita", "descripcion": "Cerradura floja", "url_foto": "/media/garita.avif"},
                )
                assert resp_otro.status_code == 201
            finally:
                app.dependency_overrides.clear()

            # Error interno DB (FK violada con usuario_id inexistente) -> 500 + rollback + libera idempotencia
            usuario_huerfano = Usuario(
                id=999999,
                condominio_id=1,
                nombre="Huérfano FK",
                cedula="V-99999999",
                correo="huerfano@condo.test",
                telefono="+584140000000",
                password_hash="x",
                es_activo=True,
                rol="PROPIETARIO",
            )
            try:
                _instalar_overrides(factory, fake_redis, usuario=usuario_huerfano)
                resp_500 = await client.post(
                    "/api/incidencias/crear",
                    headers={"Idempotency-Key": "inc-fk-error-001"},
                    json={"area": "Techo", "descripcion": "Falla simulada FK"},
                )
                assert resp_500.status_code == 500
            finally:
                app.dependency_overrides.clear()

            # JWT real sin override de get_current_user
            token_cons = create_access_token({"sub": conserje.correo, "condominio_id": 1, "sid": "sid-inc-1"})
            try:
                _instalar_overrides(factory, fake_redis, usuario=None)
                resp_jwt = await client.post(
                    "/api/incidencias/crear",
                    headers={
                        "Authorization": f"Bearer {token_cons}",
                        "Idempotency-Key": "inc-jwt-001",
                    },
                    json={"area": "Estacionamiento", "descripcion": "Lámpara intermitente"},
                )
                assert resp_jwt.status_code == 201
            finally:
                app.dependency_overrides.clear()

        async with factory() as session:
            incs = (await session.execute(select(Incidencia))).scalars().all()
            adhs = (await session.execute(select(IncidenciaAdhesion))).scalars().all()
            assert len(incs) == 3
            assert len(adhs) == 3
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def test_adherir_incidencia_me_sumo_duplicados_cerrada_y_404() -> None:
    """Cubre POST /api/incidencias/{id}/adherir: incremento, replay, 404, 409 cerrada y 409 duplicada."""
    reset_local_security_state()
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        fake_redis = _FakeAsyncRedis()
        fantasma = await _crear_fantasma(factory)
        propietario = await _cargar_usuario(factory, ctx.propietario_id)
        inquilino = await _cargar_usuario(factory, ctx.inquilino_id)
        conserje = await _cargar_usuario(factory, ctx.conserje_id)
        presidente = await _cargar_usuario(factory, ctx.presidente_id)

        async with factory() as session:
            inc_abierta = Incidencia(
                condominio_id=1,
                usuario_creador_id=ctx.propietario_id,
                area="Piscina",
                descripcion="Filtro obstruido",
                estado="ABIERTO",
                adhesiones_count=1,
            )
            inc_cerrada = Incidencia(
                condominio_id=1,
                usuario_creador_id=ctx.propietario_id,
                area="Salón",
                descripcion="Aire reparado",
                estado="CERRADO",
                adhesiones_count=2,
            )
            session.add_all([inc_abierta, inc_cerrada])
            await session.flush()
            session.add(
                IncidenciaAdhesion(condominio_id=1, incidencia_id=inc_abierta.id, usuario_id=ctx.propietario_id)
            )
            await session.commit()
            abierta_id = inc_abierta.id
            cerrada_id = inc_cerrada.id

        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://localhost") as client:
            try:
                _instalar_overrides(factory, fake_redis, usuario=fantasma)
                assert (
                    await client.post(
                        f"/api/incidencias/{abierta_id}/adherir",
                        headers={"Idempotency-Key": "adh-fan-001"},
                    )
                ).status_code == 403
            finally:
                app.dependency_overrides.clear()

            # Propietario creador ya adherido -> 409; 404 inexistente; 409 incidencia cerrada
            try:
                _instalar_overrides(factory, fake_redis, usuario=propietario)
                assert (
                    await client.post(
                        "/api/incidencias/99999/adherir",
                        headers={"Idempotency-Key": "adh-404-001"},
                    )
                ).status_code == 404
                assert (
                    await client.post(
                        f"/api/incidencias/{cerrada_id}/adherir",
                        headers={"Idempotency-Key": "adh-closed-001"},
                    )
                ).status_code == 409
                assert (
                    await client.post(
                        f"/api/incidencias/{abierta_id}/adherir",
                        headers={"Idempotency-Key": "adh-dup-creador"},
                    )
                ).status_code == 409
            finally:
                app.dependency_overrides.clear()

            # Inquilino, conserje y presidente se suman; replay e intento duplicado con otra key
            for idx, user in enumerate((inquilino, conserje, presidente), start=2):
                try:
                    _instalar_overrides(factory, fake_redis, usuario=user)
                    key = f"adh-ok-{user.id}"
                    resp = await client.post(
                        f"/api/incidencias/{abierta_id}/adherir",
                        headers={"Idempotency-Key": key},
                    )
                    assert resp.status_code == 200
                    assert resp.json()["adhesiones_count"] == idx

                    resp_rep = await client.post(
                        f"/api/incidencias/{abierta_id}/adherir",
                        headers={"Idempotency-Key": key},
                    )
                    assert resp_rep.status_code == 200
                    assert resp_rep.headers.get("X-Idempotency-Replayed") == "true"

                    resp_dup = await client.post(
                        f"/api/incidencias/{abierta_id}/adherir",
                        headers={"Idempotency-Key": f"adh-dup2-{user.id}"},
                    )
                    assert resp_dup.status_code == 409
                finally:
                    app.dependency_overrides.clear()

        async with factory() as session:
            inc_db = (await session.execute(select(Incidencia).where(Incidencia.id == abierta_id))).scalar_one()
            assert inc_db.adhesiones_count == 4
            adhs_db = (
                (
                    await session.execute(
                        select(IncidenciaAdhesion).where(IncidenciaAdhesion.incidencia_id == abierta_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(adhs_db) == 4
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
