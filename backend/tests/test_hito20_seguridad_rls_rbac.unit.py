"""Suite integral Hito 20: PG17/SQLite paridad FK+WORM, HKDF, KeyDB fail-closed, CSRF, Nginx y RBAC/IDOR."""

from __future__ import annotations

import socket
from collections.abc import AsyncIterator, Generator
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, bind_rls_tenant, get_db, sellar_cadena_worm
from src.dependencies import verificar_usuario_activo
from src.main import app
from src.models import (
    AreaSocial,
    AuditoriaRecibo,
    ContratoOcupacion,
    Estructura,
    PaqueteRecibido,
    PaseVisita,
    Recibo,
    ReservaAreaSocial,
    Unidad,
    Usuario,
    VotoConsulta,
)
from src.redis_client import (
    LOGIN_ACCOUNT_MAX_ATTEMPTS,
    MAX_LOCAL_SECURITY_ENTRIES,
    REFRESH_USED_TTL_SECONDS,
    REVOKED_USER_TTL_SECONDS,
    get_redis_client,
    is_login_locked_out,
    record_login_failure,
    reset_local_security_state,
    revoke_session_id,
    revoke_user_session,
)
from src.routers.auth import _resolver_unidad_activa_id
from src.schemas import ComunicadoCreate, PaqueteCreate
from src.security import (
    JWT_AUDIENCE,
    JWT_ISSUER,
    compute_worm_record_hash,
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
    decode_token_unverified_exp,
    derive_subkey,
    get_password_hash,
    get_qr_signing_key,
    get_solvency_signing_key,
    get_vote_signing_key,
    is_trusted_proxy_ip,
    validate_safe_outgoing_url_async,
)
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base


@pytest.fixture(autouse=True)
def _limpiar_h20() -> Generator[None]:
    app.dependency_overrides.clear()
    reset_local_security_state()
    try:
        yield
    finally:
        app.dependency_overrides.clear()
        reset_local_security_state()


