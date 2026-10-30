"""Pruebas unitarias Nivel 11X para el Hito 11: Gobernanza Digital, Cartas Consulta (Art. 23 LPH) y Asambleas."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from src.database import get_db
from src.dependencies import get_current_user
from src.finanzas import (
    ErrorFinanciero,
    calcular_ip_hash_voto,
    construir_mensaje_voto_consulta,
    evaluar_escrutinio_consulta,
    generar_firma_voto_consulta,
    umbral_quorum_por_regla,
    verificar_firma_voto_consulta,
)
from src.main import app
from src.models import (
    BitacoraActa,
    ConsultaComunitaria,
    ContratoOcupacion,
    OpcionConsulta,
    Unidad,
    VotoConsulta,
)
from src.redis_client import get_redis_client
from src.security import SECRET_KEY

HEADERS = {"Idempotency-Key": "018f4a12-1111-7000-8000-000000001111"}


class FakeUser:
    def __init__(self, user_id: int = 1, rol: str = "PRESIDENTE", es_activo: bool = True) -> None:
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
    added: list[Any] = []

    def _add(obj: Any) -> None:
        if getattr(obj, "id", None) is None:
            obj.id = 100 + len(added)
        added.append(obj)

    session.add = MagicMock(side_effect=_add)

    async def _flush() -> None:
        for idx, obj in enumerate(added, start=1):
            if getattr(obj, "id", None) is None:
                obj.id = 200 + idx

    async def _refresh(instance: Any, *args: object, **kwargs: object) -> None:
        if getattr(instance, "id", None) is None:
            instance.id = 300

    session.flush = _flush
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
# 1. FUNCIONES PURAS CRIPTOGRÁFICAS Y DE ESCRUTINIO LPH (src/finanzas.py)
# ==============================================================================


def test_umbral_quorum_por_regla_y_error() -> None:
    assert umbral_quorum_por_regla("DOS_TERCIOS") == Decimal("66.6700")
    assert umbral_quorum_por_regla("MAYORIA_SIMPLE") == Decimal("50.0100")
    assert umbral_quorum_por_regla("UNANIMIDAD") == Decimal("100.0000")
    with pytest.raises(ErrorFinanciero, match="Regla de quórum inválida"):
        umbral_quorum_por_regla("CUARTO")


def test_firma_voto_consulta_y_ip_hash() -> None:
    fecha_iso = "2026-10-30T12:00:00+00:00"
    msg = construir_mensaje_voto_consulta(4, 12, 1, Decimal("25.5"), fecha_iso)
    assert msg == "VOTO|v1|4|12|1|25.5000|2026-10-30T12:00:00+00:00"

    firma = generar_firma_voto_consulta(4, 12, 1, Decimal("25.5000"), fecha_iso, SECRET_KEY)
    assert len(firma) == 64
    assert verificar_firma_voto_consulta(4, 12, 1, Decimal("25.5000"), fecha_iso, firma, SECRET_KEY) is True
    assert verificar_firma_voto_consulta(4, 12, 2, Decimal("25.5000"), fecha_iso, firma, SECRET_KEY) is False
    assert verificar_firma_voto_consulta(4, 12, 1, Decimal("25.5000"), fecha_iso, "   ", SECRET_KEY) is False

    h1 = calcular_ip_hash_voto("192.168.1.50", 4, SECRET_KEY)
    h2 = calcular_ip_hash_voto("", 4, SECRET_KEY)
    assert len(h1) == 64 and len(h2) == 64 and h1 != h2


def test_evaluar_escrutinio_consulta_tres_estados() -> None:
    # 1. Sin quórum (participación 45% < 66.67%)
    est_sq, part_sq, aprob_sq = evaluar_escrutinio_consulta(
        Decimal("66.6700"), {1}, {1: Decimal("30.0000"), 2: Decimal("15.0000")}
    )
    assert est_sq == "CERRADA_SIN_QUORUM"
    assert part_sq == Decimal("45.0000")
    assert aprob_sq == Decimal("30.0000")

    # 2. Aprobada (participación 80%, aprobatoria 70% >= 66.67%)
    est_ap, part_ap, aprob_ap = evaluar_escrutinio_consulta(
        Decimal("66.6700"), {1}, {1: Decimal("70.0000"), 2: Decimal("10.0000")}
    )
    assert est_ap == "CERRADA_APROBADA"
    assert part_ap == Decimal("80.0000")
    assert aprob_ap == Decimal("70.0000")

    # 3. Rechazada (participación 80% >= 66.67%, pero aprobatoria 40% < 66.67%)
    est_re, part_re, aprob_re = evaluar_escrutinio_consulta(
        Decimal("66.6700"), {1}, {1: Decimal("40.0000"), 2: Decimal("40.0000")}
    )
    assert est_re == "CERRADA_RECHAZADA"
    assert part_re == Decimal("80.0000")
    assert aprob_re == Decimal("40.0000")


# ==============================================================================
# 2. ENDPOINTS DE CREACIÓN Y CONSULTA (/api/consultas)
# ==============================================================================


def test_crear_consulta_exitoso_y_validaciones(client: TestClient) -> None:
    ahora = datetime.now(UTC)
    cierre = ahora + timedelta(days=5)
    op1 = OpcionConsulta(id=1, consulta_id=100, etiqueta="APROBAR PRESUPUESTO A", es_opcion_aprobatoria=True)
    op2 = OpcionConsulta(id=2, consulta_id=100, etiqueta="RECHAZAR PROPUESTA", es_opcion_aprobatoria=False)

    session = _mock_session(
        _result_list([op1, op2]),  # _cargar_opciones_y_votos -> opciones
        _result_list([]),  # _cargar_opciones_y_votos -> votos
        _result_list([1]),  # _unidades_usuario
    )
    _setup(session, user=FakeUser(1, "PRESIDENTE"))

    resp = client.post(
        "/api/consultas",
        headers=HEADERS,
        json={
            "titulo": "Carta Consulta #04-2026: Impermeabilización Torre A",
            "descripcion_legal": "Reparación urgente del manto asfáltico conforme al Art. 23 LPH.",
            "tipo_consulta": "CARTA_CONSULTA_1RA",
            "regla_quorum": "DOS_TERCIOS",
            "fecha_cierre": cierre.isoformat(),
            "opciones": [
                {"etiqueta": "APROBAR PRESUPUESTO A", "es_opcion_aprobatoria": True},
                {"etiqueta": "RECHAZAR PROPUESTA", "es_opcion_aprobatoria": False},
            ],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["quorum_minimo_alicuota"] == "66.6700"
    assert body["estado"] == "ABIERTA"
    assert len(body["opciones"]) == 2
    assert body["ya_voto_usuario"] is False

    # Idempotency-Key duplicada -> 409
    _setup(_mock_session(), user=FakeUser(1, "SECRETARIO"), redis_new=False)
    resp_dup = client.post(
        "/api/consultas",
        headers=HEADERS,
        json={
            "titulo": "Carta Consulta Duplicada",
            "descripcion_legal": "Descripción legal suficiente.",
            "fecha_cierre": cierre.isoformat(),
            "opciones": [
                {"etiqueta": "SÍ", "es_opcion_aprobatoria": True},
                {"etiqueta": "NO", "es_opcion_aprobatoria": False},
            ],
        },
    )
    assert resp_dup.status_code == 409


def test_listar_y_obtener_detalle_consulta_con_voto_previo(client: TestClient) -> None:
    ahora = datetime.now(UTC)
    consulta = ConsultaComunitaria(
        id=7,
        titulo="Carta Consulta Ascensor",
        descripcion_legal="Cambio de guayas.",
        tipo_consulta="CARTA_CONSULTA_1RA",
        regla_quorum="DOS_TERCIOS",
        quorum_minimo_alicuota=Decimal("66.6700"),
        fecha_apertura=ahora,
        fecha_cierre=ahora + timedelta(days=3),
        estado="ABIERTA",
        creada_por_id=1,
        acta_bitacora_id=None,
    )
    op1 = OpcionConsulta(id=10, consulta_id=7, etiqueta="Aprobar", es_opcion_aprobatoria=True)
    op2 = OpcionConsulta(id=11, consulta_id=7, etiqueta="Rechazar", es_opcion_aprobatoria=False)
    voto = VotoConsulta(
        id=55,
        consulta_id=7,
        unidad_id=3,
        usuario_id=2,
        opcion_id=10,
        alicuota_capturada=Decimal("35.0000"),
        fecha_voto=ahora,
        ip_hash="a" * 64,
        firma_hmac="b" * 64,
    )

    session = _mock_session(
        _result_list([consulta]),  # listar_consultas -> consultas
        _result_list([3]),  # _unidades_usuario
        _result_list([op1, op2]),  # _cargar_opciones_y_votos -> opciones
        _result_list([voto]),  # _cargar_opciones_y_votos -> votos
    )
    _setup(session, user=FakeUser(2, "PROPIETARIO"))
    resp_list = client.get("/api/consultas")
    assert resp_list.status_code == 200
    items = resp_list.json()
    assert len(items) == 1
    assert items[0]["participacion_alicuota"] == "35.0000"
    assert items[0]["ya_voto_usuario"] is True

    # Detalle con unidad encontrada y con fallback de unidad None
    unidad = Unidad(id=3, identificador="A-03", estructura_id=1, alicuota=Decimal("35.0000"))
    session_det = _mock_session(
        _result(consulta),
        _result_list([op1, op2]),
        _result_list([voto]),
        _result_list([3]),
        _result(unidad),
    )
    _setup(session_det, user=FakeUser(2, "PROPIETARIO"))
    resp_det = client.get("/api/consultas/7")
    assert resp_det.status_code == 200
    det = resp_det.json()
    assert det["mi_voto"]["identificador_unidad"] == "A-03"
    assert det["mi_voto"]["firma_hmac"] == "b" * 64

    # 404 cuando no existe
    _setup(_mock_session(_result(None)), user=FakeUser(2, "PROPIETARIO"))
    assert client.get("/api/consultas/999").status_code == 404


# ==============================================================================
# 3. VOTACIÓN PONDERADA POR ALÍCUOTA E INVARIANTES NEGATIVAS (/votar)
# ==============================================================================


def test_votar_en_consulta_propietario_exitoso_e_inquilino_con_y_sin_poder(client: TestClient) -> None:
    ahora = datetime.now(UTC)
    consulta = ConsultaComunitaria(
        id=8,
        titulo="Carta Consulta #08",
        descripcion_legal="Pintura de fachada.",
        tipo_consulta="CARTA_CONSULTA_1RA",
        regla_quorum="DOS_TERCIOS",
        quorum_minimo_alicuota=Decimal("66.6700"),
        fecha_apertura=ahora,
        fecha_cierre=ahora + timedelta(days=3),
        estado="ABIERTA",
        creada_por_id=1,
    )
    op = OpcionConsulta(id=20, consulta_id=8, etiqueta="Aprobar Fachada", es_opcion_aprobatoria=True)
    unidad = Unidad(id=5, identificador="B-05", estructura_id=1, alicuota=Decimal("40.0000"))
    contrato_prop = ContratoOcupacion(
        id=1, usuario_id=2, unidad_id=5, tipo_ocupante="PROPIETARIO", es_activo=True, puede_votar_asamblea=True
    )
    voto_guardado = VotoConsulta(
        id=100,
        consulta_id=8,
        unidad_id=5,
        usuario_id=2,
        opcion_id=20,
        alicuota_capturada=Decimal("40.0000"),
        fecha_voto=ahora,
        ip_hash="c" * 64,
        firma_hmac="d" * 64,
    )

    session = _mock_session(
        _result(consulta),
        _result(op),
        _result(unidad),
        _result(contrato_prop),
        _result(None),  # sin voto previo
        _result_list([op]),
        _result_list([voto_guardado]),
    )
    _setup(session, user=FakeUser(2, "PROPIETARIO"))
    resp = client.post("/api/consultas/8/votar", headers=HEADERS, json={"unidad_id": 5, "opcion_id": 20})
    assert resp.status_code == 201
    recibo = resp.json()
    assert recibo["identificador_unidad"] == "B-05"
    assert recibo["alicuota_capturada"] == "40.0000"
    assert recibo["participacion_total_alicuota"] == "40.0000"
    assert len(recibo["firma_hmac"]) == 64

    # Inquilino SIN poder registrado -> 403 Forbidden
    contrato_inq_sin_poder = ContratoOcupacion(
        id=2, usuario_id=3, unidad_id=5, tipo_ocupante="INQUILINO", es_activo=True, puede_votar_asamblea=False
    )
    session_inq = _mock_session(
        _result(consulta),
        _result(op),
        _result(unidad),
        _result(contrato_inq_sin_poder),
    )
    _setup(session_inq, user=FakeUser(3, "PROPIETARIO"))
    resp_inq = client.post("/api/consultas/8/votar", headers=HEADERS, json={"unidad_id": 5, "opcion_id": 20})
    assert resp_inq.status_code == 403
    assert "propietario titular" in resp_inq.json()["detail"].lower()


def test_votar_errores_404_403_409_y_race_condition(client: TestClient) -> None:
    ahora = datetime.now(UTC)
    consulta_abierta = ConsultaComunitaria(
        id=8,
        titulo="Consulta",
        descripcion_legal="Texto legal.",
        tipo_consulta="CARTA_CONSULTA_1RA",
        regla_quorum="DOS_TERCIOS",
        quorum_minimo_alicuota=Decimal("66.6700"),
        fecha_apertura=ahora,
        fecha_cierre=ahora + timedelta(days=2),
        estado="ABIERTA",
        creada_por_id=1,
    )
    consulta_cerrada = ConsultaComunitaria(
        id=9,
        titulo="Cerrada",
        descripcion_legal="Texto.",
        tipo_consulta="CARTA_CONSULTA_1RA",
        regla_quorum="DOS_TERCIOS",
        quorum_minimo_alicuota=Decimal("66.6700"),
        fecha_apertura=ahora,
        fecha_cierre=ahora + timedelta(days=2),
        estado="CERRADA_APROBADA",
        creada_por_id=1,
    )
    op = OpcionConsulta(id=20, consulta_id=8, etiqueta="Sí", es_opcion_aprobatoria=True)
    unidad = Unidad(id=5, identificador="B-05", estructura_id=1, alicuota=Decimal("20.0000"))
    contrato = ContratoOcupacion(
        id=1, usuario_id=2, unidad_id=5, tipo_ocupante="PROPIETARIO", es_activo=True, puede_votar_asamblea=True
    )

    payload = {"unidad_id": 5, "opcion_id": 20}

    # 1. Idempotency-Key duplicada -> 409
    _setup(_mock_session(), user=FakeUser(2, "PROPIETARIO"), redis_new=False)
    assert client.post("/api/consultas/8/votar", headers=HEADERS, json=payload).status_code == 409

    # 2. Consulta no encontrada -> 404
    _setup(_mock_session(_result(None)), user=FakeUser(2, "PROPIETARIO"))
    assert client.post("/api/consultas/99/votar", headers=HEADERS, json=payload).status_code == 404

    # 3. Consulta cerrada -> 409
    _setup(_mock_session(_result(consulta_cerrada)), user=FakeUser(2, "PROPIETARIO"))
    assert client.post("/api/consultas/9/votar", headers=HEADERS, json=payload).status_code == 409

    # 4. Opción no encontrada -> 404
    _setup(_mock_session(_result(consulta_abierta), _result(None)), user=FakeUser(2, "PROPIETARIO"))
    assert (
        client.post("/api/consultas/8/votar", headers=HEADERS, json={"unidad_id": 5, "opcion_id": 99}).status_code
        == 404
    )

    # 5. Unidad no encontrada -> 404
    _setup(_mock_session(_result(consulta_abierta), _result(op), _result(None)), user=FakeUser(2, "PROPIETARIO"))
    assert (
        client.post("/api/consultas/8/votar", headers=HEADERS, json={"unidad_id": 99, "opcion_id": 20}).status_code
        == 404
    )

    # 6. Sin contrato activo sobre la unidad -> 403
    _setup(
        _mock_session(_result(consulta_abierta), _result(op), _result(unidad), _result(None)),
        user=FakeUser(2, "PROPIETARIO"),
    )
    assert client.post("/api/consultas/8/votar", headers=HEADERS, json=payload).status_code == 403

    # 7. Voto previo existente -> 409
    voto_previo = VotoConsulta(
        id=1,
        consulta_id=8,
        unidad_id=5,
        usuario_id=2,
        opcion_id=20,
        alicuota_capturada=Decimal("20.0000"),
        fecha_voto=ahora,
        ip_hash="a" * 64,
        firma_hmac="b" * 64,
    )
    _setup(
        _mock_session(_result(consulta_abierta), _result(op), _result(unidad), _result(contrato), _result(voto_previo)),
        user=FakeUser(2, "PROPIETARIO"),
    )
    assert client.post("/api/consultas/8/votar", headers=HEADERS, json=payload).status_code == 409

    # 8. IntegrityError concurrente en commit -> 409
    sess_ie = _mock_session(_result(consulta_abierta), _result(op), _result(unidad), _result(contrato), _result(None))
    sess_ie.commit.side_effect = IntegrityError("dup", {}, Exception("uq_voto_consulta_unidad"))
    _setup(sess_ie, user=FakeUser(2, "PROPIETARIO"))
    assert client.post("/api/consultas/8/votar", headers=HEADERS, json=payload).status_code == 409


# ==============================================================================
# 4. CIERRE DE CONSULTA Y GENERACIÓN AUTOMÁTICA DE ACTA EN BITÁCORA (/cerrar)
# ==============================================================================


def test_cerrar_consulta_genera_acta_bitacora_y_maneja_errores(client: TestClient) -> None:
    ahora = datetime.now(UTC)
    consulta = ConsultaComunitaria(
        id=12,
        titulo="Carta Consulta #12: Bomba Hidroneumática",
        descripcion_legal="Sustitución de bomba principal.",
        tipo_consulta="CARTA_CONSULTA_1RA",
        regla_quorum="DOS_TERCIOS",
        quorum_minimo_alicuota=Decimal("66.6700"),
        fecha_apertura=ahora,
        fecha_cierre=ahora + timedelta(days=1),
        estado="ABIERTA",
        creada_por_id=1,
    )
    op_si = OpcionConsulta(id=30, consulta_id=12, etiqueta="Aprobar Bomba", es_opcion_aprobatoria=True)
    op_no = OpcionConsulta(id=31, consulta_id=12, etiqueta="Rechazar", es_opcion_aprobatoria=False)
    v1 = VotoConsulta(
        id=1,
        consulta_id=12,
        unidad_id=1,
        usuario_id=2,
        opcion_id=30,
        alicuota_capturada=Decimal("40.0000"),
        fecha_voto=ahora,
        ip_hash="1" * 64,
        firma_hmac="a" * 64,
    )
    v2 = VotoConsulta(
        id=2,
        consulta_id=12,
        unidad_id=2,
        usuario_id=3,
        opcion_id=30,
        alicuota_capturada=Decimal("30.0000"),
        fecha_voto=ahora,
        ip_hash="2" * 64,
        firma_hmac="b" * 64,
    )

    session = _mock_session(
        _result(consulta),
        _result_list([op_si, op_no]),
        _result_list([v1, v2]),
    )
    _setup(session, user=FakeUser(1, "SECRETARIO"))

    resp = client.post("/api/consultas/12/cerrar", headers=HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["estado"] == "CERRADA_APROBADA"
    assert body["participacion_alicuota"] == "70.0000"
    assert body["alicuota_aprobatoria"] == "70.0000"
    assert body["acta_bitacora_id"] >= 100
    assert len(body["hash_global_escrutinio"]) == 64

    # Verificar que se añadió un objeto BitacoraActa a la sesión
    objetos_agregados = [call.args[0] for call in session.add.call_args_list]
    assert any(isinstance(o, BitacoraActa) for o in objetos_agregados)

    # Errores: Idempotency-Key duplicada (409), no encontrada (404), ya cerrada (409)
    _setup(_mock_session(), user=FakeUser(1, "PRESIDENTE"), redis_new=False)
    assert client.post("/api/consultas/12/cerrar", headers=HEADERS).status_code == 409

    _setup(_mock_session(_result(None)), user=FakeUser(1, "PRESIDENTE"))
    assert client.post("/api/consultas/999/cerrar", headers=HEADERS).status_code == 404

    _setup(_mock_session(_result(consulta)), user=FakeUser(1, "PRESIDENTE"))
    assert client.post("/api/consultas/12/cerrar", headers=HEADERS).status_code == 409
