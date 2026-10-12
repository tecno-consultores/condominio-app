import pytest
from pydantic import ValidationError
from src.schemas import UsuarioCreate, UsuarioResponse


def test_usuario_schema_valido() -> None:
    """Valida que Pydantic acepta un payload de registro correcto con los nuevos campos"""
    user = UsuarioCreate(
        nombre="Juan Perez",
        cedula="V-12345678",
        correo="juan@example.com",
        telefono="+584121234567",
        password="SecurePassword123!",
        unidad_solicitada_id=1,
        tipo_ocupante_solicitado="PROPIETARIO"
    )
    assert user.nombre == "Juan Perez"
    assert user.password == "SecurePassword123!"
    assert user.unidad_solicitada_id == 1
    assert user.tipo_ocupante_solicitado == "PROPIETARIO"


def test_usuario_schema_correo_invalido() -> None:
    """Valida que Pydantic rechaza correos malformados de acuerdo a EmailStr"""
    with pytest.raises(ValidationError) as exc_info:
        UsuarioCreate(
            nombre="Maria Lopez",
            cedula="V-87654321",
            correo="maria-correo-falso",
            telefono="+584129876543",
            password="SecurePassword123!",
            unidad_solicitada_id=1,
            tipo_ocupante_solicitado="INQUILINO"
        )

    assert "correo" in str(exc_info.value)


def test_usuario_response_from_attributes() -> None:
    """Valida que UsuarioResponse construye correctamente el modelo a partir de atributos"""
    class MockUsuario:
        id: int = 10
        nombre: str = "Ana Morales"
        cedula: str = "V-20000000"
        correo: str = "ana@example.com"
        telefono: str = "+584140000000"
        es_activo: bool = False
        rol: str = "FANTASMA"

    response = UsuarioResponse.model_validate(MockUsuario())
    assert response.id == 10
    assert response.nombre == "Ana Morales"
    assert response.es_activo is False
    assert response.rol == "FANTASMA"
