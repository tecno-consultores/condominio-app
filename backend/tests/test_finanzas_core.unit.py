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
    aplicar_pago,
    calcular_deuda_total,
    calcular_saldo_pendiente,
    convertir_a_usd,
    cuantizar,
    determinar_estado_recibo,
    requiere_referencia,
    validar_referencia,
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
