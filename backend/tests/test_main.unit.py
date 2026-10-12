from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """
    Verifica que el punto de entrada principal (Healthcheck) de la API responda correctamente
    con un estado 200 y el JSON esperado. Esta prueba asegura que FastAPI levantó correctamente.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_options_405_incluye_allow_completo(client: TestClient) -> None:
    """Un OPTIONS sobre un path con varios verbos devuelve 405 con el header Allow completo."""
    response = client.options("/api/finanzas/tasa")
    assert response.status_code == 405
    allow = response.headers.get("allow", "")
    assert "GET" in allow
    assert "POST" in allow


def test_respuestas_no_cacheables(client: TestClient) -> None:
    """Toda respuesta lleva Cache-Control: no-store para evitar almacenamiento de datos sensibles."""
    assert client.get("/health").headers["cache-control"] == "no-store"
    assert client.get("/no-existe").headers["cache-control"] == "no-store"