@asynccontextmanager
async def _entorno_h20(
    *,
    con_semilla: bool = True,
) -> AsyncIterator[tuple[async_sessionmaker[AsyncSession], SeededCondoContext | None, AsyncClient]]:
    """Prepara SQLite FK real y AsyncClient con limpieza garantizada en try...finally."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory) if con_semilla else None

        async def _override_get_db() -> AsyncIterator[AsyncSession]:
            async with factory() as session:
                yield session

        app.dependency_overrides[get_db] = _override_get_db
        app.dependency_overrides[get_redis_client] = lambda: None
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as ac:
            yield factory, ctx, ac
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


def test_hkdf_subclaves_independientes_y_claims_jwt(monkeypatch: pytest.MonkeyPatch) -> None:
    """HKDF-SHA256 genera subclaves distintas por propósito e impide confusión de tokens JWT."""
    monkeypatch.setenv("SECRET_KEY", "clave-maestra-hito20-super-segura-32bytes")
    propositos = (
        "jwt-access",
        "jwt-refresh",
        "csrf-hmac",
        "solvency-hmac",
        "vote-hmac",
        "qr-pass-hmac",
        "worm-audit-hmac",
    )
    subclaves = [derive_subkey(p) for p in propositos]
    assert len(set(subclaves)) == len(propositos)
    assert all(len(s) == 64 for s in subclaves)
    assert get_solvency_signing_key() == derive_subkey("solvency-hmac")
    assert get_vote_signing_key() == derive_subkey("vote-hmac")
    assert get_qr_signing_key() == derive_subkey("qr-pass-hmac")

    acc = create_access_token({"sub": "u@condo.test", "rol": "PROPIETARIO", "id": 1, "sid": "s1", "condominio_id": 1})
    ref = create_refresh_token({"sub": "u@condo.test", "id": 1, "sid": "s1", "condominio_id": 1})
    dec_acc = decode_access_token(acc)
    dec_ref = decode_refresh_token(ref)
    assert dec_acc["typ"] == "access" and dec_acc["iss"] == JWT_ISSUER and dec_acc["aud"] == JWT_AUDIENCE
    assert dec_ref["typ"] == "refresh" and dec_ref["iss"] == JWT_ISSUER and dec_ref["aud"] == JWT_AUDIENCE

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token(ref)
    with pytest.raises(jwt.InvalidTokenError):
        decode_refresh_token(acc)

    # Token con clave de acceso pero typ adulterado también se rechaza
    forged_typ = jwt.encode(
        {
            "sub": "u@condo.test",
            "typ": "refresh",
            "iat": int(datetime.now(UTC).timestamp()),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "exp": int((datetime.now(UTC) + timedelta(minutes=5)).timestamp()),
        },
        derive_subkey("jwt-access"),
        algorithm="HS256",
    )
    with pytest.raises(jwt.InvalidTokenError, match="acceso"):
        decode_access_token(forged_typ)

    exp_acc = create_access_token({"sub": "u@condo.test", "sid": "s-exp"}, expires_delta=timedelta(seconds=-10))
    exp_ref = create_refresh_token({"sub": "u@condo.test", "sid": "s-ref-exp"}, expires_delta=timedelta(seconds=-10))
    assert decode_token_unverified_exp(exp_acc)["sid"] == "s-exp"  # type: ignore[index]
    assert decode_token_unverified_exp(exp_ref)["sid"] == "s-ref-exp"  # type: ignore[index]


@pytest.mark.asyncio
async def test_sqlite_foreign_keys_worm_triggers_y_sellar_cadena(tmp_path: Path) -> None:
    """PRAGMA foreign_keys=ON, triggers WORM SQLite y sellar_cadena_worm encadenado operan end-to-end."""
    db_path = tmp_path / "worm_fk_h20.db"
    eng = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    factory = async_sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    try:
        async with eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await conn.execute(
                text(
                    "CREATE TRIGGER IF NOT EXISTS trg_auditoria_recibos_worm_no_update "
                    "BEFORE UPDATE ON auditoria_recibos "
                    "BEGIN SELECT RAISE(ABORT, 'WORM: tabla inmutable'); END;"
                )
            )
            await conn.execute(
                text(
                    "CREATE TRIGGER IF NOT EXISTS trg_auditoria_recibos_worm_no_delete "
                    "BEFORE DELETE ON auditoria_recibos "
                    "BEGIN SELECT RAISE(ABORT, 'WORM: tabla inmutable'); END;"
                )
            )

        # PRAGMA foreign_keys=ON rechaza ContratoOcupacion con unidad inexistente
        async with factory() as s:
            await bind_rls_tenant(s, 1)
            usr = Usuario(
                condominio_id=1,
                nombre="FK Test",
                cedula="V-20001001",
                correo="fk@condo.test",
                telefono="0414",
                password_hash="h",
                es_activo=True,
                rol="PROPIETARIO",
            )
            s.add(usr)
            await s.flush()
            s.add(
                ContratoOcupacion(
                    condominio_id=1,
                    usuario_id=usr.id,
                    unidad_id=99999,
                    tipo_ocupante="PROPIETARIO",
                    es_activo=True,
                )
            )
            with pytest.raises(IntegrityError):
                await s.commit()
            await s.rollback()

        # Cadena WORM determinista en auditoria_recibos y rechazo de UPDATE/DELETE
        async with factory() as s:
            est = Estructura(condominio_id=1, nombre="Torre WORM", tipo="TORRE")
            s.add(est)
            await s.flush()
            uni = Unidad(condominio_id=1, identificador="W-01", estructura_id=est.id)
            s.add(uni)
            await s.flush()
            rec = Recibo(condominio_id=1, unidad_id=uni.id, periodo="2026-11", monto_usd=Decimal("20.00"))
            s.add(rec)
            await s.flush()

            p1, r1 = await sellar_cadena_worm(s, "auditoria_recibos", 1, "tx-1")
            p2, r2 = await sellar_cadena_worm(s, "auditoria_recibos", 1, "tx-2")
            assert p2 == r1
            assert r2 == compute_worm_record_hash(r1, "tx-2")
            aud = AuditoriaRecibo(
                condominio_id=1,
                recibo_id=rec.id,
                estado_viejo="PENDIENTE",
                estado_nuevo="APROBADO",
                motivo="ok",
                prev_hash=p1,
                record_hash=r1,
            )
            s.add(aud)
            await s.commit()

            with pytest.raises(IntegrityError, match="WORM"):
                await s.execute(text("UPDATE auditoria_recibos SET motivo = 'hack'"))
            await s.rollback()
            with pytest.raises(IntegrityError, match="WORM"):
                await s.execute(text("DELETE FROM auditoria_recibos"))
            await s.rollback()

        with pytest.raises(ValueError, match="Tabla WORM no soportada"):
            await sellar_cadena_worm(None, "usuarios", 1, "x")
        _ = VotoConsulta
    finally:
        await eng.dispose()


@pytest.mark.asyncio
async def test_keydb_ttl_7d_lockout_cuenta_global_y_limite_local(monkeypatch: pytest.MonkeyPatch) -> None:
    """TTL de revocación >= 7d, lockout Lua global por cuenta rotando IP y tope estricto en RAM."""
    assert REVOKED_USER_TTL_SECONDS == REFRESH_USED_TTL_SECONDS
    assert REVOKED_USER_TTL_SECONDS >= 7 * 86_400

    monkeypatch.setenv("APP_ENV", "development")
    reset_local_security_state()

    # Tope estricto MAX_LOCAL_SECURITY_ENTRIES evita fuga infinita en memoria
    for idx in range(MAX_LOCAL_SECURITY_ENTRIES + 25):
        await revoke_session_id(None, f"sid-cap-{idx}", ttl_seconds=60)
    from src import redis_client as rc

    assert len(rc._local_revoked_sids) == MAX_LOCAL_SECURITY_ENTRIES

    # Lockout global por correo aunque cambie la IP en cada intento
    correo = "ataque.distribuido@condo.test"
    for idx in range(LOGIN_ACCOUNT_MAX_ATTEMPTS):
        assert await is_login_locked_out(None, f"198.51.100.{idx + 1}", correo) is False
        await record_login_failure(None, f"198.51.100.{idx + 1}", correo)
    assert await is_login_locked_out(None, "203.0.113.250", correo) is True


@pytest.mark.asyncio
async def test_login_no_limpia_revocacion_y_logout_aisla_dispositivo(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """login bloquea usuario revocado/deshabilitado y logout solo revoca el sid del dispositivo actual."""
    monkeypatch.setenv("APP_ENV", "development")
    async with _entorno_h20(con_semilla=False) as (factory, _, ac):
        async with factory() as session:
            user_activo = Usuario(
                condominio_id=1,
                nombre="Multi Device",
                cedula="V-88008800",
                correo="multi@condo.test",
                telefono="0414",
                password_hash=get_password_hash("ClaveMulti2026!"),
                es_activo=True,
                rol="PROPIETARIO",
            )
            session.add(user_activo)
            await session.commit()
            user_id = user_activo.id

        # 1. Logout de dispositivo A (sid-A) no invalida dispositivo B (sid-B)
        tok_a = create_access_token({"sub": "multi@condo.test", "id": user_id, "sid": "sid-A", "rol": "PROPIETARIO"})
        tok_b = create_access_token({"sub": "multi@condo.test", "id": user_id, "sid": "sid-B", "rol": "PROPIETARIO"})
        ac.cookies.set("access_token", f"Bearer {tok_a}")
        assert (await ac.post("/api/auth/logout")).status_code == 200
        ac.cookies.clear()

        assert (await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {tok_a}"})).status_code == 401
        assert (await ac.get("/api/auth/me", headers={"Authorization": f"Bearer {tok_b}"})).status_code == 200

        # 2. Usuario revocado administrativamente NO puede hacer login ni borrar su propia revocación
        await revoke_user_session(None, user_id)
        r_rev = await ac.post("/api/auth/login", json={"correo": "multi@condo.test", "password": "ClaveMulti2026!"})
        assert r_rev.status_code == 403
        assert await rc_is_user_revoked(user_id) is True

        # 3. Cuenta deshabilitada no-fantasma rechazada en login
        reset_local_security_state()
        async with factory() as session:
            user_db = await session.get(Usuario, user_id)
            assert user_db is not None
            user_db.es_activo = False
            user_db.rol = "PROPIETARIO"
            await session.commit()
        r_dis = await ac.post("/api/auth/login", json={"correo": "multi@condo.test", "password": "ClaveMulti2026!"})
        assert r_dis.status_code == 403


async def rc_is_user_revoked(uid: int) -> bool:
    from src.redis_client import is_user_session_revoked

    return await is_user_session_revoked(None, uid)


@pytest.mark.asyncio
async def test_esquemas_urls_peligrosas_y_anti_ssrf_async_mayusculas(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bloquea javascript:, data:, //, caracteres de control y normaliza HTTP:// en Anti-SSRF asíncrono."""
    with pytest.raises(ValidationError):
        ComunicadoCreate.model_validate(
            {"titulo": "Aviso", "contenido": "Texto", "enlace_externo": "javascript:alert(1)"}
        )
    with pytest.raises(ValidationError):
        ComunicadoCreate.model_validate({"titulo": "Aviso", "contenido": "Texto", "enlace_externo": "//evil.com/x"})
    with pytest.raises(ValidationError):
        PaqueteCreate.model_validate(
            {
                "unidad_id": 1,
                "empresa_envio": "MRW",
                "descripcion": "Caja",
                "url_foto_evidencia": "//evil.com/img.png",
            }
        )
    with pytest.raises(ValidationError):
        PaqueteCreate.model_validate(
            {
                "unidad_id": 1,
                "empresa_envio": "MRW",
                "descripcion": "Caja",
                "url_foto_evidencia": "https://cdn.example.com/a\n.png",
            }
        )

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))],
    )
    norm = await validate_safe_outgoing_url_async("  HTTPS://CDN.EXAMPLE.COM/Path/File.PNG  ")
    assert norm == "https://cdn.example.com/Path/File.PNG"

    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda host, port: [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 0))],
    )
    with pytest.raises(ValueError, match="prohibido"):
        await validate_safe_outgoing_url_async("HTTP://PUBLIC-ALIAS.EXAMPLE.COM/ssrf.png")


