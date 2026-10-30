"""Pruebas de mutación súper estrictas del núcleo matemático financiero.

Se atacan todas las fronteras de "pago parcial vs total", la conversión por la
tasa del día y el redondeo, de modo que cualquier mutante lógico sea detectado.
"""

from decimal import Decimal

import pytest
from src.finanzas import (
    CERO,
    ESTADO_PAGADO,
    ESTADO_PARCIAL,
    ESTADO_PENDIENTE,
    ErrorFinanciero,
    aplicar_credito_disponible,
    aplicar_pago,
    calcular_deuda_total,
    calcular_excedente_pago,
    calcular_saldo_pendiente,
    construir_qr_token_solvencia,
    convertir_a_usd,
    cuantizar,
    determinar_estado_recibo,
    generar_firma_solvencia,
    prorratear_partes_iguales,
    prorratear_por_alicuotas,
    requiere_referencia,
    validar_referencia,
    validar_suma_alicuotas,
    verificar_firma_solvencia,
)


def test_error_financiero_es_value_error() -> None:
    assert issubclass(ErrorFinanciero, ValueError)


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (Decimal("1.005"), Decimal("1.01")),
        (Decimal("1.004"), Decimal("1.00")),
        (Decimal("0.015"), Decimal("0.02")),
        (Decimal("99.999"), Decimal("100.00")),
        (Decimal("3.33"), Decimal("3.33")),
    ],
)
def test_cuantizar_redondeo_half_up(entrada: Decimal, esperado: Decimal) -> None:
    assert cuantizar(entrada) == esperado


def test_convertir_usd_es_identidad() -> None:
    assert convertir_a_usd(Decimal("100.00"), "USD", Decimal("36.5000")) == Decimal("100.00")


def test_convertir_usd_minusculas() -> None:
    assert convertir_a_usd(Decimal("50.00"), "usd", Decimal("10.0000")) == Decimal("50.00")


def test_convertir_usd_no_exige_tasa_positiva() -> None:
    assert convertir_a_usd(Decimal("10.00"), "USD", Decimal("0")) == Decimal("10.00")


def test_convertir_ves_a_usd() -> None:
    assert convertir_a_usd(Decimal("3650.00"), "VES", Decimal("36.5000")) == Decimal("100.00")


def test_convertir_ves_redondea_a_centavos() -> None:
    assert convertir_a_usd(Decimal("100.00"), "VES", Decimal("36.5000")) == Decimal("2.74")


def test_convertir_moneda_no_soportada_falla() -> None:
    with pytest.raises(ErrorFinanciero, match="Moneda no soportada"):
        convertir_a_usd(Decimal("10.00"), "EUR", Decimal("36.5000"))


def test_convertir_ves_con_tasa_cero_falla() -> None:
    with pytest.raises(ErrorFinanciero, match="mayor que cero"):
        convertir_a_usd(Decimal("10.00"), "VES", Decimal("0"))


def test_convertir_ves_con_tasa_negativa_falla() -> None:
    with pytest.raises(ErrorFinanciero, match="mayor que cero"):
        convertir_a_usd(Decimal("10.00"), "VES", Decimal("-5"))


@pytest.mark.parametrize("metodo", ["ZELLE", "PAGO_MOVIL", "TRANSFERENCIA"])
def test_requiere_referencia_metodos_que_la_exigen(metodo: str) -> None:
    assert requiere_referencia(metodo) is True


def test_requiere_referencia_es_case_insensitive() -> None:
    assert requiere_referencia("zelle") is True


def test_requiere_referencia_efectivo_no_la_exige() -> None:
    assert requiere_referencia("EFECTIVO") is False


def test_validar_referencia_con_referencia_ok() -> None:
    validar_referencia("ZELLE", "REF-123")


def test_validar_referencia_efectivo_sin_referencia_ok() -> None:
    validar_referencia("EFECTIVO", None)


def test_validar_referencia_ausente_falla() -> None:
    with pytest.raises(ErrorFinanciero, match="referencia es obligatorio"):
        validar_referencia("PAGO_MOVIL", None)


