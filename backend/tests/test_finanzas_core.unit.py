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
    FRACCION_DOS_TERCIOS,
    UMBRAL_DOS_TERCIOS_PCT,
    ErrorFinanciero,
    aplicar_credito_disponible,
    aplicar_pago,
    calcular_deuda_total,
    calcular_excedente_pago,
    calcular_ip_hash_voto,
    calcular_saldo_pendiente,
    construir_claims_pase_qr,
    construir_mensaje_voto_consulta,
    construir_qr_token_solvencia,
    construir_token_pase_qr,
    convertir_a_usd,
    cuantizar,
    decodificar_y_verificar_token_pase_qr,
    determinar_estado_recibo,
    evaluar_escrutinio_consulta,
    generar_firma_pase_qr,
    generar_firma_solvencia,
    generar_firma_voto_consulta,
    prorratear_partes_iguales,
    prorratear_por_alicuotas,
    requiere_referencia,
    umbral_quorum_por_regla,
    validar_referencia,
    validar_suma_alicuotas,
    verificar_firma_solvencia,
    verificar_firma_voto_consulta,
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
    assert convertir_a_usd(Decimal("10.00"), "USD", Decimal(0)) == Decimal("10.00")


def test_convertir_ves_a_usd() -> None:
    assert convertir_a_usd(Decimal("3650.00"), "VES", Decimal("36.5000")) == Decimal("100.00")


def test_convertir_ves_redondea_a_centavos() -> None:
    assert convertir_a_usd(Decimal("100.00"), "VES", Decimal("36.5000")) == Decimal("2.74")


def test_convertir_moneda_no_soportada_falla() -> None:
    with pytest.raises(ErrorFinanciero, match="Moneda no soportada"):
        convertir_a_usd(Decimal("10.00"), "EUR", Decimal("36.5000"))


def test_convertir_ves_con_tasa_cero_falla() -> None:
    with pytest.raises(ErrorFinanciero, match="mayor que cero"):
        convertir_a_usd(Decimal("10.00"), "VES", Decimal(0))


def test_convertir_ves_con_tasa_negativa_falla() -> None:
    with pytest.raises(ErrorFinanciero, match="mayor que cero"):
        convertir_a_usd(Decimal("10.00"), "VES", Decimal(-5))


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

    # Solvencia v2 con JTI explícito vs JTI vacío/espacios
    import base64 as _b64

    firma_v2 = generar_firma_solvencia("SOLV-202610-0001", "A-01", "2026-10-31", "secreto-11x", jti="jti-v2")
    assert firma_v2 != firma
    assert generar_firma_solvencia("SOLV-202610-0001", "A-01", "2026-10-31", "secreto-11x", jti="   ") == firma
    assert verificar_firma_solvencia("SOLV-202610-0001", "A-01", "2026-10-31", firma_v2, "secreto-11x", jti="jti-v2")
    assert not verificar_firma_solvencia("SOLV-202610-0001", "A-01", "2026-10-31", firma_v2, "secreto-11x", jti="otro")
    assert not verificar_firma_solvencia("SOLV-202610-0001", "A-01", "2026-10-31", firma_v2, "secreto-11x", jti=None)
    qr_v2 = construir_qr_token_solvencia("SOLV-202610-0001", "A-01", "2026-10-31", firma_v2, jti="jti-v2")
    payload_b64, sig_qr = qr_v2.split(".", 1)
    assert sig_qr == firma_v2
    padded = payload_b64 + "=" * (-len(payload_b64) % 4)
    decoded_qr = _b64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
    assert decoded_qr == "SOLV|v2|jti-v2|SOLV-202610-0001|A-01|2026-10-31|0.00"
    assert "=" not in qr_v2


