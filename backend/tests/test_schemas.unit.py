from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.schemas import (
    CierreMensualRequest,
    EgresoCreate,
    PagoRechazo,
    PagoReportar,
    ReciboCreate,
    TasaCambioCreate,
    UsuarioCreate,
    UsuarioResponse,
)


def test_usuario_schema_valido() -> None:
    """Valida que Pydantic acepta un payload de registro correcto con los nuevos campos"""
    user = UsuarioCreate(
        nombre="Juan Perez",
        cedula="V-12345678",
        correo="juan@example.com",
        telefono="+584121234567",
        password="SecurePassword123!",
        unidad_solicitada_id=1,
        tipo_ocupante_solicitado="PROPIETARIO",
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
            tipo_ocupante_solicitado="INQUILINO",
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


def test_pago_reportar_schema_valido() -> None:
    pago = PagoReportar(recibo_id=1, monto=Decimal("100.00"), moneda="USD", metodo_pago="EFECTIVO")
    assert pago.moneda == "USD"
    assert pago.numero_referencia is None
    assert pago.url_comprobante is None


def test_pago_reportar_moneda_invalida() -> None:
    with pytest.raises(ValidationError):
        PagoReportar.model_validate({"recibo_id": 1, "monto": "100.00", "moneda": "EUR", "metodo_pago": "EFECTIVO"})


def test_pago_reportar_monto_no_positivo() -> None:
    with pytest.raises(ValidationError):
        PagoReportar(recibo_id=1, monto=Decimal(0), moneda="USD", metodo_pago="EFECTIVO")


def test_pago_rechazo_motivo_vacio_invalido() -> None:
    with pytest.raises(ValidationError):
        PagoRechazo(motivo="")


def test_pago_rechazo_motivo_valido() -> None:
    assert PagoRechazo(motivo="Sin comprobante").motivo == "Sin comprobante"


def test_tasa_cambio_schema_tasa_no_positiva() -> None:
    with pytest.raises(ValidationError):
        TasaCambioCreate(tasa_usd_ves=Decimal(0))


def test_tasa_cambio_schema_fecha_opcional() -> None:
    tasa = TasaCambioCreate(tasa_usd_ves=Decimal("36.5000"))
    assert tasa.fecha is None


def test_recibo_schema_periodo_invalido() -> None:
    with pytest.raises(ValidationError):
        ReciboCreate(unidad_id=1, periodo="2026/10", monto_usd=Decimal("100.00"))


def test_recibo_schema_valido() -> None:
    recibo = ReciboCreate(unidad_id=1, periodo="2026-10", monto_usd=Decimal("100.00"))
    assert recibo.periodo == "2026-10"


def test_egreso_create_schema_valido() -> None:
    egreso = EgresoCreate(
        periodo="2026-10",
        categoria="LIMPIEZA",
        descripcion="Insumos",
        monto=Decimal("50.00"),
        moneda="VES",
    )
    assert egreso.categoria == "LIMPIEZA"


def test_cierre_mensual_request_valido() -> None:
    assert CierreMensualRequest(periodo="2026-10").periodo == "2026-10"


def test_cierre_mensual_request_periodo_invalido() -> None:
    with pytest.raises(ValidationError):
        CierreMensualRequest(periodo="octubre")


def test_url_evidencia_segura_bloquea_esquemas_peligrosos() -> None:
    """Valida que UrlEvidenciaSegura bloquea javascript:, data:, file: y URLs sin esquema válido."""
    for url_maliciosa in [
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "file:///etc/passwd",
        "   ",
        "ftp://servidor.interno/archivo.png",
    ]:
        with pytest.raises(ValidationError):
            PagoReportar(
                recibo_id=1,
                monto=Decimal("50.00"),
                moneda="USD",
                metodo_pago="EFECTIVO",
                url_comprobante=url_maliciosa,
            )

    pago_https = PagoReportar(
        recibo_id=1,
        monto=Decimal("50.00"),
        moneda="USD",
        metodo_pago="EFECTIVO",
        url_comprobante="https://cdn.condominio.local/recibos/1.avif",
    )
    assert pago_https.url_comprobante == "https://cdn.condominio.local/recibos/1.avif"

    pago_relativo = PagoReportar(
        recibo_id=1,
        monto=Decimal("50.00"),
        moneda="USD",
        metodo_pago="EFECTIVO",
        url_comprobante="/media/recibos/1.avif",
    )
    assert pago_relativo.url_comprobante == "/media/recibos/1.avif"