def test_validar_referencia_solo_espacios_falla() -> None:
    with pytest.raises(ErrorFinanciero, match="referencia es obligatorio"):
        validar_referencia("TRANSFERENCIA", "   ")


def test_validar_referencia_vacia_falla() -> None:
    with pytest.raises(ErrorFinanciero, match="referencia es obligatorio"):
        validar_referencia("ZELLE", "")


@pytest.mark.parametrize(
    ("monto", "pagado", "esperado"),
    [
        (Decimal("100.00"), Decimal("0.00"), Decimal("100.00")),
        (Decimal("100.00"), Decimal("40.00"), Decimal("60.00")),
        (Decimal("100.00"), Decimal("100.00"), Decimal("0.00")),
        (Decimal("100.00"), Decimal("120.00"), Decimal("0.00")),
    ],
)
def test_calcular_saldo_pendiente(monto: Decimal, pagado: Decimal, esperado: Decimal) -> None:
    assert calcular_saldo_pendiente(monto, pagado) == esperado


def test_determinar_estado_pendiente() -> None:
    assert determinar_estado_recibo(Decimal("100.00"), Decimal("0.00")) == ESTADO_PENDIENTE


def test_determinar_estado_parcial() -> None:
    assert determinar_estado_recibo(Decimal("100.00"), Decimal("99.99")) == ESTADO_PARCIAL


def test_determinar_estado_pagado_frontera_exacta() -> None:
    assert determinar_estado_recibo(Decimal("100.00"), Decimal("100.00")) == ESTADO_PAGADO


def test_determinar_estado_pagado_con_excedente() -> None:
    assert determinar_estado_recibo(Decimal("100.00"), Decimal("100.01")) == ESTADO_PAGADO


def test_aplicar_pago_parcial() -> None:
    nuevo_pagado, estado = aplicar_pago(Decimal("100.00"), Decimal("0.00"), Decimal("40.00"))
    assert nuevo_pagado == Decimal("40.00")
    assert estado == ESTADO_PARCIAL


def test_aplicar_pago_parcial_acumula_pagos_previos() -> None:
    nuevo_pagado, estado = aplicar_pago(Decimal("100.00"), Decimal("40.00"), Decimal("30.00"))
    assert nuevo_pagado == Decimal("70.00")
    assert estado == ESTADO_PARCIAL


def test_aplicar_pago_total_frontera_exacta() -> None:
    nuevo_pagado, estado = aplicar_pago(Decimal("100.00"), Decimal("40.00"), Decimal("60.00"))
    assert nuevo_pagado == Decimal("100.00")
    assert estado == ESTADO_PAGADO


def test_aplicar_pago_con_excedente() -> None:
    nuevo_pagado, estado = aplicar_pago(Decimal("100.00"), Decimal("0.00"), Decimal("150.00"))
    assert nuevo_pagado == Decimal("150.00")
    assert estado == ESTADO_PAGADO


def test_aplicar_pago_cero_queda_pendiente() -> None:
    nuevo_pagado, estado = aplicar_pago(Decimal("100.00"), Decimal("0.00"), Decimal("0.00"))
    assert nuevo_pagado == CERO
    assert estado == ESTADO_PENDIENTE


def test_calcular_deuda_total_suma_saldos() -> None:
    montos = [
        (Decimal("100.00"), Decimal("0.00")),
        (Decimal("50.00"), Decimal("50.00")),
        (Decimal("200.00"), Decimal("100.00")),
    ]
    assert calcular_deuda_total(montos) == Decimal("200.00")


def test_calcular_deuda_total_lista_vacia() -> None:
    assert calcular_deuda_total([]) == CERO


def test_calcular_excedente_pago() -> None:
    assert calcular_excedente_pago(Decimal("100.00"), Decimal("0.00"), Decimal("40.00")) == CERO
    assert calcular_excedente_pago(Decimal("100.00"), Decimal("0.00"), Decimal("100.00")) == CERO
    assert calcular_excedente_pago(Decimal("100.00"), Decimal("20.00"), Decimal("95.50")) == Decimal("15.50")