def test_fronteras_matematicas_finanzas_estrictas() -> None:
    """Ataque de fronteras exactas para conversión, referencias, prorrateos, crédito y tolerancias."""
    assert CERO == Decimal("0.00")
    assert ESTADO_PENDIENTE == "PENDIENTE"
    assert ESTADO_PARCIAL == "PAGADO_PARCIAL"
    assert ESTADO_PAGADO == "PAGADO"

    # USD ignora tasa <= 0 pero cuantiza; VES falla con tasa <= 0
    assert convertir_a_usd(Decimal("25.555"), "USD", Decimal("0")) == Decimal("25.56")
    with pytest.raises(ErrorFinanciero, match="mayor que cero"):
        convertir_a_usd(Decimal("100.00"), "VES", Decimal("0"))
    with pytest.raises(ErrorFinanciero, match="mayor que cero"):
        convertir_a_usd(Decimal("100.00"), "ves", Decimal("-36.50"))
    assert convertir_a_usd(Decimal("365.00"), "ves", Decimal("36.50")) == Decimal("10.00")

    # Referencias
    assert requiere_referencia("efectivo") is False
    assert requiere_referencia("pago_movil") is True
    validar_referencia("EFECTIVO", "  ref  ")
    validar_referencia("EFECTIVO", None)
    validar_referencia("pago_movil", "  987654  ")
    with pytest.raises(ErrorFinanciero, match="referencia es obligatorio"):
        validar_referencia("TRANSFERENCIA", "   ")

    # Saldos y estados exactos
    assert calcular_saldo_pendiente(Decimal("50.00"), Decimal("50.00")) == Decimal("0.00")
    assert determinar_estado_recibo(Decimal("50.00"), Decimal("0.00")) == ESTADO_PENDIENTE
    assert determinar_estado_recibo(Decimal("50.00"), Decimal("0.01")) == ESTADO_PARCIAL
    assert determinar_estado_recibo(Decimal("50.00"), Decimal("50.00")) == ESTADO_PAGADO
    assert determinar_estado_recibo(Decimal("0.00"), Decimal("0.00")) == ESTADO_PAGADO

    assert aplicar_pago(Decimal("100.00"), Decimal("0.00"), Decimal("100.00")) == (
        Decimal("100.00"),
        ESTADO_PAGADO,
    )
    assert aplicar_pago(Decimal("100.00"), Decimal("0.00"), Decimal("99.99")) == (
        Decimal("99.99"),
        ESTADO_PARCIAL,
    )
    assert aplicar_pago(Decimal("100.00"), Decimal("50.00"), Decimal("50.00")) == (
        Decimal("100.00"),
        ESTADO_PAGADO,
    )

    # Tolerancia exacta de alícuotas (0.0100) y desempate de residuos
    assert validar_suma_alicuotas([Decimal("99.9900")]) is True
    assert validar_suma_alicuotas([Decimal("100.0100")]) is False
    assert validar_suma_alicuotas([Decimal("50.0050"), Decimal("50.0050")]) is True
    assert validar_suma_alicuotas([Decimal("50.0051"), Decimal("50.0050")]) is False
    assert validar_suma_alicuotas([Decimal("99.9899")]) is False
    assert validar_suma_alicuotas([Decimal("100.0101")]) is False
    assert validar_suma_alicuotas([Decimal("-10.0000"), Decimal("110.0000")]) is False
    assert validar_suma_alicuotas([Decimal("0.0000")]) is False

    empatado = prorratear_por_alicuotas(
        Decimal("10.01"),
        [(10, Decimal("50.0000")), (20, Decimal("50.0000"))],
    )
    assert empatado == {10: Decimal("5.01"), 20: Decimal("5.00")}
    assert sum(empatado.values()) == Decimal("10.01")
    assert prorratear_por_alicuotas(Decimal("0.00"), [(1, Decimal("100.0000"))]) == {1: Decimal("0.00")}
    with pytest.raises(ErrorFinanciero, match="negativo"):
        prorratear_por_alicuotas(Decimal("-0.01"), [(1, Decimal("100.0000"))])
    with pytest.raises(ErrorFinanciero, match="al menos una unidad"):
        prorratear_por_alicuotas(Decimal("10.00"), [])

    iguales = prorratear_partes_iguales(Decimal("10.01"), [1, 2, 3])
    assert iguales == {1: Decimal("3.34"), 2: Decimal("3.34"), 3: Decimal("3.33")}
    assert sum(iguales.values()) == Decimal("10.01")
    with pytest.raises(ErrorFinanciero, match="negativo"):
        prorratear_partes_iguales(Decimal("-1.00"), [1])
    with pytest.raises(ErrorFinanciero, match="al menos una unidad"):
        prorratear_partes_iguales(Decimal("10.00"), [])

    assert aplicar_credito_disponible(Decimal("50.00"), Decimal("0.00")) == (
        Decimal("50.00"),
        Decimal("0.00"),
        Decimal("0.00"),
    )
    assert aplicar_credito_disponible(Decimal("50.00"), Decimal("75.00")) == (
        Decimal("0.00"),
        Decimal("50.00"),
        Decimal("25.00"),
    )
    with pytest.raises(ErrorFinanciero, match="negativos"):
        aplicar_credito_disponible(Decimal("-1.00"), Decimal("10.00"))
    with pytest.raises(ErrorFinanciero, match="negativos"):
        aplicar_credito_disponible(Decimal("10.00"), Decimal("-1.00"))
    assert calcular_deuda_total([(Decimal("10.00"), Decimal("0.00")), (Decimal("20.56"), Decimal("0.00"))]) == Decimal(
        "30.56"
    )
    assert calcular_excedente_pago(Decimal("10.00"), Decimal("0.00"), Decimal("10.00")) == Decimal("0.00")


