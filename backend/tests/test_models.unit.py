from src.models import Usuario, Estructura, Unidad, ContratoOcupacion


def test_modelo_usuario_instanciacion() -> None:
    """Valida la creación y valores por defecto del modelo Usuario"""
    usuario = Usuario(
        nombre="Carlos Gomez",
        cedula="V-19876543",
        correo="carlos@example.com",
        telefono="+584149998877",
        password_hash="hashed_pw_example",
        es_activo=False,
        rol="FANTASMA"
    )
    assert usuario.nombre == "Carlos Gomez"
    assert usuario.cedula == "V-19876543"
    assert usuario.es_activo is False
    assert usuario.rol == "FANTASMA"


def test_modelo_estructura_instanciacion() -> None:
    """Valida la instanciación de Estructura (Torre, Edificio o Calle)"""
    estructura = Estructura(
        nombre="Torre A",
        tipo="EDIFICIO"
    )
    assert estructura.nombre == "Torre A"
    assert estructura.tipo == "EDIFICIO"


def test_modelo_unidad_instanciacion() -> None:
    """Valida la instanciación de Unidad asociada a una estructura"""
    unidad = Unidad(
        identificador="A-101",
        estructura_id=1
    )
    assert unidad.identificador == "A-101"
    assert unidad.estructura_id == 1


def test_modelo_contrato_ocupacion_instanciacion() -> None:
    """Valida la tabla histórica ContratoOcupacion con sus campos y valores por defecto"""
    contrato = ContratoOcupacion(
        usuario_id=1,
        unidad_id=2,
        tipo_ocupante="PROPIETARIO",
        es_activo=False
    )
    assert contrato.usuario_id == 1
    assert contrato.unidad_id == 2
    assert contrato.tipo_ocupante == "PROPIETARIO"
    assert contrato.es_activo is False