@pytest.mark.asyncio
async def test_middleware_http_host_metrics_proxies_csrf_corrupta_y_500_oshp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Valida ALLOWED_HOSTS, /metrics protegido, TRUSTED_PROXY_IPS, CSRF corrupta y cabeceras OSHP en 500."""
    async with _entorno_h20(con_semilla=False) as (factory, _, ac):
        # 1. ALLOWED_HOSTS
        monkeypatch.setenv("ALLOWED_HOSTS", "api.condominio.test")
        bad_host = await ac.get("/health", headers={"Host": "evil.attacker.com"})
        assert bad_host.status_code == 400
        assert bad_host.headers["x-frame-options"] == "DENY"
        assert (await ac.get("/health", headers={"Host": "api.condominio.test"})).status_code == 200
        monkeypatch.delenv("ALLOWED_HOSTS", raising=False)

        # 2. /metrics protegido por METRICS_AUTH_TOKEN
        monkeypatch.setenv("METRICS_AUTH_TOKEN", "secreto-metrics-11x")
        m_401 = await ac.get("/metrics")
        assert m_401.status_code == 401
        assert m_401.headers["cache-control"] == "no-store"
        assert (await ac.get("/metrics", headers={"Authorization": "Bearer secreto-metrics-11x"})).status_code == 200
        assert (await ac.get("/metrics", headers={"X-Metrics-Token": "secreto-metrics-11x"})).status_code == 200
        monkeypatch.delenv("METRICS_AUTH_TOKEN", raising=False)

        # 3. TRUSTED_PROXY_IPS rechaza X-Forwarded-Proto de origen no confiable
        monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.99.99.99")
        assert is_trusted_proxy_ip("198.51.100.10") is False
        assert is_trusted_proxy_ip("10.99.99.99") is True
        res_no_hsts = await ac.get("/health", headers={"X-Forwarded-Proto": "https"})
        assert "strict-transport-security" not in res_no_hsts.headers
        monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)

        # 4. Cookie corrupta en ruta mutante bloqueada con 403 si CSRF_ENFORCE=true (pero /logout permitido)
        monkeypatch.setenv("CSRF_ENFORCE", "true")
        ac.cookies.set("access_token", "Bearer corrupto.jwt.invalido")
        res_corrupt = await ac.post("/api/finanzas/tasa", json={})
        assert res_corrupt.status_code == 403
        res_logout_corrupt = await ac.post("/api/auth/logout")
        assert res_logout_corrupt.status_code == 200
        ac.cookies.clear()
        monkeypatch.delenv("CSRF_ENFORCE", raising=False)

        # 5. Cabeceras OSHP garantizadas incluso cuando una sesión SQLite real dispara 500 no capturado
        async with factory() as real_db:

            async def _fallo_motor(*args: object, **kwargs: object) -> Any:
                raise RuntimeError("Fallo inesperado en motor")

            monkeypatch.setattr(real_db, "execute", _fallo_motor)
            app.dependency_overrides[get_db] = lambda: real_db
            res_500 = await ac.get("/api/estructura/unidades")

        assert res_500.status_code == 500
        assert res_500.headers["x-content-type-options"] == "nosniff"
        assert res_500.headers["x-frame-options"] == "DENY"
        assert res_500.headers["cache-control"] == "no-store"


@pytest.mark.asyncio
async def test_rbac_idor_fail_closed_fecha_fin_y_aislamiento_horizontal() -> None:
    """Cierra escalación VP->Presidente, verificar_usuario_activo fail-closed, fecha_fin y listados."""
    from fastapi import HTTPException

    # 1. verificar_usuario_activo fail-closed ante falta de es_activo o rol desconocido
    with pytest.raises(HTTPException) as exc_no_attr:
        verificar_usuario_activo(SimpleNamespace(id=1, rol="PROPIETARIO"))  # type: ignore[arg-type]
    assert exc_no_attr.value.status_code == 403

    with pytest.raises(HTTPException) as exc_bad_rol:
        usuario_rol_invalido = SimpleNamespace(id=1, es_activo=True, rol="ROL_INEXISTENTE")
        verificar_usuario_activo(usuario_rol_invalido)  # type: ignore[arg-type]
    assert exc_bad_rol.value.status_code == 403

    async with _entorno_h20() as (factory, ctx, ac):
        assert ctx is not None

        # 2. _resolver_unidad_activa_id filtra fecha_fin.is_(None) en SQLite real
        async with factory() as session:
            user_cerrado = Usuario(
                condominio_id=1,
                nombre="Contrato Cerrado",
                cedula="V-55005500",
                correo="cerrado@condo.test",
                telefono="0414",
                password_hash=get_password_hash("Clave1234!"),
                es_activo=True,
                rol="PROPIETARIO",
            )
            session.add(user_cerrado)
            await session.flush()
            session.add(
                ContratoOcupacion(
                    condominio_id=1,
                    usuario_id=user_cerrado.id,
                    unidad_id=ctx.unidad_a_id,
                    tipo_ocupante="PROPIETARIO",
                    es_activo=True,
                    fecha_fin=datetime.now(UTC),
                )
            )
            await session.commit()

            assert await _resolver_unidad_activa_id(session, user_cerrado) is None
            prop_db = await session.get(Usuario, ctx.propietario_id)
            assert prop_db is not None
            assert await _resolver_unidad_activa_id(session, prop_db) == ctx.unidad_a_id

        # 3. VICEPRESIDENTE no puede asignar rol PRESIDENTE ni modificar a un PRESIDENTE
        async with factory() as session:
            vp = Usuario(
                condominio_id=1,
                nombre="VP Test",
                cedula="V-20000002",
                correo="vp@condo.test",
                telefono="0414",
                password_hash=get_password_hash("Clave1234!"),
                es_activo=True,
                rol="VICEPRESIDENTE",
            )
            fantasma = Usuario(
                condominio_id=1,
                nombre="Fant",
                cedula="V-90000009",
                correo="f@condo.test",
                telefono="0414",
                password_hash=get_password_hash("Clave1234!"),
                es_activo=False,
                rol="FANTASMA",
            )
            session.add_all([vp, fantasma])
            await session.commit()
            vp_id, fantasma_id = vp.id, fantasma.id

        tok_vp = create_access_token({"sub": "vp@condo.test", "id": vp_id, "rol": "VICEPRESIDENTE", "condominio_id": 1})
        cookies_vp = {"access_token": f"Bearer {tok_vp}"}
        r_esc1 = await ac.put(
            f"/api/usuarios/{fantasma_id}/asignar",
            headers={"Idempotency-Key": "20000000-0000-4000-8000-000000000001"},
            cookies=cookies_vp,
            json={"unidad_id": ctx.unidad_a_id, "tipo_ocupante": "PROPIETARIO", "rol": "PRESIDENTE"},
        )
        assert r_esc1.status_code == 403

        r_esc2 = await ac.put(
            f"/api/usuarios/{ctx.presidente_id}/asignar",
            headers={"Idempotency-Key": "20000000-0000-4000-8000-000000000002"},
            cookies=cookies_vp,
            json={"unidad_id": ctx.unidad_a_id, "tipo_ocupante": "PROPIETARIO", "rol": "PROPIETARIO"},
        )
        assert r_esc2.status_code == 403

        # 4. /api/finanzas/resumen oculta recibos de terceros para PROPIETARIO y CONSERJE
        async with factory() as session:
            session.add_all(
                [
                    Recibo(
                        condominio_id=1,
                        unidad_id=ctx.unidad_a_id,
                        periodo="2026-11",
                        monto_usd=Decimal("40.00"),
                        monto_pagado_usd=Decimal("0.00"),
                        estado="PENDIENTE",
                    ),
                    Recibo(
                        condominio_id=1,
                        unidad_id=ctx.unidad_b_id,
                        periodo="2026-11",
                        monto_usd=Decimal("99.00"),
                        monto_pagado_usd=Decimal("0.00"),
                        estado="PENDIENTE",
                    ),
                    PaseVisita(
                        condominio_id=1,
                        jti=str(uuid4()),
                        unidad_id=ctx.unidad_a_id,
                        creado_por_id=ctx.propietario_id,
                        nombre_visitante="Visita Ajena",
                        cedula_visitante="V-44444444",
                        modalidad="UNICO_USO",
                        valido_desde=datetime.now(UTC),
                        valido_hasta=datetime.now(UTC) + timedelta(hours=4),
                        estado="ACTIVO",
                        firma_hmac="a" * 64,
                    ),
                    PaqueteRecibido(
                        condominio_id=1,
                        unidad_id=ctx.unidad_a_id,
                        recibido_por_id=ctx.conserje_id,
                        empresa_envio="MRW",
                        descripcion="Caja vecina",
                        estado="EN_GARITA",
                    ),
                ]
            )
            area = AreaSocial(condominio_id=1, nombre="Caney Central", aforo_maximo=25)
            session.add(area)
            await session.flush()
            session.add(
                ReservaAreaSocial(
                    condominio_id=1,
                    area_id=area.id,
                    unidad_id=ctx.unidad_a_id,
                    solicitante_id=ctx.propietario_id,
                    fecha_evento=date.today() + timedelta(days=3),
                    motivo_evento="Reunión privada",
                    estado="CONFIRMADA",
                )
            )
            await session.commit()

        tok_prop = create_access_token(
            {"sub": "prop@condo.test", "id": ctx.propietario_id, "rol": "PROPIETARIO", "condominio_id": 1}
        )
        r_res_prop = await ac.get("/api/finanzas/resumen", cookies={"access_token": f"Bearer {tok_prop}"})
        assert r_res_prop.status_code == 200
        assert len(r_res_prop.json()["estado_cobranza"]) == 1
        assert r_res_prop.json()["estado_cobranza"][0]["unidad_id"] == ctx.unidad_a_id

        tok_cons = create_access_token(
            {"sub": "cons@condo.test", "id": ctx.conserje_id, "rol": "CONSERJE", "condominio_id": 1}
        )
        r_res_cons = await ac.get("/api/finanzas/resumen", cookies={"access_token": f"Bearer {tok_cons}"})
        assert r_res_cons.status_code == 200
        assert r_res_cons.json()["estado_cobranza"] == []

        # 5. /api/accesos/pases/mios para PRESIDENTE sin unidad propia devuelve [] (no filtra pases de vecinos)
        tok_pres = create_access_token(
            {"sub": "pres@condo.test", "id": ctx.presidente_id, "rol": "PRESIDENTE", "condominio_id": 1}
        )
        r_mios = await ac.get("/api/accesos/pases/mios", cookies={"access_token": f"Bearer {tok_pres}"})
        assert r_mios.status_code == 200
        assert r_mios.json() == []

        # 6. /api/paqueteria restringe a TESORERO a sus unidades propias y /api/reservas restringe a VOCERO
        tok_tes = create_access_token(
            {"sub": "tes@condo.test", "id": ctx.tesorero_id, "rol": "TESORERO", "condominio_id": 1}
        )
        assert (await ac.get("/api/paqueteria", cookies={"access_token": f"Bearer {tok_tes}"})).json() == []

        tok_voc = create_access_token(
            {"sub": "voc@condo.test", "id": ctx.vocero_id, "rol": "VOCERO", "condominio_id": 1}
        )
        assert (await ac.get("/api/reservas", cookies={"access_token": f"Bearer {tok_voc}"})).json() == []
