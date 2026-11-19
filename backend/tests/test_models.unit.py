import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    AreaSocial,
    AuditoriaRecibo,
    Base,
    BitacoraActa,
    CertificadoSolvencia,
    Comunicado,
    ConsultaComunitaria,
    ContratoOcupacion,
    Egreso,
    Estructura,
    FondoCondominio,
    FotoVocero,
    Incidencia,
    IncidenciaAdhesion,
    OpcionConsulta,
    PagoReportado,
    PaqueteRecibido,
    PaseVisita,
    PlantillaTarea,
    Recibo,
    ReciboItem,
    ReporteMensual,
    ReservaAreaSocial,
    TareaDiaria,
    TasaCambio,
    Unidad,
    Usuario,
    VotoConsulta,
)
from tests._sqlite_helpers import SeededCondoContext, create_sqlite_fk_factory, seed_condo_base


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


MODELOS_ORM_27: tuple[type[Base], ...] = (
    Usuario,
    Estructura,
    Unidad,
    ContratoOcupacion,
    TasaCambio,
    Recibo,
    PagoReportado,
    Egreso,
    AuditoriaRecibo,
    ReporteMensual,
    Incidencia,
    IncidenciaAdhesion,
    PlantillaTarea,
    TareaDiaria,
    FotoVocero,
    BitacoraActa,
    Comunicado,
    FondoCondominio,
    ReciboItem,
    CertificadoSolvencia,
    ConsultaComunitaria,
    OpcionConsulta,
    VotoConsulta,
    PaseVisita,
    PaqueteRecibido,
    AreaSocial,
    ReservaAreaSocial,
)