def test_consultas_lph_quorum_voto_hmac_y_escrutinio() -> None:
    """Pruebas unitarias directas de quórum LPH, HMAC de votos e IP hash (finanzas L266-386)."""
    assert Decimal("0.6666") < FRACCION_DOS_TERCIOS < Decimal("0.6667")
    assert UMBRAL_DOS_TERCIOS_PCT == Decimal("66.6667")

    assert umbral_quorum_por_regla("DOS_TERCIOS") == UMBRAL_DOS_TERCIOS_PCT
    assert umbral_quorum_por_regla("MAYORIA_SIMPLE") == Decimal("50.0100")
    assert umbral_quorum_por_regla("UNANIMIDAD") == Decimal("100.0000")
    with pytest.raises(ErrorFinanciero, match="Regla de quórum inválida"):
        umbral_quorum_por_regla("dos_tercios")
    with pytest.raises(ErrorFinanciero, match="Regla de quórum inválida"):
        umbral_quorum_por_regla("OTRA_REGLA")

    msg_v1 = construir_mensaje_voto_consulta(7, 12, 3, Decimal("12.3456"), "2026-11-14T10:00:00Z")
    msg_v1_blank = construir_mensaje_voto_consulta(7, 12, 3, Decimal("12.3456"), "2026-11-14T10:00:00Z", jti="  ")
    msg_v2 = construir_mensaje_voto_consulta(7, 12, 3, Decimal("12.3456"), "2026-11-14T10:00:00Z", jti="voto-jti-1")
    assert msg_v1 == "VOTO|v1|7|12|3|12.3456|2026-11-14T10:00:00Z"
    assert msg_v1 == msg_v1_blank
    assert msg_v2 == "VOTO|v2|voto-jti-1|7|12|3|12.3456|2026-11-14T10:00:00Z"

    sig_v1 = generar_firma_voto_consulta(7, 12, 3, Decimal("12.3456"), "2026-11-14T10:00:00Z", "sec-voto")
    sig_v2 = generar_firma_voto_consulta(
        7, 12, 3, Decimal("12.3456"), "2026-11-14T10:00:00Z", "sec-voto", jti="voto-jti-1"
    )
    assert len(sig_v1) == 64
    assert sig_v1 != sig_v2
    assert verificar_firma_voto_consulta(7, 12, 3, Decimal("12.3456"), "2026-11-14T10:00:00Z", sig_v1, "sec-voto")
    assert verificar_firma_voto_consulta(
        7, 12, 3, Decimal("12.3456"), "2026-11-14T10:00:00Z", sig_v2, "sec-voto", jti="voto-jti-1"
    )
    assert not verificar_firma_voto_consulta(
        7, 12, 4, Decimal("12.3456"), "2026-11-14T10:00:00Z", sig_v2, "sec-voto", jti="voto-jti-1"
    )
    assert not verificar_firma_voto_consulta(
        7, 12, 3, Decimal("12.3456"), "2026-11-14T10:00:00Z", "   ", "sec-voto", jti="voto-jti-1"
    )
    assert not verificar_firma_voto_consulta(
        7, 12, 3, Decimal("12.3456"), "2026-11-14T10:00:00Z", sig_v2, "otro-sec", jti="voto-jti-1"
    )

    ip1 = calcular_ip_hash_voto(" 192.168.1.50 ", 7, "sec-voto")
    ip2 = calcular_ip_hash_voto("192.168.1.50", 7, "sec-voto")
    ip_otra_consulta = calcular_ip_hash_voto("192.168.1.50", 8, "sec-voto")
    ip_vacia = calcular_ip_hash_voto("   ", 7, "sec-voto")
    ip_none_empty = calcular_ip_hash_voto("", 7, "sec-voto")
    assert len(ip1) == 64
    assert ip1 == ip2
    assert ip1 != ip_otra_consulta
    assert ip_vacia != ip_none_empty
    assert ip1 != ip_vacia
    assert ip1 != ip_none_empty

    # Escrutinio: sin quórum, frontera DOS_TERCIOS (2/3), aprobada y rechazada
    estado_sq, pct_part, pct_ap = evaluar_escrutinio_consulta(
        Decimal("50.0000"),
        {1},
        {1: Decimal("30.0000"), 2: Decimal("19.9999")},
    )
    assert estado_sq == "CERRADA_SIN_QUORUM"
    assert pct_part == Decimal("49.9999")
    assert pct_ap == Decimal("30.0000")

    estado_ap, pct_part2, pct_ap2 = evaluar_escrutinio_consulta(
        Decimal("50.0000"),
        {1},
        {1: Decimal("50.0000"), 2: Decimal("20.0000")},
    )
    assert estado_ap == "CERRADA_APROBADA"
    assert pct_part2 == Decimal("70.0000")
    assert pct_ap2 == Decimal("50.0000")

    # Con quórum alcanzado pero alícuota aprobatoria inferior al umbral -> CERRADA_RECHAZADA
    estado_rech, pct_part3, pct_ap3 = evaluar_escrutinio_consulta(
        Decimal("50.0000"),
        {1},
        {1: Decimal("49.9999"), 2: Decimal("25.0000")},
    )
    assert estado_rech == "CERRADA_RECHAZADA"
    assert pct_part3 == Decimal("74.9999")
    assert pct_ap3 == Decimal("49.9999")

    # Regla DOS_TERCIOS: <2/3 sin quórum, >=2/3 part pero <2/3 aprob rechazada, y 66.6667 aprobada
    est_23_sq, _, _ = evaluar_escrutinio_consulta(
        Decimal("66.6667"),
        {1},
        {1: Decimal("66.6600")},
        regla_quorum="DOS_TERCIOS",
    )
    assert est_23_sq == "CERRADA_SIN_QUORUM"

    est_23_rech, _, _ = evaluar_escrutinio_consulta(
        Decimal("66.6667"),
        {1},
        {1: Decimal("66.6600"), 2: Decimal("10.0000")},
        regla_quorum="DOS_TERCIOS",
    )
    assert est_23_rech == "CERRADA_RECHAZADA"

    est_23_ok, _, _ = evaluar_escrutinio_consulta(
        Decimal("66.6667"),
        {1},
        {1: Decimal("66.6667")},
        regla_quorum="DOS_TERCIOS",
    )
    assert est_23_ok == "CERRADA_APROBADA"


