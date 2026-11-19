import json
import logging
from collections.abc import AsyncIterator
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import Response
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from src.database import Base, get_db
from src.main import (
    _API_CSP,
    _DEFAULT_ALLOWED_HOSTS,
    _DOCS_CSP,
    _DOCS_PATHS,
    _INVALID_HOST_CHARS,
    _PERMISSIONS_POLICY,
    _allowed_hosts_set,
    _apply_security_headers,
    _check_pre_route_guards,
    _es_produccion,
    _extraer_metodos_ops,
    _extract_client_host,
    _extract_cookie_session_id_for_csrf,
    _extract_host_from_header,
    _extract_metrics_token,
    _extract_origin_host,
    _is_allowed_fetch_metadata,
    _is_allowed_host,
    _is_https_request,
    _is_metrics_authorized,
    _is_valid_cookie_csrf,
    _merge_vary_header,
    _metodos_permitidos,
    _parse_allowed_hosts_env,
    _parse_valid_host_url,
    _parse_vary_items,
    _requires_cookie_csrf_check,
    _session_id_from_payload,
    _session_id_from_token,
    app,
    http_exception_handler,
    lifespan,
    security_headers_middleware,
    validation_exception_handler,
)
from src.redis_client import get_redis_client
from src.security import (
    DEFAULT_INSECURE_SECRET_KEY,
    create_access_token,
    create_refresh_token,
    generate_csrf_token,
)


def test_health_check(client: TestClient) -> None:
    """
    Verifica que el punto de entrada principal (Healthcheck) de la API responda correctamente
    con un estado 200 y el JSON esperado. Esta prueba asegura que FastAPI levantó correctamente.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_options_405_incluye_allow_completo(client: TestClient) -> None:
    """Un OPTIONS sobre un path devuelve 405 con Allow exacto sin colisión con rutas parametrizadas."""
    response = client.options("/api/finanzas/tasa")
    assert response.status_code == 405
    allow = response.headers.get("allow", "")
    assert "GET" in allow
    assert "POST" in allow

    exact_static = client.options("/api/accesos/pases/mios")
    assert exact_static.status_code == 405
    assert exact_static.headers.get("allow") == "GET"

    delete_static = client.delete("/api/accesos/pases/mios")
    assert delete_static.status_code == 405
    assert delete_static.headers.get("allow") == "GET"


def test_respuestas_no_cacheables(client: TestClient) -> None:
    """Toda respuesta lleva Cache-Control: no-store para evitar almacenamiento de datos sensibles."""
    assert client.get("/health").headers["cache-control"] == "no-store"
    assert client.get("/no-existe").headers["cache-control"] == "no-store"


def test_cabeceras_seguridad_modern_web(client: TestClient) -> None:
    """Verifica CSP, COOP, CORP, Permissions-Policy y Vary en rutas API y Swagger UI."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.headers["x-content-type-options"] == "nosniff"
    assert res_health.headers["x-frame-options"] == "DENY"
    assert res_health.headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert (
        res_health.headers["content-security-policy"]
        == "default-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'"
    )
    assert res_health.headers["cross-origin-opener-policy"] == "same-origin-allow-popups"
    assert res_health.headers["cross-origin-resource-policy"] == "same-origin"
    assert res_health.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    vary_tokens = {item.strip() for item in res_health.headers["vary"].split(",")}
    assert {"Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site"}.issubset(vary_tokens)
    assert "strict-transport-security" not in res_health.headers

    res_docs = client.get("/docs")
    assert res_docs.status_code == 200
    assert "frame-ancestors 'none'" in res_docs.headers["content-security-policy"]
    assert "https://cdn.jsdelivr.net" in res_docs.headers["content-security-policy"]


def test_hsts_habilitado_en_cookie_secure_o_https(client: TestClient, monkeypatch) -> None:
    """Emite Strict-Transport-Security solo bajo COOKIE_SECURE=true o señal HTTPS."""
    monkeypatch.setenv("COOKIE_SECURE", "true")
    res_cookie_secure = client.get("/health")
    assert res_cookie_secure.status_code == 200
    assert res_cookie_secure.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"

    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    res_https_proxy = client.get("/health", headers={"X-Forwarded-Proto": "https"})
    assert res_https_proxy.status_code == 200
    assert res_https_proxy.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"


