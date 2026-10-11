import pytest
from unittest.mock import AsyncMock, MagicMock
from src.main import app

def test_register_user_success(client, mocker):
    """Simula el registro exitoso aislando la base de datos"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result
    
    # Mocking id after flush
    async def mock_flush(*args, **kwargs):
        pass
    mock_session.flush = mock_flush
    
    from src.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_session

    payload = {
        "nombre": "Pedro QA",
        "cedula": "V-9999999",
        "correo": "pedro@test.com",
        "telefono": "12345",
        "password": "Mypassword1!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
    }
    headers = {
        "Idempotency-Key": "123e4567-e89b-12d3-a456-426614174000"
    }
    response = client.post("/api/auth/register", json=payload, headers=headers)
    
    assert response.status_code == 201
    assert response.json()["es_activo"] == False
    assert response.json()["rol"] == "FANTASMA"
    
    app.dependency_overrides = {}

def test_register_missing_idempotency_key(client):
    """Falla si no se envía el header de idempotencia"""
    payload = {
        "nombre": "Pedro QA",
        "cedula": "V-9999999",
        "correo": "pedro@test.com",
        "telefono": "12345",
        "password": "Mypassword1!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422 # Error de validación Pydantic por Header faltante

def test_register_user_db_failure(client, mocker):
    """Simula una falla catastrófica en la BD durante el registro"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result
    
    mock_session.commit.side_effect = Exception("DB Connection Lost")
    
    from src.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_session

    payload = {
        "nombre": "Pedro Error",
        "cedula": "V-1111111",
        "correo": "error@test.com",
        "telefono": "123",
        "password": "Mypassword1!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
    }
    headers = {
        "Idempotency-Key": "123e4567-e89b-12d3-a456-426614174001"
    }
    response = client.post("/api/auth/register", json=payload, headers=headers)
    
    assert response.status_code == 500
    assert "Error en base de datos" in response.json()["detail"]
    
    app.dependency_overrides = {}
    
def test_login_set_httponly_cookie(client, mocker):
    """Simula un login exitoso validando la creación de la cookie HttpOnly"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    from src.security import get_password_hash
    class FakeUser:
        correo = "admin@test.com"
        rol = "PRESIDENTE"
        password_hash = get_password_hash("secure")
        
    mock_result.scalars().first.return_value = FakeUser()
    mock_session.execute.return_value = mock_result
    
    from src.database import get_db
    app.dependency_overrides[get_db] = lambda: mock_session
    
    payload = {"correo": "admin@test.com", "password": "secure"}
    response = client.post("/api/auth/login", json=payload)
    
    assert response.status_code == 200
    cookies = response.headers.get_all("set-cookie")
    assert any("access_token" in c and "HttpOnly" in c for c in cookies)
    
    app.dependency_overrides = {}