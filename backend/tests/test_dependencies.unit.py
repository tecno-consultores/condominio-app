"""Pruebas de la dependencia get_current_user (ciclo de vida de la cookie JWT)."""

from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.database import get_db
from src.main import app
from src.security import create_access_token

PROTEGIDO = "/api/finanzas/tasa"


def _session(*results: Any) -> AsyncMock:
    session = AsyncMock()
    session.execute.side_effect = list(results)
    return session


def _result(value: Any) -> MagicMock:
    result = MagicMock()
    result.scalars().first.return_value = value
    return result


class FakeUser:
    id: int = 3
    correo: str = "tesorero@test.com"
    rol: str = "TESORERO"


def test_endpoint_protegido_sin_cookie(client: TestClient) -> None:
    response = client.get(PROTEGIDO)
    assert response.status_code == 401
    assert "No autenticado" in response.json()["detail"]


def test_token_expirado(client: TestClient) -> None:
    token = create_access_token(data={"sub": "x@test.com"}, expires_delta=timedelta(seconds=-10))
    client.cookies.set("access_token", f"Bearer {token}")

    response = client.get(PROTEGIDO)

    assert response.status_code == 401
    assert "expirado" in response.json()["detail"]
    client.cookies.clear()


def test_token_invalido(client: TestClient) -> None:
    client.cookies.set("access_token", "Bearer token_corrupto")

    response = client.get(PROTEGIDO)

    assert response.status_code == 401
    assert "inválido" in response.json()["detail"]
    client.cookies.clear()


def test_token_sin_identificacion(client: TestClient) -> None:
    token = create_access_token(data={"rol": "TESORERO"})
    client.cookies.set("access_token", f"Bearer {token}")

    response = client.get(PROTEGIDO)

    assert response.status_code == 401
    assert "sin identificación" in response.json()["detail"]
    client.cookies.clear()


def test_usuario_no_encontrado(client: TestClient) -> None:
    token = create_access_token(data={"sub": "nadie@test.com"})
    session = _session(_result(None))
    app.dependency_overrides[get_db] = lambda: session
    client.cookies.set("access_token", f"Bearer {token}")

    response = client.get(PROTEGIDO)

    assert response.status_code == 401
    assert "Usuario no encontrado" in response.json()["detail"]
    client.cookies.clear()
    app.dependency_overrides = {}


def test_usuario_valido_continua_al_endpoint(client: TestClient) -> None:
    token = create_access_token(data={"sub": "tesorero@test.com"})
    session = _session(_result(FakeUser()), _result(None))
    app.dependency_overrides[get_db] = lambda: session
    client.cookies.set("access_token", f"Bearer {token}")

    response = client.get(PROTEGIDO)

    assert response.status_code == 404
    client.cookies.clear()
    app.dependency_overrides = {}