def test_fetch_metadata_rechaza_cross_site_antes_de_auth(client: TestClient) -> None:
    """Rechaza solicitudes Fetch Metadata cross-site no navegables con 403 antes de auth o rutas."""
    cors_blocked = client.get(
        "/api/auth/me",
        headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "cors"},
    )
    assert cors_blocked.status_code == 403
    assert cors_blocked.headers["x-frame-options"] == "DENY"
    assert "Sec-Fetch-Site" in cors_blocked.headers["vary"]

    missing_route_blocked = client.get(
        "/no-existe-cross-site",
        headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "no-cors"},
    )
    assert missing_route_blocked.status_code == 403

    post_nav_blocked = client.post(
        "/api/auth/login",
        json={},
        headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate"},
    )
    assert post_nav_blocked.status_code == 403

    embed_blocked = client.get(
        "/health",
        headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Dest": "object"},
    )
    assert embed_blocked.status_code == 403

    nav_allowed = client.get(
        "/health",
        headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Dest": "document"},
    )
    assert nav_allowed.status_code == 200

    same_origin_allowed = client.get(
        "/health",
        headers={"Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "cors"},
    )
    assert same_origin_allowed.status_code == 200


def test_merge_vary_preserva_cabeceras_y_evita_duplicados() -> None:
    """_merge_vary_header conserva cabeceras previas y evita duplicados sin distinguir mayúsculas."""
    from fastapi import Response

    from src.main import _merge_vary_header

    response = Response(headers={"Vary": "Origin, sec-fetch-site"})
    _merge_vary_header(response)
    tokens = [item.strip() for item in response.headers["Vary"].split(",")]
    assert tokens == ["Origin", "sec-fetch-site", "Sec-Fetch-Dest", "Sec-Fetch-Mode"]


def test_lifespan_fail_fast_produccion(monkeypatch: pytest.MonkeyPatch) -> None:
    """El arranque lifespan rechaza iniciar en producción si faltan secretos o DB real."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@postgres:5432/db")
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        with TestClient(app):
            pass

    monkeypatch.setenv("SECRET_KEY", "a" * 32)
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        with TestClient(app):
            pass


def _build_request(
    *,
    method: str = "GET",
    path: str = "/health",
    scheme: str = "http",
    headers: dict[str, str] | None = None,
    cookies: dict[str, str] | None = None,
    client: tuple[str, int] | None = ("127.0.0.1", 12345),
) -> Request:
    """Construye un Request ASGI sintético en memoria para probar middlewares y helpers sin red."""
    raw_headers: list[tuple[bytes, bytes]] = [
        (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in (headers or {}).items()
    ]
    if cookies:
        cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
        raw_headers.append((b"cookie", cookie_str.encode("latin-1")))
    scope: dict[str, Any] = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": scheme,
        "path": path,
        "raw_path": path.encode("ascii"),
        "query_string": b"",
        "headers": raw_headers,
        "client": client,
        "server": ("testserver", 80),
    }
    return Request(scope)


async def _fake_db_override() -> AsyncIterator[None]:
    """Generador asíncrono inocuo para aislar rutas sin abrir conexión SQLite/PostgreSQL."""
    yield None


def _boom_db_override() -> Any:
    """Dependencia simulada que falla para provocar un HTTP 500 controlado en middleware."""
    raise RuntimeError("fallo_simulado_db")


def _assert_oshp_headers(headers: Any, *, is_docs: bool = False, expect_hsts: bool = False) -> None:
    """Valida todas las cabeceras de seguridad OSHP exigidas por Nivel 11X."""
    assert headers["cache-control"] == "no-store"
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert headers["content-security-policy"] == (_DOCS_CSP if is_docs else _API_CSP)
    assert headers["cross-origin-opener-policy"] == "same-origin-allow-popups"
    assert headers["cross-origin-resource-policy"] == "same-origin"
    assert headers["permissions-policy"] == _PERMISSIONS_POLICY
    vary_tokens = {item.strip() for item in headers["vary"].split(",")}
    assert {"Sec-Fetch-Dest", "Sec-Fetch-Mode", "Sec-Fetch-Site"}.issubset(vary_tokens)
    if expect_hsts:
        assert headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"
    else:
        assert "strict-transport-security" not in headers


def test_app_metadata_y_es_produccion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica metadatos de FastAPI, exclusión de /metrics en OpenAPI y detección de _es_produccion."""
    assert app.title == "Condominio App API"
    assert app.version == "1.0.0"
    assert app.docs_url == "/docs"
    assert app.redoc_url == "/redoc"
    assert app.openapi_url == "/openapi.json"
    assert "/metrics" not in app.openapi()["paths"]

    monkeypatch.delenv("APP_ENV", raising=False)
    assert _es_produccion() is False

    monkeypatch.setenv("APP_ENV", "development")
    assert _es_produccion() is False

    monkeypatch.setenv("APP_ENV", "production")
    assert _es_produccion() is True

    monkeypatch.setenv("APP_ENV", "PRODUCTION")
    assert _es_produccion() is True

    monkeypatch.setenv("APP_ENV", " production ")
    assert _es_produccion() is False


@pytest.mark.asyncio
async def test_lifespan_sqlite_crea_esquema_y_produccion_postgresql_omite_sqlite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """lifespan crea esquema en SQLite y valida producción sin tocar SQLite cuando usa PostgreSQL."""
    fake_conn = AsyncMock()
    fake_begin_cm = MagicMock()
    fake_begin_cm.__aenter__ = AsyncMock(return_value=fake_conn)
    fake_begin_cm.__aexit__ = AsyncMock(return_value=None)
    fake_sqlite_engine = MagicMock()
    fake_sqlite_engine.dialect.name = "sqlite"
    fake_sqlite_engine.begin.return_value = fake_begin_cm

    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setattr("src.main.engine", fake_sqlite_engine)
    async with lifespan(app):
        pass
    fake_sqlite_engine.begin.assert_called_once_with()
    fake_conn.run_sync.assert_awaited_once_with(Base.metadata.create_all)

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "s" * 32)
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@postgres:5432/db")
    fake_pg_engine = MagicMock()
    fake_pg_engine.dialect.name = "postgresql"
    monkeypatch.setattr("src.main.engine", fake_pg_engine)
    async with lifespan(app):
        pass
    fake_pg_engine.begin.assert_not_called()

    monkeypatch.setenv("SECRET_KEY", DEFAULT_INSECURE_SECRET_KEY)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        async with lifespan(app):
            pass