async def _poblar_finanzas_y_operacion(
    session: AsyncSession,
    ctx: SeededCondoContext,
) -> tuple[TareaDiaria, BitacoraActa]:
    """Inserta registros válidos en tablas financieras, de mantenimiento y actas."""
    tasa = TasaCambio(condominio_id=1, fecha=date(2025, 1, 15), tasa_usd_ves=Decimal("46.0000"))
    recibo = Recibo(
        condominio_id=1,
        unidad_id=ctx.unidad_a_id,
        periodo="2026-10",
        monto_usd=Decimal("120.00"),
        monto_pagado_usd=Decimal("0.00"),
        estado="PENDIENTE",
        bloqueado=False,
    )
    incidencia = Incidencia(
        condominio_id=1,
        usuario_creador_id=ctx.propietario_id,
        area="Ascensor Torre A",
        descripcion="Ruido en polea del piso 3",
        estado="ABIERTO",
        adhesiones_count=1,
    )
    plantilla = PlantillaTarea(
        condominio_id=1,
        titulo="Limpieza de lobby",
        area="Lobby",
        frecuencia="DIARIA",
        activa=True,
    )
    acta = BitacoraActa(
        condominio_id=1,
        fecha=date(2026, 10, 12),
        hora="19:00",
        ubicacion="Salón de Usos Múltiples",
        contenido="Acta ordinaria de la junta de condominio.",
        autor_id=ctx.secretario_id,
    )
    fondo = FondoCondominio(
        condominio_id=1,
        nombre="Fondo de Reserva Legal",
        tipo="RESERVA_LEGAL",
        porcentaje_recargo=Decimal("10.00"),
        saldo_actual_usd=Decimal("1500.00"),
        es_activo=True,
    )
    session.add_all([tasa, recibo, incidencia, plantilla, acta, fondo])
    await session.flush()

    pago = PagoReportado(
        condominio_id=1,
        recibo_id=recibo.id,
        usuario_id=ctx.propietario_id,
        monto=Decimal("4550.00"),
        moneda="VES",
        monto_usd=Decimal("100.00"),
        tasa_cambio=Decimal("45.5000"),
        metodo_pago="PAGO_MOVIL",
        numero_referencia="REF-11X-001",
        url_comprobante="https://cdn.condominio.test/comprobante.avif",
        estado="EN_REVISION",
    )
    egreso = Egreso(
        condominio_id=1,
        periodo="2026-10",
        categoria="MANTENIMIENTO",
        descripcion="Revisión preventiva de ascensor",
        monto=Decimal("250.00"),
        moneda="USD",
        monto_usd=Decimal("250.00"),
        tasa_cambio=Decimal("45.5000"),
        incidencia_id=incidencia.id,
        es_gasto_comun=True,
        bloqueado=False,
    )
    adhesion = IncidenciaAdhesion(
        condominio_id=1,
        incidencia_id=incidencia.id,
        usuario_id=ctx.inquilino_id,
    )
    tarea = TareaDiaria(
        condominio_id=1,
        plantilla_id=plantilla.id,
        incidencia_id=incidencia.id,
        titulo="Limpieza de lobby",
        area="Lobby",
        fecha=date(2026, 10, 12),
        completada=False,
    )
    recibo_item = ReciboItem(
        condominio_id=1,
        recibo_id=recibo.id,
        tipo_item="GASTO_COMUN",
        descripcion="Cuota ordinaria alícuota 60%",
        monto_usd=Decimal("120.00"),
    )
    session.add_all(
        [
            pago,
            egreso,
            adhesion,
            tarea,
            recibo_item,
            ReporteMensual(condominio_id=1, periodo="2026-10", estado="PRELIMINAR"),
            FotoVocero(
                condominio_id=1,
                usuario_id=ctx.vocero_id,
                periodo="2026-10",
                area="Estacionamiento",
                comentario="Luminaria reparada",
                url_foto="/media/voceros/foto1.avif",
            ),
            Comunicado(
                condominio_id=1,
                titulo="Mantenimiento de tanque",
                contenido="Corte programado el viernes de 9:00 a 12:00.",
                enlace_externo="https://condominio.test/avisos/tanque",
                activo=True,
            ),
            CertificadoSolvencia(
                condominio_id=1,
                jti=str(uuid.uuid4()),
                folio="SOLV-2026-0001",
                unidad_id=ctx.unidad_a_id,
                emitido_por_id=ctx.tesorero_id,
                fecha_vencimiento=date(2026, 11, 12),
                deuda_verificada_usd=Decimal("0.00"),
                firma_hmac="b" * 64,
            ),
        ]
    )
    await session.flush()

    session.add(
        AuditoriaRecibo(
            condominio_id=1,
            recibo_id=recibo.id,
            pago_id=pago.id,
            usuario_id=ctx.tesorero_id,
            estado_viejo="EN_REVISION",
            estado_nuevo="APROBADO",
            motivo="Verificado contra estado de cuenta",
            prev_hash="0" * 64,
            record_hash="a" * 64,
        )
    )
    return tarea, acta