def test_validar_suma_alicuotas() -> None:
    assert validar_suma_alicuotas([]) is False
    assert validar_suma_alicuotas([Decimal("-1.0000"), Decimal("101.0000")]) is False
    assert validar_suma_alicuotas([Decimal("101.0000")]) is False
    assert validar_suma_alicuotas([Decimal("33.3333"), Decimal("33.3333"), Decimal("33.3334")]) is True
    assert validar_suma_alicuotas([Decimal("33.3333"), Decimal("33.3333"), Decimal("33.3333")]) is True
    assert validar_suma_alicuotas([Decimal("50.0000"), Decimal("40.0000")]) is False


def test_prorratear_por_alicuotas_metodo_hamilton_exacto() -> None:
    unidades = [(1, Decimal("33.3333")), (2, Decimal("33.3333")), (3, Decimal("33.3333"))]
    res = prorratear_por_alicuotas(Decimal("100.00"), unidades)
    assert res[1] == Decimal("33.34")
    assert res[2] == Decimal("33.33")
    assert res[3] == Decimal("33.33")
    assert sum(res.values()) == Decimal("100.00")

    res_cero = prorratear_por_alicuotas(Decimal("0.00"), unidades)
    assert res_cero == {1: CERO, 2: CERO, 3: CERO}


def test_prorratear_por_alicuotas_errores() -> None:
    with pytest.raises(ErrorFinanciero, match="negativo"):
        prorratear_por_alicuotas(Decimal("-10.00"), [(1, Decimal("100.0000"))])
    with pytest.raises(ErrorFinanciero, match="al menos una unidad"):
        prorratear_por_alicuotas(Decimal("10.00"), [])
    with pytest.raises(ErrorFinanciero, match="negativas"):
        prorratear_por_alicuotas(Decimal("10.00"), [(1, Decimal("-5.0000")), (2, Decimal("10.0000"))])
    with pytest.raises(ErrorFinanciero, match="mayor que cero"):
        prorratear_por_alicuotas(Decimal("10.00"), [(1, Decimal("0.0000"))])


def test_prorratear_partes_iguales() -> None:
    res = prorratear_partes_iguales(Decimal("100.00"), [10, 20, 30])
    assert res == {10: Decimal("33.34"), 20: Decimal("33.33"), 30: Decimal("33.33")}
    with pytest.raises(ErrorFinanciero, match="al menos una unidad"):
        prorratear_partes_iguales(Decimal("50.00"), [])


def test_aplicar_credito_disponible() -> None:
    assert aplicar_credito_disponible(Decimal("50.00"), Decimal("15.00")) == (
        Decimal("35.00"),
        Decimal("15.00"),
        CERO,
    )
    assert aplicar_credito_disponible(Decimal("40.00"), Decimal("65.00")) == (
        CERO,
        Decimal("40.00"),
        Decimal("25.00"),
    )
    with pytest.raises(ErrorFinanciero, match="negativos"):
        aplicar_credito_disponible(Decimal("-1.00"), Decimal("10.00"))


def test_firmar_y_verificar_solvencia_hmac() -> None:
    firma = generar_firma_solvencia("SOLV-202610-0001", "A-01", "2026-10-31", "secreto-11x")
    assert len(firma) == 64
    assert verificar_firma_solvencia("SOLV-202610-0001", "A-01", "2026-10-31", firma, "secreto-11x") is True
    assert verificar_firma_solvencia("SOLV-202610-0001", "A-02", "2026-10-31", firma, "secreto-11x") is False
    assert verificar_firma_solvencia("SOLV-202610-0001", "A-01", "2026-10-31", "   ", "secreto-11x") is False
    qr = construir_qr_token_solvencia("SOLV-202610-0001", "A-01", "2026-10-31", firma)
    assert qr.endswith(f".{firma}")
