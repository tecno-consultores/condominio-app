from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    """
    Verifica que el punto de entrada principal (Healthcheck) de la API responda correctamente
    con un estado 200 y el JSON esperado. Esta prueba asegura que FastAPI levantó correctamente.
    """
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
