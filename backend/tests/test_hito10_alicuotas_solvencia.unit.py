"""Pruebas unitarias Nivel 11X para el Hito 10: Alícuotas, Cuota Fija, Facturación LPH, Fondos y Solvencia Digital."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from src.database import get_db
from src.dependencies import get_current_user
from src.facturacion_lph import (
    _anexar_cuota_extraordinaria,
    _cargos_cuota_fija,
    _cargos_variables,
    _crear_recibo_e_items_unidad,
    calcular_cargos_modalidad,
    cargar_contexto_facturacion,
    persistir_lote_facturacion,
)
from src.finanzas import ErrorFinanciero, generar_firma_solvencia
from src.main import app
from src.models import (
    CertificadoSolvencia,
    ContratoOcupacion,
    Egreso,
    FondoCondominio,
    PagoReportado,
    Recibo,
    ReciboItem,
    ReporteMensual,
    TasaCambio,
    Unidad,
)
from src.redis_client import get_redis_client
from src.security import SECRET_KEY

HEADERS = {"Idempotency-Key": "018f4a12-1010-7000-8000-000000001010"}


class FakeUser:
    def __init__(self, user_id: int = 1, rol: str = "TESORERO", es_activo: bool = True) -> None:
        self.id = user_id
        self.correo = f"{rol.lower()}@condominio.test"
        self.rol = rol
        self.es_activo = es_activo


def _result(value: Any) -> MagicMock:
    res = MagicMock()
    res.scalars().first.return_value = value
    return res


def _result_list(values: list[Any]) -> MagicMock:
    res = MagicMock()
    res.scalars().all.return_value = values
    return res


def _mock_session(*results: Any) -> AsyncMock:
    session = AsyncMock()
    session.execute.side_effect = list(results)
    session.add = MagicMock()

    async def _refresh(instance: Any, *args: object, **kwargs: object) -> None:
        if getattr(instance, "id", None) is None:
            instance.id = 10

    session.refresh = _refresh
    return session


def _setup(session: AsyncMock, user: FakeUser | None = None, redis_new: bool = True) -> AsyncMock:
    mock_redis = AsyncMock()
    mock_redis.set.return_value = redis_new
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_redis_client] = lambda: mock_redis
    app.dependency_overrides[get_current_user] = lambda: user or FakeUser()
    return mock_redis


# ==============================================================================
# 1. ANTI-FRAUDE DE REFERENCIAS BANCARIAS Y SOBREPAGOS EN PAGOS
# ==============================================================================


def test_reportar_pago_referencia_bancaria_duplicada_devuelve_409(client: TestClient) -> None:
    pago_existente = PagoReportado(
        id=9,
        recibo_id=1,
        usuario_id=2,
        monto=Decimal("50.00"),
        moneda="USD",
        monto_usd=Decimal("50.00"),
        tasa_cambio=Decimal("36.5000"),
        metodo_pago="ZELLE",
        numero_referencia="REF-DUP-001",
        estado="APROBADO",
    )
    session = _mock_session(_result(pago_existente))
    _setup(session, user=FakeUser(user_id=5, rol="PROPIETARIO"))

    res = client.post(
        "/api/pagos/reportar",
        json={
            "recibo_id": 1,
            "monto": "50.00",
            "moneda": "USD",
            "metodo_pago": "ZELLE",
            "numero_referencia": "REF-DUP-001",
        },
        headers=HEADERS,
    )
    assert res.status_code == 409
    assert "referencia bancaria ya fue registrado" in res.json()["detail"]
    # pyrefly: ignore[implicit-any-empty-container]
    app.dependency_overrides = {}


def test_reportar_pago_referencia_bancaria_unica_exito(client: TestClient) -> None:
    tasa = TasaCambio(id=1, fecha=date.today(), tasa_usd_ves=Decimal("36.5000"))
    recibo = Recibo(
        id=1,
        unidad_id=1,
        periodo="2026-10",
        monto_usd=Decimal("100.00"),
        monto_pagado_usd=Decimal("0.00"),
        estado="PENDIENTE",
        bloqueado=False,
    )
    contrato = ContratoOcupacion(id=1, usuario_id=5, unidad_id=1, tipo_ocupante="PROPIETARIO", es_activo=True)
    session = _mock_session(_result(None), _result(tasa), _result(recibo), _result(contrato))
    _setup(session, user=FakeUser(user_id=5, rol="PROPIETARIO"))

    res = client.post(
        "/api/pagos/reportar",
        json={
            "recibo_id": 1,
            "monto": "100.00",
            "moneda": "USD",
            "metodo_pago": "PAGO_MOVIL",
            "numero_referencia": "REF-UNICA-999",
        },
        headers=HEADERS,
    )
    assert res.status_code == 201
    app.dependency_overrides = {}


def test_aprobar_pago_con_sobrepago_acredita_saldo_a_favor_unidad(client: TestClient) -> None:
    pago = PagoReportado(
        id=12,
        recibo_id=1,
        usuario_id=5,
        monto=Decimal("125.00"),
        moneda="USD",
        monto_usd=Decimal("125.00"),
        tasa_cambio=Decimal("36.5000"),
        metodo_pago="ZELLE",
        numero_referencia="REF-OVER-1",
        estado="EN_REVISION",
    )
    recibo = Recibo(
        id=1,
        unidad_id=3,
        periodo="2026-10",
        monto_usd=Decimal("100.00"),
        monto_pagado_usd=Decimal("0.00"),
        estado="PENDIENTE",
        bloqueado=False,
    )
    unidad = Unidad(
        id=3,
        identificador="A-03",
        estructura_id=1,
        alicuota=Decimal("25.0000"),
        credito_disponible_usd=Decimal("10.00"),
    )
    session = _mock_session(_result(pago), _result(recibo), _result(unidad))
    _setup(session)

    res = client.put("/api/pagos/12/aprobar", headers=HEADERS)
    assert res.status_code == 200
    assert recibo.estado == "PAGADO"
    assert recibo.monto_pagado_usd == Decimal("100.00")
    assert unidad.credito_disponible_usd == Decimal("35.00")
    audit = session.add.call_args[0][0]
    assert "Sobrepago acreditado" in audit.motivo
    app.dependency_overrides = {}


# ==============================================================================
# 2. ACTUALIZACIÓN DE ALÍCUOTA Y CUOTA FIJA EN UNIDAD
# ==============================================================================


def test_actualizar_alicuota_unidad_exito_y_errores(client: TestClient) -> None:
    unidad = Unidad(
        id=1,
        identificador="A-01",
        estructura_id=1,
        alicuota=Decimal("0.0000"),
        cuota_fija_usd=None,
        credito_disponible_usd=Decimal("0.00"),
    )
    session = _mock_session(_result(unidad))
    _setup(session)

    res = client.put(
        "/api/estructura/unidades/1/alicuota",
        json={"alicuota": "33.3333", "cuota_fija_usd": "25.00"},
        headers=HEADERS,
    )
    assert res.status_code == 200
    body = res.json()
    assert Decimal(body["alicuota"]) == Decimal("33.3333")
    assert Decimal(body["cuota_fija_usd"]) == Decimal("25.00")

    # 404 Unidad no encontrada
    session_404 = _mock_session(_result(None))
    _setup(session_404)
    res_404 = client.put(
        "/api/estructura/unidades/999/alicuota",
        json={"alicuota": "10.0000"},
        headers=HEADERS,
    )
    assert res_404.status_code == 404

    # 409 Idempotencia duplicada
    _setup(_mock_session(), redis_new=False)
    res_409 = client.put(
        "/api/estructura/unidades/1/alicuota",
        json={"alicuota": "10.0000"},
        headers=HEADERS,
    )
    assert res_409.status_code == 409
    app.dependency_overrides = {}


# ==============================================================================
# 3. FONDOS PATRIMONIALES DEL CONDOMINIO
# ==============================================================================


def test_crear_y_listar_fondos_condominio(client: TestClient) -> None:
    session = _mock_session(_result(None))
    _setup(session)

    res = client.post(
        "/api/finanzas/fondos",
        json={"nombre": "Fondo de Reserva Legal", "tipo": "RESERVA_LEGAL", "porcentaje_recargo": "10.00"},
        headers=HEADERS,
    )
    assert res.status_code == 201
    assert res.json()["nombre"] == "Fondo de Reserva Legal"

    # 409 Nombre duplicado
    fondo_exist = FondoCondominio(
        id=1,
        nombre="Fondo de Reserva Legal",
        tipo="RESERVA_LEGAL",
        porcentaje_recargo=Decimal("10.00"),
        saldo_actual_usd=Decimal("0.00"),
        es_activo=True,
    )
    session_dup = _mock_session(_result(fondo_exist))
    _setup(session_dup)
    res_dup = client.post(
        "/api/finanzas/fondos",
        json={"nombre": "Fondo de Reserva Legal"},
        headers=HEADERS,
    )
    assert res_dup.status_code == 409

    # 409 Idempotencia duplicada
    _setup(_mock_session(), redis_new=False)
    res_idemp = client.post(
        "/api/finanzas/fondos",
        json={"nombre": "Caja Chica", "tipo": "CAJA_CHICA"},
        headers=HEADERS,
    )
    assert res_idemp.status_code == 409

    # GET /api/finanzas/fondos
    session_list = _mock_session(_result_list([fondo_exist]))
    _setup(session_list, user=FakeUser(rol="PROPIETARIO"))
    res_list = client.get("/api/finanzas/fondos")
    assert res_list.status_code == 200
    assert len(res_list.json()) == 1
    app.dependency_overrides = {}


# ==============================================================================
# 4. FACTURACIÓN TRIMODAL (ALICUOTA, CUOTA_FIJA, PARTES_IGUALES) Y DESGLOSE
# ==============================================================================


def test_facturar_periodo_modalidad_alicuota_con_credito_y_fondo(client: TestClient) -> None:
    unidades = [
        Unidad(
            id=1,
            identificador="A-01",
            estructura_id=1,
            alicuota=Decimal("33.3333"),
            credito_disponible_usd=Decimal("50.00"),
        ),
        Unidad(
            id=2,
            identificador="A-02",
            estructura_id=1,
            alicuota=Decimal("33.3333"),
            credito_disponible_usd=Decimal("10.00"),
        ),
        Unidad(
            id=3,
            identificador="A-03",
            estructura_id=1,
            alicuota=Decimal("33.3334"),
            credito_disponible_usd=Decimal("0.00"),
        ),
    ]
    egresos = [
        Egreso(
            id=1,
            periodo="2026-10",
            categoria="MANTENIMIENTO",
            descripcion="Bomba de agua",
            monto=Decimal("100.00"),
            moneda="USD",
            monto_usd=Decimal("100.00"),
            tasa_cambio=Decimal("36.5000"),
            es_gasto_comun=True,
        )
    ]
    fondo = FondoCondominio(
        id=1,
        nombre="Fondo de Reserva Legal",
        tipo="RESERVA_LEGAL",
        porcentaje_recargo=Decimal("10.00"),
        saldo_actual_usd=Decimal("200.00"),
        es_activo=True,
    )
    session = _mock_session(
        _result(None),  # ReporteMensual
        _result(None),  # Recibo existente
        _result_list(unidades),
        _result_list(egresos),
        _result(fondo),
    )
    _setup(session)

    res = client.post(
        "/api/finanzas/facturar-periodo",
        json={
            "periodo": "2026-10",
            "modalidad": "ALICUOTA",
            "incluir_fondo_reserva": True,
            "cuota_extraordinaria_total_usd": "30.00",
            "descripcion_cuota_extraordinaria": "Pintura fachada",
        },
        headers=HEADERS,
    )
    assert res.status_code == 201
    body = res.json()
    assert body["recibos_emitidos"] == 3
    assert Decimal(body["total_egresos_comunes_usd"]) == Decimal("100.00")
    assert Decimal(body["recargo_fondo_reserva_usd"]) == Decimal("10.00")
    assert Decimal(body["cuota_extraordinaria_total_usd"]) == Decimal("30.00")
    assert Decimal(body["total_facturado_bruto_usd"]) == Decimal("140.00")
    assert fondo.saldo_actual_usd == Decimal("210.00")
    # Unidad 1 tenía $50 de crédito y su cargo bruto era ~$46.67 -> queda cubierta al 100%
    assert unidades[0].credito_disponible_usd > Decimal("0.00")
    assert unidades[1].credito_disponible_usd == Decimal("0.00")
    app.dependency_overrides = {}


def test_facturar_periodo_modalidad_cuota_fija_y_partes_iguales(client: TestClient) -> None:
    unidades = [
        Unidad(
            id=1,
            identificador="C-01",
            estructura_id=1,
            alicuota=Decimal("0.0000"),
            cuota_fija_usd=Decimal("35.00"),
            credito_disponible_usd=Decimal("0.00"),
        ),
        Unidad(
            id=2,
            identificador="C-02",
            estructura_id=1,
            alicuota=Decimal("0.0000"),
            cuota_fija_usd=None,
            credito_disponible_usd=Decimal("0.00"),
        ),
    ]
    egresos = [
        Egreso(
            id=1,
            periodo="2026-11",
            categoria="VIGILANCIA",
            descripcion="Servicio garita",
            monto=Decimal("40.00"),
            moneda="USD",
            monto_usd=Decimal("40.00"),
            tasa_cambio=Decimal("36.5000"),
            es_gasto_comun=True,
        )
    ]
    fondo = FondoCondominio(
        id=1,
        nombre="Fondo de Reserva Legal",
        tipo="RESERVA_LEGAL",
        porcentaje_recargo=Decimal("10.00"),
        saldo_actual_usd=Decimal("100.00"),
        es_activo=True,
    )
    session_fija = _mock_session(
        _result(None),
        _result(None),
        _result_list(unidades),
        _result_list(egresos),
        _result(fondo),
    )
    _setup(session_fija)

    res_fija = client.post(
        "/api/finanzas/facturar-periodo",
        json={
            "periodo": "2026-11",
            "modalidad": "CUOTA_FIJA",
            "monto_cuota_fija_usd": "25.00",
        },
        headers=HEADERS,
    )
    assert res_fija.status_code == 201
    body_fija = res_fija.json()
    # 35.00 + 25.00 = 60.00 facturado - 40.00 egresos = +20.00 superávit al fondo
    assert Decimal(body_fija["total_facturado_bruto_usd"]) == Decimal("60.00")
    assert Decimal(body_fija["superavit_conciliado_fondo_usd"]) == Decimal("20.00")
    assert fondo.saldo_actual_usd == Decimal("120.00")

    # Modalidad PARTES_IGUALES
    session_iguales = _mock_session(
        _result(None),
        _result(None),
        _result_list(unidades),
        _result_list(egresos),
        _result(None),
    )
    _setup(session_iguales)
    res_iguales = client.post(
        "/api/finanzas/facturar-periodo",
        json={
            "periodo": "2026-12",
            "modalidad": "PARTES_IGUALES",
            "incluir_fondo_reserva": False,
        },
        headers=HEADERS,
    )
    assert res_iguales.status_code == 201
    assert Decimal(res_iguales.json()["total_facturado_bruto_usd"]) == Decimal("40.00")
    app.dependency_overrides = {}


def test_facturar_periodo_errores_y_bloqueos(client: TestClient) -> None:
    # 1. Idempotencia duplicada
    _setup(_mock_session(), redis_new=False)
    assert (
        client.post(
            "/api/finanzas/facturar-periodo",
            json={"periodo": "2026-10"},
            headers=HEADERS,
        ).status_code
        == 409
    )

    # 2. Periodo cerrado por Candado Contable
    session_cerrado = _mock_session(_result(ReporteMensual(id=1, periodo="2026-10", estado="CERRADO")))
    _setup(session_cerrado)
    assert (
        client.post(
            "/api/finanzas/facturar-periodo",
            json={"periodo": "2026-10"},
            headers=HEADERS,
        ).status_code
        == 409
    )

    # 3. Periodo ya facturado
    session_ya = _mock_session(
        _result(None),
        _result(Recibo(id=1, unidad_id=1, periodo="2026-10", monto_usd=Decimal("10.00"))),
    )
    _setup(session_ya)
    assert (
        client.post(
            "/api/finanzas/facturar-periodo",
            json={"periodo": "2026-10"},
            headers=HEADERS,
        ).status_code
        == 409
    )

    # 4. Sin unidades registradas
    session_sin_uni = _mock_session(_result(None), _result(None), _result_list([]))
    _setup(session_sin_uni)
    assert (
        client.post(
            "/api/finanzas/facturar-periodo",
            json={"periodo": "2026-10"},
            headers=HEADERS,
        ).status_code
        == 400
    )

    # 5. CUOTA_FIJA sin monto_cuota_fija_usd y unidad sin cuota_fija_usd
    uni_sin_fija = [Unidad(id=1, identificador="A-01", estructura_id=1, alicuota=Decimal("0.0000"))]
    session_bad_fija = _mock_session(
        _result(None),
        _result(None),
        _result_list(uni_sin_fija),
        _result_list([]),
        _result(None),
    )
    _setup(session_bad_fija)
    assert (
        client.post(
            "/api/finanzas/facturar-periodo",
            json={"periodo": "2026-10", "modalidad": "CUOTA_FIJA"},
            headers=HEADERS,
        ).status_code
        == 400
    )

    # 6. Modalidad ALICUOTA con suma de alícuotas != 100.0000% -> 400
    uni_suma_invalida = [
        Unidad(
            id=1,
            identificador="A-01",
            estructura_id=1,
            alicuota=Decimal("50.0000"),
            credito_disponible_usd=Decimal("0.00"),
        ),
        Unidad(
            id=2,
            identificador="A-02",
            estructura_id=1,
            alicuota=Decimal("30.0000"),
            credito_disponible_usd=Decimal("0.00"),
        ),
    ]
    session_bad_alic = _mock_session(
        _result(None),
        _result(None),
        _result_list(uni_suma_invalida),
        _result_list([]),
        _result(None),
    )
    _setup(session_bad_alic)
    res_bad_alic = client.post(
        "/api/finanzas/facturar-periodo",
        json={"periodo": "2026-10", "modalidad": "ALICUOTA", "incluir_fondo_reserva": False},
        headers=HEADERS,
    )
    assert res_bad_alic.status_code == 400
    assert "100.0000%" in res_bad_alic.json()["detail"]

    # 7. Colisión concurrente IntegrityError sobre uq_recibo_unidad_periodo -> 409 Conflict
    uni_ok = [
        Unidad(
            id=1,
            identificador="A-01",
            estructura_id=1,
            alicuota=Decimal("100.0000"),
            credito_disponible_usd=Decimal("0.00"),
        )
    ]
    session_ie = _mock_session(
        _result(None),
        _result(None),
        _result_list(uni_ok),
        _result_list([]),
        _result(None),
    )
    session_ie.commit.side_effect = IntegrityError("dup", {}, Exception("uq_recibo_unidad_periodo"))
    _setup(session_ie)
    res_ie = client.post(
        "/api/finanzas/facturar-periodo",
        json={"periodo": "2026-10", "modalidad": "ALICUOTA", "incluir_fondo_reserva": False},
        headers=HEADERS,
    )
    assert res_ie.status_code == 409
    app.dependency_overrides = {}


def test_facturar_periodo_cuota_extraordinaria_prorrateada_por_alicuota(client: TestClient) -> None:
    unidades = [
        Unidad(
            id=1,
            identificador="A-01",
            estructura_id=1,
            alicuota=Decimal("50.0000"),
            credito_disponible_usd=Decimal("0.00"),
        ),
        Unidad(
            id=2,
            identificador="A-02",
            estructura_id=1,
            alicuota=Decimal("30.0000"),
            credito_disponible_usd=Decimal("0.00"),
        ),
        Unidad(
            id=3,
            identificador="A-03",
            estructura_id=1,
            alicuota=Decimal("20.0000"),
            credito_disponible_usd=Decimal("0.00"),
        ),
    ]
    session = _mock_session(
        _result(None),
        _result(None),
        _result_list(unidades),
        _result_list([]),
        _result(None),
    )
    _setup(session)

    res = client.post(
        "/api/finanzas/facturar-periodo",
        json={
            "periodo": "2027-01",
            "modalidad": "ALICUOTA",
            "incluir_fondo_reserva": False,
            "cuota_extraordinaria_total_usd": "100.00",
            "descripcion_cuota_extraordinaria": "Impermeabilización techo",
        },
        headers=HEADERS,
    )
    assert res.status_code == 201
    extra_items = [
        call.args[0]
        for call in session.add.call_args_list
        if isinstance(call.args[0], ReciboItem) and call.args[0].tipo_item == "CUOTA_EXTRAORDINARIA"
    ]
    montos_extra = sorted(item.monto_usd for item in extra_items)
    assert montos_extra == [Decimal("20.00"), Decimal("30.00"), Decimal("50.00")]
    app.dependency_overrides = {}


def test_obtener_desglose_recibo_exito_y_permisos(client: TestClient) -> None:
    recibo = Recibo(
        id=7,
        unidad_id=2,
        periodo="2026-10",
        monto_usd=Decimal("35.00"),
        monto_pagado_usd=Decimal("0.00"),
        estado="PENDIENTE",
        bloqueado=False,
    )
    unidad = Unidad(id=2, identificador="B-02", estructura_id=1, alicuota=Decimal("25.0000"))
    items = [
        ReciboItem(id=1, recibo_id=7, tipo_item="GASTO_COMUN", descripcion="Gasto común", monto_usd=Decimal("45.00")),
        ReciboItem(
            id=2,
            recibo_id=7,
            tipo_item="ABONO_CREDITO_PREVIO",
            descripcion="Abono previo",
            monto_usd=Decimal("-10.00"),
        ),
    ]
    session = _mock_session(_result(recibo), _result(unidad), _result_list(items))
    _setup(session)

    res = client.get("/api/finanzas/recibos/7/desglose")
    assert res.status_code == 200
    body = res.json()
    assert body["identificador_unidad"] == "B-02"
    assert Decimal(body["credito_descontado_usd"]) == Decimal("10.00")
    assert len(body["items"]) == 2

    # Propietario de otra unidad recibe 403
    session_403 = _mock_session(_result(recibo), _result(None))
    _setup(session_403, user=FakeUser(user_id=99, rol="PROPIETARIO"))
    assert client.get("/api/finanzas/recibos/7/desglose").status_code == 403

    # Recibo inexistente devuelve 404
    session_404 = _mock_session(_result(None))
    _setup(session_404)
    assert client.get("/api/finanzas/recibos/999/desglose").status_code == 404
    app.dependency_overrides = {}


# ==============================================================================
# 5. CERTIFICADO DIGITAL DE SOLVENCIA (HMAC-SHA256)
# ==============================================================================


def test_emitir_y_verificar_certificado_solvencia(client: TestClient) -> None:
    unidad = Unidad(id=4, identificador="PH-01", estructura_id=1, alicuota=Decimal("10.0000"))
    contrato = ContratoOcupacion(id=1, usuario_id=44, unidad_id=4, tipo_ocupante="PROPIETARIO", es_activo=True)
    session = _mock_session(_result(contrato), _result(unidad), _result(Decimal("0.00")))
    _setup(session, user=FakeUser(user_id=44, rol="PROPIETARIO"))

    res = client.post("/api/finanzas/solvencia/4", headers=HEADERS)
    assert res.status_code == 201
    cert_data = res.json()
    assert cert_data["identificador_unidad"] == "PH-01"
    assert Decimal(cert_data["deuda_verificada_usd"]) == Decimal("0.00")
    assert cert_data["qr_token"].endswith(cert_data["firma_hmac"])

    # Verificar el certificado emitido
    venc = date.fromisoformat(cert_data["fecha_vencimiento"])
    firma = generar_firma_solvencia(cert_data["folio"], "PH-01", venc.isoformat(), SECRET_KEY)
    cert_orm = CertificadoSolvencia(
        id=1,
        folio=cert_data["folio"],
        unidad_id=4,
        emitido_por_id=44,
        fecha_emision=datetime.now(UTC),
        fecha_vencimiento=venc,
        deuda_verificada_usd=Decimal("0.00"),
        firma_hmac=firma,
    )
    session_verif = _mock_session(_result(cert_orm), _result(unidad), _result(Decimal("0.00")))
    _setup(session_verif)
    res_verif = client.get(f"/api/finanzas/solvencia/verificar/{cert_data['folio']}?sig={firma}")
    assert res_verif.status_code == 200
    assert res_verif.json()["valido"] is True

    # Firma adulterada devuelve 400
    session_bad_sig = _mock_session(_result(cert_orm), _result(unidad))
    _setup(session_bad_sig)
    res_bad = client.get(f"/api/finanzas/solvencia/verificar/{cert_data['folio']}?sig=firma_falsa")
    assert res_bad.status_code == 400

    # Folio no encontrado devuelve 404
    session_404 = _mock_session(_result(None))
    _setup(session_404)
    assert client.get("/api/finanzas/solvencia/verificar/SOLV-NO-EXISTE?sig=abc").status_code == 404
    app.dependency_overrides = {}


def test_emitir_solvencia_con_deuda_pendiente_devuelve_409(client: TestClient) -> None:
    unidad = Unidad(id=4, identificador="PH-01", estructura_id=1, alicuota=Decimal("10.0000"))
    session = _mock_session(_result(unidad), _result(Decimal("60.00")))
    _setup(session)

    res = client.post("/api/finanzas/solvencia/4", headers=HEADERS)
    assert res.status_code == 409
    assert "60.00 USD" in res.json()["detail"]

    # Unidad no encontrada -> 404
    session_no_u = _mock_session(_result(None))
    _setup(session_no_u)
    assert client.post("/api/finanzas/solvencia/999", headers=HEADERS).status_code == 404

    # Idempotencia duplicada -> 409
    _setup(_mock_session(), redis_new=False)
    assert client.post("/api/finanzas/solvencia/4", headers=HEADERS).status_code == 409
    app.dependency_overrides = {}


def test_facturacion_lph_nucleo_helpers_cuota_fija_variables_y_recibos() -> None:
    """Ataque unitario directo a helpers de facturacion_lph.py para cobertura de mutantes."""
    import pytest

    from src.schemas import FacturarPeriodoRequest

    u1 = Unidad(
        id=1,
        identificador="A-01",
        estructura_id=1,
        alicuota=Decimal("60.0000"),
        cuota_fija_usd=Decimal("40.00"),
        credito_disponible_usd=Decimal("50.00"),
    )
    u2 = Unidad(
        id=2,
        identificador="A-02",
        estructura_id=1,
        alicuota=Decimal("40.0000"),
        cuota_fija_usd=Decimal("0.00"),
        credito_disponible_usd=Decimal("5.00"),
    )

    req_fija = FacturarPeriodoRequest(periodo="2026-10", modalidad="CUOTA_FIJA", monto_cuota_fija_usd=Decimal("20.00"))
    items_fija, superavit = _cargos_cuota_fija(req_fija, [u1, u2], Decimal("50.00"))
    assert items_fija[1][0][0] == "CUOTA_FIJA"
    assert items_fija[1][0][1] == "Cuota fija mensual (2026-10)"
    assert items_fija[1][0][2] == Decimal("40.00")
    assert items_fija[2][0][2] == Decimal("20.00")
    assert superavit == Decimal("10.00")

    # Si total fijo < total egresos, retorna diferencia negativa sin truncar
    _, superavit_cero = _cargos_cuota_fija(req_fija, [u1, u2], Decimal("80.00"))
    assert superavit_cero == Decimal("-20.00")

    # Error si una unidad no tiene cuota individual (>0) ni global
    req_fija_sin_monto = FacturarPeriodoRequest(periodo="2026-10", modalidad="CUOTA_FIJA", monto_cuota_fija_usd=None)
    with pytest.raises(ErrorFinanciero, match="CUOTA_FIJA"):
        _cargos_cuota_fija(req_fija_sin_monto, [u1, u2], Decimal("10.00"))

    # Cargos variables: PARTES_IGUALES sin fondo de reserva (> 0)
    req_pi = FacturarPeriodoRequest(periodo="2026-10", modalidad="PARTES_IGUALES", incluir_fondo_reserva=False)
    items_pi = _cargos_variables(req_pi, [u1, u2], Decimal("100.00"), Decimal("0.00"))
    assert len(items_pi[1]) == 1
    assert items_pi[1][0][0] == "GASTO_COMUN"
    assert items_pi[1][0][1] == "Cuota parte de gastos comunes (2026-10)"
    assert items_pi[1][0][2] == Decimal("50.00")
    assert items_pi[2][0][2] == Decimal("50.00")

    # Cargos variables: ALICUOTA con reserva > 0 emite GASTO_COMUN y FONDO_RESERVA
    req_al = FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA", incluir_fondo_reserva=True)
    items_al = _cargos_variables(req_al, [u1, u2], Decimal("100.00"), Decimal("10.00"))
    assert [t[0] for t in items_al[1]] == ["GASTO_COMUN", "FONDO_RESERVA"]
    assert items_al[1][0][1] == "Cuota parte de gastos comunes (2026-10)"
    assert items_al[1][1][1] == "Aporte al Fondo de Reserva Legal"
    assert items_al[1][0][2] == Decimal("60.00")
    assert items_al[1][1][2] == Decimal("6.00")
    assert items_al[2][0][2] == Decimal("40.00")
    assert items_al[2][1][2] == Decimal("4.00")

    # Cuota extraordinaria <= 0 no agrega ítems; > 0 prorratea por alícuota y agrega fallback desc
    _anexar_cuota_extraordinaria(req_al, [u1, u2], items_al)
    assert len(items_al[1]) == 2

    req_ext_pi = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="PARTES_IGUALES",
        cuota_extraordinaria_total_usd=Decimal("30.00"),
    )
    items_ext: dict[int, list[tuple[str, str, Decimal]]] = {1: [], 2: []}
    _anexar_cuota_extraordinaria(req_ext_pi, [u1, u2], items_ext)
    assert items_ext[1][0][0] == "CUOTA_EXTRAORDINARIA"
    assert items_ext[1][0][1] == "Cuota extraordinaria aprobada"
    assert items_ext[1][0][2] == Decimal("15.00")
    assert items_ext[2][0][2] == Decimal("15.00")

    # Cuota extraordinaria en ALICUOTA con alícuotas que no suman 100% -> 400
    req_ext_al = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="ALICUOTA",
        cuota_extraordinaria_total_usd=Decimal("30.00"),
    )
    u_bad = Unidad(
        id=3,
        identificador="A-03",
        estructura_id=1,
        alicuota=Decimal("10.0000"),
        credito_disponible_usd=Decimal("0.00"),
    )
    with pytest.raises(ErrorFinanciero, match="100.0000%"):
        _anexar_cuota_extraordinaria(req_ext_al, [u1, u_bad], {1: [], 3: []})

    # Pruebas directas sobre calcular_cargos_modalidad (CUOTA_FIJA y ALICUOTA con extraordinaria)
    req_mod_fija = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="CUOTA_FIJA",
        monto_cuota_fija_usd=Decimal("20.00"),
        cuota_extraordinaria_total_usd=Decimal("20.00"),
    )
    items_mod_fija, sup_mod = calcular_cargos_modalidad(req_mod_fija, [u1, u2], Decimal("50.00"), Decimal("0.00"))
    assert sup_mod == Decimal("10.00")
    assert [t[0] for t in items_mod_fija[1]] == ["CUOTA_FIJA", "CUOTA_EXTRAORDINARIA"]

    req_mod_al = FacturarPeriodoRequest(
        periodo="2026-10",
        modalidad="ALICUOTA",
        incluir_fondo_reserva=True,
        cuota_extraordinaria_total_usd=Decimal("20.00"),
    )
    items_mod_al, sup_mod_al = calcular_cargos_modalidad(req_mod_al, [u1, u2], Decimal("100.00"), Decimal("10.00"))
    assert sup_mod_al == Decimal("0.00")
    assert [t[0] for t in items_mod_al[1]] == ["GASTO_COMUN", "FONDO_RESERVA", "CUOTA_EXTRAORDINARIA"]
    assert items_mod_al[1][2][2] == Decimal("12.00")
    assert items_mod_al[2][2][2] == Decimal("8.00")

    # _crear_recibo_e_items_unidad: crédito cubre total -> PAGADO y abono negativo
    recibo_pagado, r_items, bruto_1, cred_1 = _crear_recibo_e_items_unidad(
        u1,
        "2026-10",
        [("CUOTA_FIJA", "Cuota", Decimal("40.00"))],
    )
    assert bruto_1 == Decimal("40.00")
    assert cred_1 == Decimal("40.00")
    assert recibo_pagado.monto_usd == Decimal("40.00")
    assert recibo_pagado.monto_pagado_usd == Decimal("40.00")
    assert recibo_pagado.estado == "PAGADO"
    assert recibo_pagado.bloqueado is False
    assert u1.credito_disponible_usd == Decimal("10.00")
    assert r_items[-1].tipo_item == "ABONO_CREDITO_PREVIO"
    assert r_items[-1].descripcion == "Abono automático de saldo a favor disponible"
    assert r_items[-1].monto_usd == Decimal("-40.00")

    # Cargo bruto cero produce recibo en 0.00 marcado como PAGADO sin abono
    recibo_cero, items_cero, bruto_cero, cred_cero = _crear_recibo_e_items_unidad(u1, "2026-10", [])
    assert bruto_cero == Decimal("0.00")
    assert cred_cero == Decimal("0.00")
    assert recibo_cero.monto_usd == Decimal("0.00")
    assert recibo_cero.monto_pagado_usd == Decimal("0.00")
    assert recibo_cero.estado == "PAGADO"
    assert items_cero == []

    # Crédito parcial deja recibo PENDIENTE y consume todo el crédito
    recibo_pend, r_items2, bruto_2, cred_2 = _crear_recibo_e_items_unidad(
        u2,
        "2026-10",
        [("GASTO_COMUN", "Gasto", Decimal("25.00"))],
    )
    assert bruto_2 == Decimal("25.00")
    assert cred_2 == Decimal("5.00")
    assert recibo_pend.monto_usd == Decimal("20.00")
    assert recibo_pend.estado == "PENDIENTE"
    assert u2.credito_disponible_usd == Decimal("0.00")
    assert len(r_items2) == 2


async def test_cargar_contexto_facturacion_respaldo_diez_por_ciento() -> None:
    """Sin fondo RESERVA_LEGAL activo, cargar_contexto_facturacion aplica 10.00% por defecto."""
    from src.schemas import FacturarPeriodoRequest

    u = Unidad(id=1, identificador="A-01", estructura_id=1, alicuota=Decimal("100.0000"))
    egreso = Egreso(
        id=1,
        periodo="2026-10",
        categoria="MANT",
        descripcion="Bomba",
        monto=Decimal("200.00"),
        moneda="USD",
        monto_usd=Decimal("200.00"),
        tasa_cambio=Decimal("36.5000"),
        es_gasto_comun=True,
    )
    session = _mock_session(_result_list([u]), _result_list([egreso]), _result(None))
    req = FacturarPeriodoRequest(periodo="2026-10", modalidad="ALICUOTA", incluir_fondo_reserva=True)
    unidades, total_eg, fondo, recargo = await cargar_contexto_facturacion(session, req)
    assert len(unidades) == 1
    assert total_eg == Decimal("200.00")
    assert fondo is None
    assert recargo == Decimal("20.00")


async def test_persistir_lote_facturacion_actualiza_fondos_y_recibos() -> None:
    """Verifica actualización de fondo según modalidad, flush, recibo_id en ítems y totales netos."""
    u1 = Unidad(
        id=1,
        identificador="A-01",
        estructura_id=1,
        alicuota=Decimal("100.0000"),
        credito_disponible_usd=Decimal("10.00"),
    )
    fondo_fija = FondoCondominio(
        id=1,
        nombre="Reserva",
        tipo="RESERVA_LEGAL",
        porcentaje_recargo=Decimal("10.00"),
        saldo_actual_usd=Decimal("100.00"),
        es_activo=True,
    )
    session_fija = _mock_session()
    tot_bruto, tot_cred, tot_neto = await persistir_lote_facturacion(
        session_fija,
        [u1],
        "2026-10",
        "CUOTA_FIJA",
        {1: [("CUOTA_FIJA", "Cuota fija mensual (2026-10)", Decimal("40.00"))]},
        fondo_fija,
        Decimal("5.00"),
        Decimal("12.00"),
    )
    assert (tot_bruto, tot_cred, tot_neto) == (Decimal("40.00"), Decimal("10.00"), Decimal("30.00"))
    assert fondo_fija.saldo_actual_usd == Decimal("112.00")
    session_fija.flush.assert_awaited_once()
    session_fija.commit.assert_awaited_once()
    items_fija_add = [c.args[0] for c in session_fija.add.call_args_list if isinstance(c.args[0], ReciboItem)]
    assert len(items_fija_add) == 2
    assert all(it.recibo_id == 1 for it in items_fija_add)

    u2 = Unidad(
        id=2,
        identificador="A-02",
        estructura_id=1,
        alicuota=Decimal("100.0000"),
        credito_disponible_usd=Decimal("0.00"),
    )
    fondo_al = FondoCondominio(
        id=2,
        nombre="Reserva 2",
        tipo="RESERVA_LEGAL",
        porcentaje_recargo=Decimal("10.00"),
        saldo_actual_usd=Decimal("50.00"),
        es_activo=True,
    )
    session_al = _mock_session()
    b2, c2, n2 = await persistir_lote_facturacion(
        session_al,
        [u2],
        "2026-11",
        "ALICUOTA",
        {2: [("GASTO_COMUN", "Cuota parte", Decimal("60.00"))]},
        fondo_al,
        Decimal("6.00"),
        Decimal("99.00"),
    )
    assert (b2, c2, n2) == (Decimal("60.00"), Decimal("0.00"), Decimal("60.00"))
    assert fondo_al.saldo_actual_usd == Decimal("56.00")
