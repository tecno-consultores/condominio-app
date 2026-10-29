from datetime import date
from decimal import Decimal

from src.models import (
    AuditoriaRecibo,
    ContratoOcupacion,
    Egreso,
    Estructura,
    PagoReportado,
    Recibo,
    ReporteMensual,
    TasaCambio,
    Unidad,
    Usuario,
)


def test_modelo_usuario_instanciacion() -> None:
    """Valida la creación y valores por defecto del modelo Usuario"""
    usuario = Usuario(
        nombre="Carlos Gomez",
        cedula="V-19876543",
        correo="carlos@example.com",
        telefono="+584149998877",
        password_hash="hashed_pw_example",
        es_activo=False,
        rol="FANTASMA",
    )
    assert usuario.nombre == "Carlos Gomez"
    assert usuario.cedula == "V-19876543"
    assert usuario.es_activo is False
    assert usuario.rol == "FANTASMA"


def test_modelo_estructura_instanciacion() -> None:
    """Valida la instanciación de Estructura (Torre, Edificio o Calle)"""
    estructura = Estructura(nombre="Torre A", tipo="EDIFICIO")
    assert estructura.nombre == "Torre A"
    assert estructura.tipo == "EDIFICIO"


def test_modelo_unidad_instanciacion() -> None:
    """Valida la instanciación de Unidad asociada a una estructura"""
    unidad = Unidad(identificador="A-101", estructura_id=1)
    assert unidad.identificador == "A-101"
    assert unidad.estructura_id == 1


def test_modelo_contrato_ocupacion_instanciacion() -> None:
    """Valida la tabla histórica ContratoOcupacion con sus campos y valores por defecto"""
    contrato = ContratoOcupacion(usuario_id=1, unidad_id=2, tipo_ocupante="PROPIETARIO", es_activo=False)
    assert contrato.usuario_id == 1
    assert contrato.unidad_id == 2
    assert contrato.tipo_ocupante == "PROPIETARIO"
    assert contrato.es_activo is False


def test_modelo_tasa_cambio_instanciacion() -> None:
    """Valida la tasa de cambio USD/VES registrada por día"""
    tasa = TasaCambio(fecha=date(2026, 10, 12), tasa_usd_ves=Decimal("36.5000"))
    assert tasa.fecha == date(2026, 10, 12)
    assert tasa.tasa_usd_ves == Decimal("36.5000")


def test_modelo_recibo_instanciacion() -> None:
    """Valida el recibo con su monto y saldo pagado"""
    recibo = Recibo(
        unidad_id=1,
        periodo="2026-10",
        monto_usd=Decimal("100.00"),
        monto_pagado_usd=Decimal("0.00"),
        estado="PENDIENTE",
        bloqueado=False,
    )
    assert recibo.periodo == "2026-10"
    assert recibo.monto_usd == Decimal("100.00")
    assert recibo.estado == "PENDIENTE"
    assert recibo.bloqueado is False


def test_modelo_pago_reportado_instanciacion() -> None:
    """Valida que el pago guarda la tasa del día exacto del reporte"""
    pago = PagoReportado(
        recibo_id=1,
        usuario_id=2,
        monto=Decimal("3650.00"),
        moneda="VES",
        monto_usd=Decimal("100.00"),
        tasa_cambio=Decimal("36.5000"),
        metodo_pago="PAGO_MOVIL",
        numero_referencia="REF-123",
        estado="EN_REVISION",
    )
    assert pago.moneda == "VES"
    assert pago.tasa_cambio == Decimal("36.5000")
    assert pago.numero_referencia == "REF-123"
    assert pago.estado == "EN_REVISION"


def test_modelo_egreso_instanciacion() -> None:
    """Valida el egreso registrado por categoría con su monto en USD"""
    egreso = Egreso(
        periodo="2026-10",
        categoria="MANTENIMIENTO",
        descripcion="Reparación de ascensor",
        monto=Decimal("500.00"),
        moneda="USD",
        monto_usd=Decimal("500.00"),
        tasa_cambio=Decimal("36.5000"),
        url_factura="https://minio.local/factura.avif",
        bloqueado=False,
    )
    assert egreso.categoria == "MANTENIMIENTO"
    assert egreso.monto_usd == Decimal("500.00")
    assert egreso.bloqueado is False


def test_modelo_auditoria_recibo_instanciacion() -> None:
    """Valida la pista de auditoría con motivo obligatorio de rechazo"""
    auditoria = AuditoriaRecibo(
        recibo_id=1,
        pago_id=5,
        usuario_id=3,
        estado_viejo="EN_REVISION",
        estado_nuevo="RECHAZADO",
        motivo="Comprobante ilegible",
    )
    assert auditoria.estado_nuevo == "RECHAZADO"
    assert auditoria.motivo == "Comprobante ilegible"


def test_modelo_reporte_mensual_instanciacion() -> None:
    """Valida el reporte mensual con su estado de candado contable"""
    reporte = ReporteMensual(periodo="2026-10", estado="PRELIMINAR")
    assert reporte.periodo == "2026-10"
    assert reporte.estado == "PRELIMINAR"
    assert reporte.cerrado_en is None
