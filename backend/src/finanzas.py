"""Núcleo matemático de finanzas (moneda base USD).

Funciones puras y deterministas para que la lógica crítica de "pago parcial vs
total" y la conversión por la tasa del día sea verificable con pruebas de
mutación súper estrictas (mutmut).
"""

import base64
import hashlib
import hmac
from collections.abc import Iterable, Sequence
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


def calcular_excedente_pago(
    monto_usd: Decimal,
    monto_pagado_usd: Decimal,
    pago_usd: Decimal,
) -> Decimal:
    """Calcula el excedente a favor (sobrepago) que debe acreditarse en Unidad.credito_disponible_usd."""
    saldo_pendiente = calcular_saldo_pendiente(monto_usd, monto_pagado_usd)
    pago = cuantizar(pago_usd)
    if pago > saldo_pendiente:
        return cuantizar(pago - saldo_pendiente)
    return CERO


def validar_suma_alicuotas(
    alicuotas: Sequence[Decimal],
    tolerancia: Decimal = Decimal("0.0100"),
) -> bool:
    """Verifica que las alícuotas sean positivas y sumen 100.0000% dentro de la tolerancia notarial."""
    if not alicuotas:
        return False
    suma = Decimal("0.0000")
    for valor in alicuotas:
        if valor < Decimal("0.0000") or valor > Decimal("100.0000"):
            return False
        suma += valor
    return abs(suma - Decimal("100.0000")) <= tolerancia


def _validar_entradas_prorrateo(
    monto_total_usd: Decimal,
    unidades_alicuotas: Sequence[tuple[int, Decimal]],
) -> tuple[Decimal, list[tuple[int, Decimal]], Decimal]:
    monto_total = cuantizar(monto_total_usd)
    if monto_total < CERO:
        raise ErrorFinanciero("El monto total a prorratear no puede ser negativo")
    if not unidades_alicuotas:
        raise ErrorFinanciero("Se requiere al menos una unidad para prorratear")

    ordenadas = sorted(unidades_alicuotas, key=lambda item: item[0])
    suma_pesos = Decimal("0")
    for _, peso in ordenadas:
        if peso < Decimal("0"):
            raise ErrorFinanciero("Las alícuotas no pueden ser negativas")
        suma_pesos += peso

    if suma_pesos <= Decimal("0"):
        raise ErrorFinanciero("La suma de alícuotas debe ser mayor que cero")
    return monto_total, ordenadas, suma_pesos


def prorratear_por_alicuotas(
    monto_total_usd: Decimal,
    unidades_alicuotas: Sequence[tuple[int, Decimal]],
) -> dict[int, Decimal]:
    """Prorratea un monto exacto en USD usando el Método del Resto Mayor (Hamilton / Penny Allocation).

    Garantiza el invariante matemático: sum(resultado.values()) == cuantizar(monto_total_usd).
    """
    monto_total, ordenadas, suma_pesos = _validar_entradas_prorrateo(monto_total_usd, unidades_alicuotas)
    if monto_total == CERO:
        return {uid: CERO for uid, _ in ordenadas}

    total_centavos = int((monto_total * 100).to_integral_value())
    pisos_por_unidad: dict[int, int] = {}
    residuos: list[tuple[Decimal, int]] = []

    for unidad_id, peso in ordenadas:
        cuota_exacta_centavos = (Decimal(total_centavos) * peso) / suma_pesos
        piso_centavos = int(cuota_exacta_centavos // Decimal(1))
        residuo = cuota_exacta_centavos - Decimal(piso_centavos)
        pisos_por_unidad[unidad_id] = piso_centavos
        residuos.append((residuo, unidad_id))

    centavos_restantes = total_centavos - sum(pisos_por_unidad.values())
    residuos.sort(key=lambda item: (-item[0], item[1]))
    for idx in range(centavos_restantes):
        uid_ganadora = residuos[idx][1]
        pisos_por_unidad[uid_ganadora] += 1

    return {uid: cuantizar(Decimal(pisos_por_unidad[uid]) / Decimal(100)) for uid, _ in ordenadas}


def prorratear_partes_iguales(
    monto_total_usd: Decimal,
    unidad_ids: Sequence[int],
) -> dict[int, Decimal]:
    """Divide un monto variable en partes iguales exactas distribuyendo centavos residuales por Hamilton."""
    if not unidad_ids:
        raise ErrorFinanciero("Se requiere al menos una unidad para prorratear en partes iguales")
    pesos_iguales = [(uid, Decimal("1.0000")) for uid in unidad_ids]
    return prorratear_por_alicuotas(monto_total_usd, pesos_iguales)


def aplicar_credito_disponible(
    cargo_bruto_usd: Decimal,
    credito_disponible_usd: Decimal,
) -> tuple[Decimal, Decimal, Decimal]:
    """Descuenta el saldo a favor del propietario contra el cargo bruto del recibo.

    Retorna (monto_neto_recibo_usd, credito_aplicado_usd, credito_restante_usd).
    """
    cargo = cuantizar(cargo_bruto_usd)
    credito = cuantizar(credito_disponible_usd)
    if cargo < CERO or credito < CERO:
        raise ErrorFinanciero("Los montos de cargo y crédito no pueden ser negativos")
    credito_aplicado = min(cargo, credito)
    monto_neto = cuantizar(cargo - credito_aplicado)
    credito_restante = cuantizar(credito - credito_aplicado)
    return monto_neto, credito_aplicado, credito_restante


def _construir_payload_solvencia(folio: str, identificador_unidad: str, fecha_vencimiento_iso: str) -> str:
    return f"SOLV|v1|{folio.strip()}|{identificador_unidad.strip()}|{fecha_vencimiento_iso.strip()}|0.00"


def generar_firma_solvencia(
    folio: str,
    identificador_unidad: str,
    fecha_vencimiento_iso: str,
    secret_key: str,
) -> str:
    """Genera la firma HMAC-SHA256 canónica para un Certificado de Solvencia (Art. 14 LPH)."""
    payload = _construir_payload_solvencia(folio, identificador_unidad, fecha_vencimiento_iso)
    return hmac.new(
        secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verificar_firma_solvencia(
    folio: str,
    identificador_unidad: str,
    fecha_vencimiento_iso: str,
    firma_recibida: str,
    secret_key: str,
) -> bool:
    """Verifica en tiempo constante la autenticidad criptográfica de un Certificado de Solvencia."""
    if not firma_recibida or not firma_recibida.strip():
        return False
    esperada = generar_firma_solvencia(folio, identificador_unidad, fecha_vencimiento_iso, secret_key)
    return hmac.compare_digest(firma_recibida.strip(), esperada)


def construir_qr_token_solvencia(
    folio: str,
    identificador_unidad: str,
    fecha_vencimiento_iso: str,
    firma_hmac: str,
) -> str:
    """Construye el token compacto base64url(payload).firma_hmac para el código QR del certificado."""
    payload = _construir_payload_solvencia(folio, identificador_unidad, fecha_vencimiento_iso)
    b64_payload = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii").rstrip("=")
    return f"{b64_payload}.{firma_hmac}"