def test_parsers_host_y_origen_normalizacion_y_rechazos() -> None:
    """Valida normalización, puertos, IPv6 y rechazo estricto de hosts/orígenes malformados."""
    assert _parse_valid_host_url("LocalHost") == "localhost"
    assert _parse_valid_host_url("Api.Condo.LOCAL:8443") == "api.condo.local"
    assert _parse_valid_host_url("[::1]:8000") == "::1"
    assert _parse_valid_host_url("[::1]") == "::1"
    assert _parse_valid_host_url("[invalid-ipv6") is None
    assert _parse_valid_host_url("user@example.com") is None
    assert _parse_valid_host_url(":pass@example.com") is None
    assert _parse_valid_host_url("user:pass@example.com") is None
    assert _parse_valid_host_url("example.com/admin") is None
    assert _parse_valid_host_url("example.com?q=1") is None
    assert _parse_valid_host_url(":8000") is None
    assert _parse_valid_host_url("") is None

    assert _extract_host_from_header("  Api.Local:8000  ") == "api.local"
    assert _extract_host_from_header("[::1]:8000") == "::1"
    assert _extract_host_from_header("") is None
    assert _extract_host_from_header("   ") is None
    assert _extract_host_from_header("evil.com?x=1") is None
    assert _INVALID_HOST_CHARS == frozenset({" ", "\r", "\n", "\x00", "/", "@", "\\"})
    for bad_char in _INVALID_HOST_CHARS:
        assert _extract_host_from_header(f"evil{bad_char}host") is None

    assert _parse_allowed_hosts_env("") == set()
    assert _parse_allowed_hosts_env(" Api.Local:8000, , bad/host, Condo.APP , [::1]:8443 ") == {
        "api.local",
        "condo.app",
        "::1",
    }

    assert _extract_origin_host("") is None
    assert _extract_origin_host("   ") is None
    assert _extract_origin_host("not-a-url") is None
    assert _extract_origin_host("  https://Portal.Condo.COM:8443/app  ") == "portal.condo.com"
    assert _extract_origin_host("http://[::1]:5173") == "::1"


