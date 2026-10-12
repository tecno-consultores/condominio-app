"""Núcleo matemático de finanzas (moneda base USD).

Funciones puras y deterministas para que la lógica crítica de "pago parcial vs
total" y la conversión por la tasa del día sea verificable con pruebas de
mutación súper estrictas (mutmut).
"""

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal

CENTAVO = Decimal("0.01")

MONEDAS_VALIDAS = frozenset({"USD", "VES"})
METODOS_CON_REFERENCIA = frozenset({"ZELLE", "PAGO_MOVIL", "TRANSFERENCIA"})

ESTADO_PENDIENTE = "PENDIENTE"
ESTADO_PARCIAL = "PAGADO_PARCIAL"
ESTADO_PAGADO = "PAGADO"

CERO = Decimal("0.00")


class ErrorFinanciero(ValueError):
    """Error de dominio financiero (entrada inválida o regla de negocio violada)."""


def cuantizar(valor: Decimal) -> Decimal:
    """Redondea un monto a dos decimales (centavos) con redondeo bancario HALF_UP."""
    return valor.quantize(CENTAVO, rounding=ROUND_HALF_UP)


def convertir_a_usd(monto: Decimal, moneda: str, tasa_cambio: Decimal) -> Decimal:
    """Convierte un monto en la moneda indicada a USD usando la tasa del día."""
    moneda_normalizada = moneda.upper()
    if moneda_normalizada not in MONEDAS_VALIDAS:
        raise ErrorFinanciero(f"Moneda no soportada: {moneda}")
    if moneda_normalizada == "USD":
        return cuantizar(monto)
    if tasa_cambio <= 0:
        raise ErrorFinanciero("La tasa de cambio debe ser mayor que cero")
    return cuantizar(monto / tasa_cambio)


def requiere_referencia(metodo_pago: str) -> bool:
    """Indica si el método de pago exige número de referencia obligatorio."""
    return metodo_pago.upper() in METODOS_CON_REFERENCIA


def validar_referencia(metodo_pago: str, numero_referencia: str | None) -> None:
    """Lanza ErrorFinanciero si el método exige referencia y no fue suministrada."""
    if requiere_referencia(metodo_pago) and not (numero_referencia and numero_referencia.strip()):
        raise ErrorFinanciero("El número de referencia es obligatorio para este método de pago")


def calcular_saldo_pendiente(monto_usd: Decimal, monto_pagado_usd: Decimal) -> Decimal:
    """Saldo pendiente en USD. Nunca negativo (los excedentes no generan crédito)."""
    saldo = cuantizar(monto_usd) - cuantizar(monto_pagado_usd)
    if saldo < CERO:
        return CERO
    return saldo


def determinar_estado_recibo(monto_usd: Decimal, monto_pagado_usd: Decimal) -> str:
    """Determina el estado del recibo a partir del monto total y lo pagado."""
    monto = cuantizar(monto_usd)
    pagado = cuantizar(monto_pagado_usd)
    if pagado >= monto:
        return ESTADO_PAGADO
    if pagado > CERO:
        return ESTADO_PARCIAL
    return ESTADO_PENDIENTE


def aplicar_pago(
    monto_usd: Decimal,
    monto_pagado_usd: Decimal,
    pago_usd: Decimal,
) -> tuple[Decimal, str]:
    """Aplica un pago aprobado y devuelve (nuevo_monto_pagado_usd, nuevo_estado)."""
    nuevo_pagado = cuantizar(monto_pagado_usd) + cuantizar(pago_usd)
    estado = determinar_estado_recibo(monto_usd, nuevo_pagado)
    return nuevo_pagado, estado


def calcular_deuda_total(montos: Iterable[tuple[Decimal, Decimal]]) -> Decimal:
    """Suma los saldos pendientes de una colección de (monto_usd, pagado_usd)."""
    total = CERO
    for monto_usd, monto_pagado_usd in montos:
        total += calcular_saldo_pendiente(monto_usd, monto_pagado_usd)
    return cuantizar(total)
