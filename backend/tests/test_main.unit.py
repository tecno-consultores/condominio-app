import pytest
from fastapi.testclient import TestClient

from src.main import app


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