def test_allowed_hosts_set_y_is_allowed_host(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica precedencia de ALLOWED_HOSTS, fusión con ALLOWED_ORIGINS y excepción loopback /health."""
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    assert _DEFAULT_ALLOWED_HOSTS == frozenset(
        {"localhost", "127.0.0.1", "::1", "api", "condominio_backend_api", "testserver", "test"}
    )
    assert _allowed_hosts_set() == set(_DEFAULT_ALLOWED_HOSTS)

    monkeypatch.setenv("ALLOWED_HOSTS", "   ")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://Portal.Condo.com:443, invalido, http://Admin.Local:5173")
    assert _allowed_hosts_set() == set(_DEFAULT_ALLOWED_HOSTS) | {"portal.condo.com", "admin.local"}

    monkeypatch.setenv("ALLOWED_HOSTS", "Prod.Example.com:8000, api.internal, bad/host")
    assert _allowed_hosts_set() == {"prod.example.com", "api.internal"}

    assert _is_allowed_host(_build_request(path="/health", headers={})) is False
    assert _is_allowed_host(_build_request(path="/health", headers={"Host": "evil/path"})) is False
    assert _is_allowed_host(_build_request(path="/health", headers={"Host": "127.0.0.1:8000"})) is True
    assert _is_allowed_host(_build_request(path="/health", headers={"Host": "LOCALHOST"})) is True
    assert _is_allowed_host(_build_request(path="/health", headers={"Host": "[::1]:8000"})) is True
    assert _is_allowed_host(_build_request(path="/health", headers={"Host": "api"})) is False
    assert _is_allowed_host(_build_request(path="/docs", headers={"Host": "127.0.0.1"})) is False
    assert _is_allowed_host(_build_request(path="/api/finanzas/tasa", headers={"Host": "PROD.EXAMPLE.COM"})) is True


@pytest.mark.asyncio
async def test_allowed_hosts_http_rechaza_desconocido_y_permite_loopback_health(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Rechaza Host no autorizado con HTTP 400 + cabeceras OSHP y permite /health loopback."""
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as ac:
        res_ok = await ac.get("/health", headers={"Host": "TESTSERVER:8000"})
        assert res_ok.status_code == 200

        res_bad = await ac.get("/health", headers={"Host": "evil.attacker.com"})
        assert res_bad.status_code == 400
        assert res_bad.json() == {"detail": "Encabezado Host inválido o no autorizado."}
        _assert_oshp_headers(res_bad.headers)

        res_empty = await ac.get("/health", headers={"Host": ""})
        assert res_empty.status_code == 400

        monkeypatch.setenv("ALLOWED_HOSTS", "only.prod.local")
        assert (await ac.get("/health", headers={"Host": "127.0.0.1:8000"})).status_code == 200
        assert (await ac.get("/docs", headers={"Host": "127.0.0.1"})).status_code == 400
        assert (await ac.get("/health", headers={"Host": "only.prod.local"})).status_code == 200


@pytest.mark.asyncio
async def test_metrics_autorizacion_y_endpoint_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida extracción de token, aislamiento en producción/proxy y respuestas HTTP /metrics."""
    req_both = _build_request(headers={"X-Metrics-Token": "  tok-header  ", "Authorization": "Bearer tok-bearer"})
    assert _extract_metrics_token(req_both) == "tok-header"
    assert _extract_metrics_token(_build_request(headers={"Authorization": "  Bearer   tok-bearer  "})) == "tok-bearer"
    assert _extract_metrics_token(_build_request(headers={"Authorization": "Basic abc"})) == ""
    assert _extract_metrics_token(_build_request(headers={"Authorization": "Bearer   "})) == ""
    assert _extract_metrics_token(_build_request(headers={})) == ""

    assert _extract_client_host(_build_request(client=("10.1.2.3", 5000))) == "10.1.2.3"
    assert _extract_client_host(_build_request(client=None)) is None

    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as ac:
        monkeypatch.setenv("METRICS_AUTH_TOKEN", "  secret-metrics-11x  ")
        unauth = await ac.get("/metrics")
        assert unauth.status_code == 401
        assert unauth.json() == {"detail": "Acceso no autorizado al endpoint de métricas."}
        _assert_oshp_headers(unauth.headers)

        assert (await ac.get("/metrics", headers={"Authorization": "Bearer wrong"})).status_code == 401
        assert (await ac.get("/metrics", headers={"X-Metrics-Token": "wrong"})).status_code == 401

        ok_bearer = await ac.get("/metrics", headers={"Authorization": "Bearer secret-metrics-11x"})
        assert ok_bearer.status_code == 200
        assert "text/plain" in ok_bearer.headers["content-type"]
        assert "# HELP" in ok_bearer.text
        _assert_oshp_headers(ok_bearer.headers)

        ok_header = await ac.get("/metrics", headers={"X-Metrics-Token": "secret-metrics-11x"})
        assert ok_header.status_code == 200

        monkeypatch.setenv("APP_ENV", "production")
        assert (await ac.get("/metrics", headers={"Authorization": "Bearer secret-metrics-11x"})).status_code == 200

        monkeypatch.setenv("METRICS_AUTH_TOKEN", "   ")
        assert (await ac.get("/metrics")).status_code == 401
        assert _is_metrics_authorized(_build_request(path="/metrics", client=("127.0.0.1", 1000))) is False

        monkeypatch.setenv("APP_ENV", "development")
        assert (await ac.get("/metrics")).status_code == 200

        monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.99.99.99")
        assert (await ac.get("/metrics")).status_code == 401


def test_csrf_helpers_y_extraccion_sesion(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prueba todas las ramas de _requires_cookie_csrf_check, extracción SID/SUB y validación CSRF."""
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("CSRF_ENFORCE", "false")
    assert _requires_cookie_csrf_check(_build_request(method="POST", cookies={"access_token": "tok"})) is False

    monkeypatch.setenv("CSRF_ENFORCE", "true")
    for safe_method in ("GET", "HEAD", "OPTIONS"):
        req_safe = _build_request(method=safe_method, cookies={"access_token": "tok"})
        assert _requires_cookie_csrf_check(req_safe) is False

    for preauth in ("/api/auth/login", "/api/auth/register"):
        assert (
            _requires_cookie_csrf_check(_build_request(method="POST", path=preauth, cookies={"access_token": "tok"}))
            is False
        )

    assert _requires_cookie_csrf_check(_build_request(method="POST", path="/api/finanzas/tasa")) is False
    assert (
        _requires_cookie_csrf_check(
            _build_request(method="POST", path="/api/finanzas/tasa", headers={"Authorization": "Bearer abc"})
        )
        is False
    )
    assert (
        _requires_cookie_csrf_check(
            _build_request(
                method="POST",
                path="/api/finanzas/tasa",
                cookies={"access_token": '""', "refresh_token": ""},
            )
        )
        is False
    )

    for mut_method in ("POST", "PUT", "PATCH", "DELETE", "post"):
        assert (
            _requires_cookie_csrf_check(
                _build_request(method=mut_method, path="/api/finanzas/tasa", cookies={"access_token": "tok"})
            )
            is True
        )
    assert (
        _requires_cookie_csrf_check(
            _build_request(method="POST", path="/api/finanzas/tasa", cookies={"refresh_token": "tok"})
        )
        is True
    )

    assert _session_id_from_payload({"sid": "  sid-1  ", "sub": "u@test.com"}) == "sid-1"
    assert _session_id_from_payload({"sid": "", "sub": "  u@test.com  "}) == "u@test.com"
    assert _session_id_from_payload({"sid": "   "}) is None
    assert _session_id_from_payload({}) is None
    assert _session_id_from_payload({"sid": 42}) == "42"

    access_jwt = create_access_token({"sub": "a@b.com", "sid": "sid-acc"})
    expired_jwt = create_access_token({"sub": "a@b.com", "sid": "sid-exp"}, expires_delta=timedelta(minutes=-5))
    refresh_jwt = create_refresh_token({"sub": "a@b.com", "sid": "sid-ref"})

    assert _session_id_from_token("") is None
    assert _session_id_from_token("   ") is None
    assert _session_id_from_token("Bearer   ") is None
    assert _session_id_from_token("token.invalido") is None
    assert _session_id_from_token(f"Bearer {access_jwt}") == "sid-acc"
    assert _session_id_from_token(expired_jwt) == "sid-exp"

    req_both = _build_request(cookies={"access_token": access_jwt, "refresh_token": refresh_jwt})
    assert _extract_cookie_session_id_for_csrf(req_both) == "sid-acc"

    req_fallback = _build_request(cookies={"access_token": "invalido", "refresh_token": refresh_jwt})
    assert _extract_cookie_session_id_for_csrf(req_fallback) == "sid-ref"

    req_invalid = _build_request(cookies={"access_token": "invalido", "refresh_token": "malo"})
    assert _extract_cookie_session_id_for_csrf(req_invalid) is None

    assert _is_valid_cookie_csrf(_build_request(path="/api/auth/logout", cookies={"access_token": "bad"})) is True
    assert _is_valid_cookie_csrf(_build_request(path="/api/finanzas/tasa", cookies={"access_token": "bad"})) is False

    csrf_acc = generate_csrf_token("sid-acc")
    assert (
        _is_valid_cookie_csrf(
            _build_request(
                path="/api/finanzas/tasa",
                cookies={"access_token": f"Bearer {access_jwt}"},
                headers={"X-CSRF-Token": csrf_acc},
            )
        )
        is True
    )
    assert (
        _is_valid_cookie_csrf(
            _build_request(
                path="/api/finanzas/tasa",
                cookies={"access_token": f"Bearer {access_jwt}"},
                headers={"X-CSRF-Token": "invalido"},
            )
        )
        is False
    )


@pytest.mark.asyncio
async def test_csrf_http_enforced_y_bypass_controlado(monkeypatch: pytest.MonkeyPatch) -> None:
    """Valida bloqueo Cookie+Bearer sin CSRF, exención Bearer puro, fallback refresh y logout sin sesión."""
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    access_jwt = create_access_token({"sub": "a@b.com", "sid": "sid-http"})
    refresh_jwt = create_refresh_token({"sub": "a@b.com", "sid": "sid-ref"})
    csrf_access = generate_csrf_token("sid-http")
    csrf_refresh = generate_csrf_token("sid-ref")

    app.dependency_overrides[get_db] = _fake_db_override
    app.dependency_overrides[get_redis_client] = lambda: AsyncMock()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as ac:
            monkeypatch.setenv("CSRF_ENFORCE", "false")
            monkeypatch.setenv("APP_ENV", "development")
            ac.cookies.set("access_token", f"Bearer {access_jwt}")
            assert (await ac.post("/api/auth/logout")).status_code == 200

            configs = (
                {"CSRF_ENFORCE": "true", "APP_ENV": "development"},
                {"CSRF_ENFORCE": "false", "APP_ENV": "production"},
            )
            for env_cfg in configs:
                for key, value in env_cfg.items():
                    monkeypatch.setenv(key, value)

                ac.cookies.clear()
                ac.cookies.set("access_token", f"Bearer {access_jwt}")
                blocked = await ac.post("/api/finanzas/tasa", json={})
                assert blocked.status_code == 403
                assert blocked.json() == {"detail": "Token CSRF inválido o ausente."}
                _assert_oshp_headers(blocked.headers, expect_hsts=env_cfg["APP_ENV"] == "production")

                both = await ac.post(
                    "/api/finanzas/tasa",
                    headers={"Authorization": f"Bearer {access_jwt}"},
                    json={},
                )
                assert both.status_code == 403

                mismatched = await ac.post(
                    "/api/finanzas/tasa",
                    headers={"X-CSRF-Token": "wrong-hmac"},
                    json={},
                )
                assert mismatched.status_code == 403

                logout_ok = await ac.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_access})
                assert logout_ok.status_code == 200

                assert (await ac.get("/health")).status_code == 200
                assert (await ac.head("/health")).status_code == 405
                assert (await ac.options("/api/finanzas/tasa")).status_code == 405

                preauth_login = await ac.post("/api/auth/login", json={})
                assert preauth_login.status_code == 422

                preauth_reg = await ac.post("/api/auth/register", json={})
                assert preauth_reg.status_code == 422

                ac.cookies.clear()
                ac.cookies.set("refresh_token", refresh_jwt)
                assert (await ac.post("/api/auth/logout")).status_code == 403
                logout_ref = await ac.post("/api/auth/logout", headers={"X-CSRF-Token": csrf_refresh})
                assert logout_ref.status_code == 200

                ac.cookies.clear()
                ac.cookies.set("access_token", "token-corrupto")
                assert (await ac.post("/api/auth/logout")).status_code == 200
                assert (await ac.post("/api/finanzas/tasa", json={})).status_code == 403

                ac.cookies.clear()
                bearer_only = await ac.post(
                    "/api/finanzas/tasa",
                    headers={"Authorization": "Bearer dummy"},
                    json={},
                )
                assert bearer_only.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_fetch_metadata_https_y_headers_seguridad(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cubre Fetch Metadata, Vary, detección HTTPS/HSTS por proxy confiable y CSP en rutas docs/API."""
    for site in ("", "   ", "same-origin", "  SAME-ORIGIN ", "same-site", "none", "NONE"):
        assert _is_allowed_fetch_metadata(_build_request(headers={"Sec-Fetch-Site": site})) is True

    assert (
        _is_allowed_fetch_metadata(_build_request(headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "cors"}))
        is False
    )
    assert (
        _is_allowed_fetch_metadata(
            _build_request(
                method="GET",
                headers={"Sec-Fetch-Site": "CROSS-SITE", "Sec-Fetch-Mode": " NAVIGATE ", "Sec-Fetch-Dest": "document"},
            )
        )
        is True
    )
    assert (
        _is_allowed_fetch_metadata(
            _build_request(
                method="HEAD",
                headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Dest": "document"},
            )
        )
        is True
    )
    assert (
        _is_allowed_fetch_metadata(
            _build_request(
                method="POST",
                headers={"Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Dest": "document"},
            )
        )
        is False
    )
    for bad_dest in ("object", "embed", " EMBED "):
        req_bad_dest = _build_request(
            method="GET",
            headers={
                "Sec-Fetch-Site": "cross-site",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Dest": bad_dest,
            },
        )
        assert _is_allowed_fetch_metadata(req_bad_dest) is False

    assert _parse_vary_items(" Origin , , Sec-Fetch-Site , ") == ["Origin", "Sec-Fetch-Site"]
    empty_vary = Response()
    _merge_vary_header(empty_vary)
    assert empty_vary.headers["Vary"] == "Sec-Fetch-Dest, Sec-Fetch-Mode, Sec-Fetch-Site"

    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
    monkeypatch.delenv("APP_ENV", raising=False)

    assert (
        _is_https_request(
            _build_request(scheme="https", headers={"X-Forwarded-Proto": "http"}, client=("198.51.100.10", 1234))
        )
        is True
    )
    assert (
        _is_https_request(
            _build_request(scheme="http", headers={"X-Forwarded-Proto": "https"}, client=("198.51.100.10", 1234))
        )
        is False
    )
    req_no_client = _build_request(scheme="http", headers={"X-Forwarded-Proto": "https"}, client=None)
    assert _is_https_request(req_no_client) is False
    assert (
        _is_https_request(
            _build_request(scheme="http", headers={"X-Forwarded-Proto": " HTTPS , http "}, client=("127.0.0.1", 1234))
        )
        is True
    )
    assert (
        _is_https_request(
            _build_request(scheme="http", headers={"X-Forwarded-Proto": "http, https"}, client=("127.0.0.1", 1234))
        )
        is False
    )

    assert _DOCS_PATHS == frozenset({"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"})
    for doc_path in _DOCS_PATHS:
        res_doc = _apply_security_headers(_build_request(path=doc_path), Response())
        _assert_oshp_headers(res_doc.headers, is_docs=True, expect_hsts=False)

    res_api = _apply_security_headers(
        _build_request(path="/docs/other", headers={"X-Forwarded-Proto": "https"}),
        Response(),
    )
    _assert_oshp_headers(res_api.headers, is_docs=False, expect_hsts=True)


@pytest.mark.asyncio
async def test_proxy_confiable_hsts_y_orden_guardias_pre_ruta(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verifica HSTS con proxy confiable vs no confiable, precedencia de guardias y middleware 500."""
    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    monkeypatch.setenv("COOKIE_SECURE", "false")
    monkeypatch.delenv("APP_ENV", raising=False)

    monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.20.30.40")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as ac:
        untrusted = await ac.get("/health", headers={"X-Forwarded-Proto": "https"})
        assert untrusted.status_code == 200
        assert "strict-transport-security" not in untrusted.headers

        monkeypatch.delenv("TRUSTED_PROXY_IPS", raising=False)
        first_http = await ac.get("/health", headers={"X-Forwarded-Proto": "http, https"})
        assert "strict-transport-security" not in first_http.headers

        first_https = await ac.get("/health", headers={"X-Forwarded-Proto": " HTTPS , http "})
        assert first_https.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"

        for doc_path in ("/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"):
            doc_res = await ac.get(doc_path)
            assert doc_res.status_code == 200
            _assert_oshp_headers(doc_res.headers, is_docs=True)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://testserver") as https_ac:
        monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.20.30.40")
        direct_https = await https_ac.get("/health")
        assert direct_https.headers["strict-transport-security"] == "max-age=31536000; includeSubDomains"

    req_bad_host = _build_request(
        path="/metrics",
        headers={"Host": "evil.com", "Sec-Fetch-Site": "cross-site"},
    )
    guard_400 = _check_pre_route_guards(req_bad_host)
    assert guard_400 is not None and guard_400.status_code == 400

    req_bad_fetch = _build_request(
        path="/metrics",
        headers={"Host": "testserver", "Sec-Fetch-Site": "cross-site", "Sec-Fetch-Mode": "cors"},
    )
    guard_403 = _check_pre_route_guards(req_bad_fetch)
    assert guard_403 is not None and guard_403.status_code == 403

    monkeypatch.setenv("METRICS_AUTH_TOKEN", "tok")
    req_bad_metrics = _build_request(path="/metrics", headers={"Host": "testserver"})
    guard_401 = _check_pre_route_guards(req_bad_metrics)
    assert guard_401 is not None and guard_401.status_code == 401
    assert _check_pre_route_guards(_build_request(path="/health", headers={"Host": "testserver"})) is None

    async def _fail_next(_req: Request) -> Response:
        raise RuntimeError("boom_directo")

    caplog.set_level(logging.ERROR)
    res_500 = await security_headers_middleware(
        _build_request(method="POST", path="/ruta-boom", headers={"Host": "testserver"}),
        _fail_next,
    )
    assert res_500.status_code == 500
    assert json.loads(bytes(res_500.body).decode("utf-8")) == {"detail": "Error interno del servidor."}
    _assert_oshp_headers(res_500.headers)
    assert "Error interno no controlado en POST /ruta-boom" in caplog.text


@pytest.mark.asyncio
async def test_exception_handlers_422_405_y_500_http(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Valida manejadores 422 (dev vs prod), 405 con Allow en rutas parametrizadas y 500 HTTP con OSHP."""
    ops = {
        "get": {},
        "put": {},
        "post": {},
        "delete": {},
        "options": {},
        "head": {},
        "patch": {},
        "trace": {},
        "parameters": [],
        "x-custom": {},
    }
    assert _extraer_metodos_ops(ops) == {"GET", "PUT", "POST", "DELETE", "OPTIONS", "HEAD", "PATCH", "TRACE"}
    assert _metodos_permitidos("/api/finanzas/tasa") == {"GET", "POST"}
    assert _metodos_permitidos("/api/accesos/pases/mios") == {"GET"}
    assert _metodos_permitidos("/api/accesos/pases/42") == {"DELETE"}
    assert _metodos_permitidos("/api/accesos/pases/42/extra") == set()
    assert _metodos_permitidos("/no-existe-openapi") == set()

    exc_422 = RequestValidationError(errors=[{"loc": ("body", "password"), "msg": "Field required", "type": "missing"}])
    monkeypatch.setenv("APP_ENV", "development")
    res_422_dev = await validation_exception_handler(_build_request(method="POST", path="/api/auth/login"), exc_422)
    assert res_422_dev.status_code == 422
    assert isinstance(json.loads(bytes(res_422_dev.body).decode("utf-8"))["detail"], list)

    caplog.set_level(logging.WARNING)
    monkeypatch.setenv("APP_ENV", "production")
    res_422_prod = await validation_exception_handler(_build_request(method="POST", path="/api/auth/login"), exc_422)
    assert res_422_prod.status_code == 422
    assert json.loads(bytes(res_422_prod.body).decode("utf-8")) == {
        "detail": "Los datos proporcionados no cumplen con los requisitos de validación."
    }
    assert "Fallo de validación 422 en POST /api/auth/login" in caplog.text

    res_405_custom = await http_exception_handler(
        _build_request(method="PUT", path="/api/finanzas/tasa"),
        StarletteHTTPException(
            status_code=405,
            detail="Method Not Allowed",
            headers={"Allow": "PATCH", "X-Tag": "keep"},
        ),
    )
    assert res_405_custom.status_code == 405
    assert res_405_custom.headers["allow"] == "GET, POST"
    assert res_405_custom.headers["x-tag"] == "keep"

    res_405_unknown = await http_exception_handler(
        _build_request(method="PUT", path="/ruta-sin-openapi"),
        StarletteHTTPException(
            status_code=405,
            detail="Method Not Allowed",
            headers={"Allow": "GET", "X-Tag": "keep"},
        ),
    )
    assert res_405_unknown.headers["allow"] == "GET"
    assert res_405_unknown.headers["x-tag"] == "keep"

    res_404_none = await http_exception_handler(
        _build_request(method="GET", path="/inexistente"),
        StarletteHTTPException(status_code=404, detail="Not Found", headers=None),
    )
    assert res_404_none.status_code == 404
    assert json.loads(bytes(res_404_none.body).decode("utf-8")) == {"detail": "Not Found"}

    res_401_headers = await http_exception_handler(
        _build_request(method="GET", path="/api/finanzas/tasa"),
        StarletteHTTPException(status_code=401, detail="No auth", headers={"WWW-Authenticate": "Bearer"}),
    )
    assert res_401_headers.headers["www-authenticate"] == "Bearer"

    monkeypatch.delenv("ALLOWED_HOSTS", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    app.dependency_overrides[get_db] = _fake_db_override
    app.dependency_overrides[get_redis_client] = lambda: AsyncMock()
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as ac:
            monkeypatch.setenv("APP_ENV", "development")
            http_422_dev = await ac.post("/api/auth/login", json={"correo": "x@y.com"})
            assert http_422_dev.status_code == 422
            assert isinstance(http_422_dev.json()["detail"], list)
            _assert_oshp_headers(http_422_dev.headers)

            monkeypatch.setenv("APP_ENV", "production")
            http_422_prod = await ac.post("/api/auth/login", json={"correo": "x@y.com"})
            assert http_422_prod.status_code == 422
            assert http_422_prod.json() == {
                "detail": "Los datos proporcionados no cumplen con los requisitos de validación."
            }
            _assert_oshp_headers(http_422_prod.headers, expect_hsts=True)

            http_405_param = await ac.get("/api/accesos/pases/42")
            assert http_405_param.status_code == 405
            assert http_405_param.headers["allow"] == "DELETE"
            _assert_oshp_headers(http_405_param.headers, expect_hsts=True)

            http_405_put = await ac.put("/api/finanzas/tasa", json={})
            assert http_405_put.status_code == 405
            assert http_405_put.headers["allow"] == "GET, POST"

            app.dependency_overrides[get_db] = _boom_db_override
            http_500 = await ac.post("/api/auth/login", json={"correo": "x@y.com", "password": "password123"})
            assert http_500.status_code == 500
            assert http_500.json() == {"detail": "Error interno del servidor."}
            _assert_oshp_headers(http_500.headers, expect_hsts=True)
    finally:
        app.dependency_overrides.clear()
