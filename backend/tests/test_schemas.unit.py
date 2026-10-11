import pytest
from pydantic import ValidationError
from src.schemas import UsuarioCreate

def test_usuario_schema_valido():
    """Valida que Pydantic acepta un payload de registro correcto con los nuevos campos"""
    data = {
        "nombre": "Juan Perez",
        "cedula": "V-12345678",
        "correo": "juan@example.com",
        "telefono": "+584121234567",
        "password": "SecurePassword123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "PROPIETARIO"
    }
    user = UsuarioCreate(**data)
    assert user.nombre == "Juan Perez"
    assert user.password == "SecurePassword123!"

def test_usuario_schema_correo_invalido():
    """Valida que Pydantic rechaza correos malformados de acuerdo a EmailStr"""
    data = {
        "nombre": "Maria Lopez",
        "cedula": "V-87654321",
        "correo": "maria-correo-falso",
        "telefono": "+584129876543",
        "password": "SecurePassword123!",
        "unidad_solicitada_id": 1,
        "tipo_ocupante_solicitado": "INQUILINO"
    }
    with pytest.raises(ValidationError) as exc_info:
        UsuarioCreate(**data)
    
    assert "correo" in str(exc_info.value)