async def _poblar_gobernanza_y_accesos(
    session: AsyncSession,
    ctx: SeededCondoContext,
    acta_id: int,
    tarea_id: int,
) -> None:
    """Inserta registros válidos en consultas, votos, pases QR, paquetería y áreas sociales."""
    consulta = ConsultaComunitaria(
        condominio_id=1,
        titulo="Aprobación de impermeabilización",
        descripcion_legal="Carta consulta escrita conforme al Art. 23 de la LPH.",
        tipo_consulta="CARTA_CONSULTA_1RA",
        regla_quorum="DOS_TERCIOS",
        quorum_minimo_alicuota=Decimal("66.6667"),
        fecha_cierre=datetime(2026, 10, 31, 23, 59, tzinfo=UTC),
        estado="ABIERTA",
        creada_por_id=ctx.presidente_id,
        acta_bitacora_id=acta_id,
    )
    area_social = AreaSocial(
        condominio_id=1,
        nombre="Salón de Fiestas",
        aforo_maximo=80,
        costo_uso_usd=Decimal("50.00"),
        deposito_garantia_usd=Decimal("100.00"),
        requiere_solvencia_estricta=True,
        es_activa=True,
    )
    session.add_all([consulta, area_social])
    await session.flush()

    opcion = OpcionConsulta(
        condominio_id=1,
        consulta_id=consulta.id,
        etiqueta="Apruebo la obra",
        es_opcion_aprobatoria=True,
    )
    session.add(opcion)
    await session.flush()

    session.add_all(
        [
            VotoConsulta(
                condominio_id=1,
                jti=str(uuid.uuid4()),
                consulta_id=consulta.id,
                unidad_id=ctx.unidad_a_id,
                usuario_id=ctx.propietario_id,
                opcion_id=opcion.id,
                alicuota_capturada=Decimal("60.0000"),
                ip_hash="c" * 64,
                firma_hmac="d" * 64,
                prev_hash="0" * 64,
                record_hash="e" * 64,
            ),
            PaseVisita(
                condominio_id=1,
                jti=str(uuid.uuid4()),
                unidad_id=ctx.unidad_a_id,
                creado_por_id=ctx.propietario_id,
                nombre_visitante="Luis Visitante",
                cedula_visitante="V-21000001",
                placa_vehiculo="AB123CD",
                modalidad="UNICO_USO",
                valido_desde=datetime(2026, 10, 12, 8, 0, tzinfo=UTC),
                valido_hasta=datetime(2026, 10, 13, 8, 0, tzinfo=UTC),
                estado="ACTIVO",
                verificado_por_id=ctx.conserje_id,
                firma_hmac="f" * 64,
            ),
            PaqueteRecibido(
                condominio_id=1,
                unidad_id=ctx.unidad_a_id,
                recibido_por_id=ctx.conserje_id,
                empresa_envio="Zoom",
                descripcion="Caja mediana sellada",
                estado="EN_GARITA",
            ),
            ReservaAreaSocial(
                condominio_id=1,
                area_id=area_social.id,
                unidad_id=ctx.unidad_a_id,
                solicitante_id=ctx.propietario_id,
                fecha_evento=date(2026, 10, 25),
                motivo_evento="Reunión familiar",
                estado="CONFIRMADA",
                tarea_inspeccion_id=tarea_id,
            ),
        ]
    )


@pytest.mark.asyncio
async def test_persistencia_sqlite_fk_todas_las_27_tablas() -> None:
    """Persiste y consulta filas reales en las 27 tablas ORM sobre SQLite con FK activas."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        ctx = await seed_condo_base(factory)
        async with factory() as session:
            tarea, acta = await _poblar_finanzas_y_operacion(session, ctx)
            await _poblar_gobernanza_y_accesos(session, ctx, acta.id, tarea.id)
            await session.commit()

        tablas_verificadas: set[str] = set()
        async with factory() as verify_session:
            for modelo in MODELOS_ORM_27:
                conteo = (await verify_session.execute(select(func.count()).select_from(modelo))).scalar_one()
                assert conteo >= 1, f"La tabla {modelo.__tablename__} no registró filas persistidas"
                tablas_verificadas.add(modelo.__tablename__)

            consulta_db = (await verify_session.execute(select(ConsultaComunitaria))).scalars().one()
            assert len(consulta_db.opciones) == 1
            assert len(consulta_db.votos) == 1

        assert len(tablas_verificadas) == 27
        assert set(Base.metadata.tables.keys()) == tablas_verificadas
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_sqlite_foreign_key_rechaza_huerfano_y_checks() -> None:
    """Verifica que PRAGMA foreign_keys=ON y CheckConstraint lanzan IntegrityError."""
    engine, factory = await create_sqlite_fk_factory()
    try:
        async with factory() as session:
            session.add(Unidad(condominio_id=1, identificador="Z-999", estructura_id=999_999))
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            session.add(Recibo(condominio_id=1, unidad_id=999_999, periodo="2026-11", monto_usd=Decimal("10.00")))
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()

            session.add(TasaCambio(condominio_id=1, fecha=date(2026, 10, 13), tasa_usd_ves=Decimal("0.0000")))
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
    finally:
        await engine.dispose()