def test_pases_qr_hmac_roundtrip_y_errores_decodificacion() -> None:
    """Valida firma, empaquetado base64url y todas las ramas de error en decodificación QR."""
    import base64
    import hashlib
    import hmac

    claims = construir_claims_pase_qr("jti-pase-1", 42, "VISITA", 1893456000)
    assert claims == "QR|v1|jti-pase-1|42|VISITA|1893456000"
    parts = claims.split("|")

    sig = generar_firma_pase_qr("jti-pase-1", 42, "VISITA", 1893456000, "sec-qr")
    assert len(sig) == 64
    tok = construir_token_pase_qr("jti-pase-1", 42, "VISITA", 1893456000, sig)
    assert "=" not in tok

    dec_jti, dec_uid, dec_mod, dec_exp, dec_sig = decodificar_y_verificar_token_pase_qr(tok, "sec-qr")
    assert (dec_jti, dec_uid, dec_mod, dec_exp, dec_sig) == ("jti-pase-1", 42, "VISITA", 1893456000, sig)

    def _forjar(bad_claims: str, secret: str = "sec-qr") -> str:
        b64 = base64.urlsafe_b64encode(bad_claims.encode("utf-8")).decode("ascii").rstrip("=")
        bad_sig = hmac.new(secret.encode("utf-8"), bad_claims.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{b64}.{bad_sig}"

    def _reemplazar(idx: int, valor: str) -> str:
        copia = list(parts)
        copia[idx] = valor
        return _forjar("|".join(copia))

    idx_jti = parts.index("jti-pase-1")
    idx_uid = parts.index("42")
    idx_exp = parts.index("1893456000")

    casos_invalidos = [
        "sin_punto",
        ".abcdef",
        "abcdef.",
        "!!!no_b64." + sig,
        _forjar("A|B|C"),
        _reemplazar(0, "BAD"),
        _reemplazar(idx_jti, "   "),
        _reemplazar(idx_uid, "no-int"),
        _reemplazar(idx_exp, "no-exp"),
        f"{tok[:-1]}{'0' if tok[-1] != '0' else '1'}",
    ]
    if idx_jti > 1:
        casos_invalidos.append(_reemplazar(1, "v99"))

    for token_invalido in casos_invalidos:
        with pytest.raises(ErrorFinanciero, match="Firma criptográfica"):
            decodificar_y_verificar_token_pase_qr(token_invalido, "sec-qr")

    with pytest.raises(ErrorFinanciero, match="Firma criptográfica"):
        decodificar_y_verificar_token_pase_qr(tok, "secreto-incorrecto")
