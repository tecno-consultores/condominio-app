import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import timedelta
from src.main import app
from src.database import get_db
from src.redis_client import get_redis_client
from src.security import create_access_token, get_password_hash

def test_register_user_success(client):
    """Simula el registro exitoso aislando la base de datos y Redis"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result
    
    async def mock_flush(*args, **kwargs):
        pass
    mock_session.flush = mock_flush

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True  # Clave nueva

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

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
    assert response.json()["es_activo"] is False
    assert response.json()["rol"] == "FANTASMA"
    
    app.dependency_overrides = {}

def test_register_user_duplicate_idempotency_key(client):
    """Falla con 409 Conflict si la Idempotency-Key ya fue procesada en Redis"""
    mock_session = AsyncMock()
    mock_redis = AsyncMock()
    mock_redis.set.return_value = False  # Clave ya existente

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    payload = {
        "nombre": "Pedro Duplicado",
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
    
    assert response.status_code == 409
    assert "Petición duplicada detectada" in response.json()["detail"]
    
    app.dependency_overrides = {}

def test_register_user_already_registered(client):
    """Falla con 400 si el usuario (correo o cédula) ya existe en base de datos"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = MagicMock()  # Usuario encontrado
    mock_session.execute.return_value = mock_result

    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

    payload = {
        "nombre": "Pedro Ya Existe",
        "cedula": "V-9999999",
        "correo": "pedro@test.com",
        "telefono": "12345",
        "password": "Mypassword1!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
    }
    headers = {
        "Idempotency-Key": "unique-idempotency-key-1"
    }
    response = client.post("/api/auth/register", json=payload, headers=headers)
    
    assert response.status_code == 400
    assert "Usuario ya registrado" in response.json()["detail"]
    
    app.dependency_overrides = {}

def test_register_missing_idempotency_key(client):
    """Falla con 422 si no se envía el header de idempotencia"""
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
    assert response.status_code == 422

def test_register_user_db_failure(client):
    """Simula una falla catastrófica en la BD durante el registro"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result
    mock_session.commit.side_effect = Exception("DB Connection Lost")
    
    mock_redis = AsyncMock()
    mock_redis.set.return_value = True

    app.dependency_overrides[get_db] = lambda: mock_session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis

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

def test_login_set_httponly_cookie(client):
    """Simula un login exitoso validando la creación de la cookie HttpOnly"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    class FakeUser:
        id = 1
        correo = "admin@test.com"
        rol = "PRESIDENTE"
        password_hash = get_password_hash("secure")
        
    mock_result.scalars().first.return_value = FakeUser()
    mock_session.execute.return_value = mock_result
    
    app.dependency_overrides[get_db] = lambda: mock_session
    
    payload = {"correo": "admin@test.com", "password": "secure"}
    response = client.post("/api/auth/login", json=payload)
    
    assert response.status_code == 200
    cookies = response.headers.get_all("set-cookie")
    assert any("access_token" in c and "HttpOnly" in c for c in cookies)
    
    app.dependency_overrides = {}

def test_login_invalid_credentials(client):
    """Simula un login con credenciales erróneas devolviendo 401"""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars().first.return_value = None
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    payload = {"correo": "noexiste@test.com", "password": "wrong"}
    response = client.post("/api/auth/login", json=payload)

    assert response.status_code == 401
    assert "Credenciales inválidas" in response.json()["detail"]

    app.dependency_overrides = {}

def test_me_without_cookie_fails(client):
    """Llamada a /api/auth/me sin cookie debe responder 401"""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "No autenticado" in response.json()["detail"]

def test_me_with_valid_token_success(client):
    """Llamada a /api/auth/me con token válido y usuario en base de datos"""
    token = create_access_token(data={"sub": "pedro@test.com", "rol": "FANTASMA", "id": 5})
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    class FakeUser:
        id = 5
        correo = "pedro@test.com"
        nombre = "Pedro QA"
        rol = "FANTASMA"
        es_activo = False

    mock_result.scalars().first.return_value = FakeUser()
    mock_session.execute.return_value = mock_result

    app.dependency_overrides[get_db] = lambda: mock_session

    client.cookies.set("access_token", f"Bearer {token}")
    response = client.get("/api/auth/me")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 5
    assert data["correo"] == "pedro@test.com"
    assert data["rol"] == "FANTASMA"
    assert data["es_activo"] is False

    client.cookies.clear()
    app.dependency_overrides = {}

def test_me_with_expired_token(client):
    """Llamada a /api/auth/me con token expirado debe responder 401"""
    expired_token = create_access_token(
        data={"sub": "expired@test.com"},
        expires_delta=timedelta(seconds=-10)
    )

    client.cookies.set("access_token", f"Bearer {expired_token}")
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert "Token expirado" in response.json()["detail"]

    client.cookies.clear()

def test_me_with_invalid_token(client):
    """Llamada a /api/auth/me con token adulterado/inválido debe responder 401"""
    client.cookies.set("access_token", "Bearer token_completamente_invalido")
    response = client.get("/api/auth/me")

    assert response.status_code == 401
    assert "Token inválido" in response.json()["detail"]

    client.cookies.clear()
