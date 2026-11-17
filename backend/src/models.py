import uuid
from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from src.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (
        UniqueConstraint("condominio_id", "cedula", name="uq_usuario_condominio_cedula"),
        UniqueConstraint("condominio_id", "correo", name="uq_usuario_condominio_correo"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String, index=True)
    cedula: Mapped[str] = mapped_column(String, index=True)
    correo: Mapped[str] = mapped_column(String, index=True)
    telefono: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    es_activo: Mapped[bool] = mapped_column(Boolean, default=False)
    rol: Mapped[str] = mapped_column(String, default="FANTASMA")


class Estructura(Base):
    __tablename__ = "estructuras"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String)
    tipo: Mapped[str] = mapped_column(String)


class Unidad(Base):
    __tablename__ = "unidades"
    __table_args__ = (
        UniqueConstraint("condominio_id", "identificador", name="uq_unidad_condominio_identificador"),
        CheckConstraint("alicuota >= 0 AND alicuota <= 100", name="ck_unidades_alicuota_rango"),
        CheckConstraint("credito_disponible_usd >= 0", name="ck_unidades_credito_no_neg"),
        CheckConstraint("cuota_fija_usd IS NULL OR cuota_fija_usd >= 0", name="ck_unidades_cuota_fija_no_neg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    identificador: Mapped[str] = mapped_column(String, index=True)
    estructura_id: Mapped[int] = mapped_column(ForeignKey("estructuras.id"), index=True)
    alicuota: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("0.0000"), server_default="0.0000")
    cuota_fija_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=None)
    credito_disponible_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0.00"
    )


class ContratoOcupacion(Base):
    __tablename__ = "contratos_ocupacion"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True)
    tipo_ocupante: Mapped[str] = mapped_column(String)
    es_activo: Mapped[bool] = mapped_column(Boolean, default=False)
    puede_votar_asamblea: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TasaCambio(Base):
    """Tasa de cambio USD/VES registrada por día (USD es la moneda base contable)."""

    __tablename__ = "tasas_cambio"
    __table_args__ = (
        UniqueConstraint("condominio_id", "fecha", name="uq_tasa_cambio_condominio_fecha"),
        CheckConstraint("tasa_usd_ves > 0", name="ck_tasas_cambio_positiva"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    fecha: Mapped[date_type] = mapped_column(Date, index=True)
    tasa_usd_ves: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recibo(Base):
    """Recibo de cobranza de una unidad para un periodo (formato YYYY-MM)."""

    __tablename__ = "recibos"
    __table_args__ = (
        UniqueConstraint("condominio_id", "unidad_id", "periodo", name="uq_recibo_unidad_periodo"),
        CheckConstraint("monto_usd >= 0", name="ck_recibos_monto_no_neg"),
        CheckConstraint("monto_pagado_usd >= 0", name="ck_recibos_pagado_no_neg"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True)
    periodo: Mapped[str] = mapped_column(String(7), index=True)
    monto_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monto_pagado_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    estado: Mapped[str] = mapped_column(String, default="PENDIENTE")
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PagoReportado(Base):
    """Pago reportado por un propietario. Guarda la tasa del día exacto del reporte."""

    __tablename__ = "pagos_reportados"
    __table_args__ = (
        Index(
            "uq_pagos_metodo_ref_activo",
            "condominio_id",
            "metodo_pago",
            "numero_referencia",
            unique=True,
            postgresql_where=text("numero_referencia IS NOT NULL AND estado != 'RECHAZADO'"),
            sqlite_where=text("numero_referencia IS NOT NULL AND estado != 'RECHAZADO'"),
        ),
        CheckConstraint("monto > 0 AND monto_usd > 0 AND tasa_cambio > 0", name="ck_pagos_montos_positivos"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    recibo_id: Mapped[int] = mapped_column(ForeignKey("recibos.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3))
    monto_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tasa_cambio: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    metodo_pago: Mapped[str] = mapped_column(String)
    numero_referencia: Mapped[str | None] = mapped_column(String, nullable=True)
    url_comprobante: Mapped[str | None] = mapped_column(String, nullable=True)
    estado: Mapped[str] = mapped_column(String, default="EN_REVISION")
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Egreso(Base):
    """Gasto del condominio registrado por el Tesorero con su factura (AVIF)."""

    __tablename__ = "egresos"
    __table_args__ = (
        CheckConstraint("monto > 0 AND monto_usd > 0 AND tasa_cambio > 0", name="ck_egresos_montos_positivos"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    periodo: Mapped[str] = mapped_column(String(7), index=True)
    categoria: Mapped[str] = mapped_column(String)
    descripcion: Mapped[str] = mapped_column(String)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3))
    monto_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tasa_cambio: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    url_factura: Mapped[str | None] = mapped_column(String, nullable=True)
    incidencia_id: Mapped[int | None] = mapped_column(
        ForeignKey("incidencias.id"), nullable=True, default=None, index=True
    )
    es_gasto_comun: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditoriaRecibo(Base):
    """Pista de auditoría inmutable WORM: quién, cuándo, estado viejo/nuevo, motivo y hash-chain."""

    __tablename__ = "auditoria_recibos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    recibo_id: Mapped[int] = mapped_column(ForeignKey("recibos.id"), index=True)
    pago_id: Mapped[int | None] = mapped_column(ForeignKey("pagos_reportados.id"), nullable=True, index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True, index=True)
    estado_viejo: Mapped[str] = mapped_column(String)
    estado_nuevo: Mapped[str] = mapped_column(String)
    motivo: Mapped[str | None] = mapped_column(String, nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64), default="0" * 64, server_default="0" * 64, nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), default="", server_default="", nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReporteMensual(Base):
    """Reporte financiero mensual. El cierre es una acción inmutable (Candado Contable)."""

    __tablename__ = "reportes_mensuales"
    __table_args__ = (UniqueConstraint("condominio_id", "periodo", name="uq_reporte_mensual_condominio_periodo"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    periodo: Mapped[str] = mapped_column(String(7), index=True)
    estado: Mapped[str] = mapped_column(String, default="PRELIMINAR")
    url_pdf: Mapped[str | None] = mapped_column(String, nullable=True)
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Incidencia(Base):
    """Incidencia comunitaria reportada en el embudo vecinal con soporte de adhesión ('Me sumo')."""

    __tablename__ = "incidencias"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    usuario_creador_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    area: Mapped[str] = mapped_column(String, index=True)
    descripcion: Mapped[str] = mapped_column(String)
    url_foto: Mapped[str | None] = mapped_column(String, nullable=True)
    estado: Mapped[str] = mapped_column(String, default="ABIERTO", index=True)
    adhesiones_count: Mapped[int] = mapped_column(Integer, default=1)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class IncidenciaAdhesion(Base):
    """Adhesión única de un vecino a una incidencia abierta ('Me sumo')."""

    __tablename__ = "incidencias_adhesiones"
    __table_args__ = (
        UniqueConstraint("condominio_id", "incidencia_id", "usuario_id", name="uq_incidencia_usuario_adhesion"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    incidencia_id: Mapped[int] = mapped_column(ForeignKey("incidencias.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlantillaTarea(Base):
    """Plantilla recurrente de mantenimiento/conserjería definida por el Presidente."""

    __tablename__ = "plantillas_tareas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String)
    area: Mapped[str] = mapped_column(String)
    frecuencia: Mapped[str] = mapped_column(String, default="DIARIA")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TareaDiaria(Base):
    """Tarea diaria asignada al conserje (generada desde plantilla o vinculada a una incidencia)."""

    __tablename__ = "tareas_diarias"
    __table_args__ = (
        UniqueConstraint("condominio_id", "plantilla_id", "fecha", name="uq_tarea_diaria_plantilla_fecha"),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    plantilla_id: Mapped[int | None] = mapped_column(ForeignKey("plantillas_tareas.id"), nullable=True, index=True)
    incidencia_id: Mapped[int | None] = mapped_column(ForeignKey("incidencias.id"), nullable=True, index=True)
    titulo: Mapped[str] = mapped_column(String)
    area: Mapped[str] = mapped_column(String)
    fecha: Mapped[date_type] = mapped_column(Date, index=True)
    completada: Mapped[bool] = mapped_column(Boolean, default=False)
    url_evidencia: Mapped[str | None] = mapped_column(String, nullable=True)
    completada_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FotoVocero(Base):
    """Fotografía de inspección subida por un Vocero (límite estricto de 30 fotos por mes)."""

    __tablename__ = "fotos_voceros"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    periodo: Mapped[str] = mapped_column(String(7), index=True)
    area: Mapped[str] = mapped_column(String, index=True)
    comentario: Mapped[str] = mapped_column(String)
    url_foto: Mapped[str] = mapped_column(String)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BitacoraActa(Base):
    """Acta o minuta oficial de reunión registrada por el Secretario."""

    __tablename__ = "bitacora_actas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    fecha: Mapped[date_type] = mapped_column(Date, index=True)
    hora: Mapped[str] = mapped_column(String)
    ubicacion: Mapped[str] = mapped_column(String)
    contenido: Mapped[str] = mapped_column(String)
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Comunicado(Base):
    """Comunicado oficial publicado en el carrusel del Dashboard."""

    __tablename__ = "comunicados"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String)
    contenido: Mapped[str] = mapped_column(String)
    enlace_externo: Mapped[str | None] = mapped_column(String, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FondoCondominio(Base):
    """Fondo patrimonial del condominio (Reserva Legal, Caja Chica o Especial) — Hito 10."""

    __tablename__ = "fondos_condominio"
    __table_args__ = (
        UniqueConstraint("condominio_id", "nombre", name="uq_fondo_condominio_nombre"),
        CheckConstraint("porcentaje_recargo >= 0 AND porcentaje_recargo <= 100", name="ck_fondos_recargo_rango"),
        CheckConstraint("saldo_actual_usd >= 0", name="ck_fondos_saldo_no_neg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), index=True)
    tipo: Mapped[str] = mapped_column(String(30), default="RESERVA_LEGAL")
    porcentaje_recargo: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"))
    saldo_actual_usd: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    es_activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReciboItem(Base):
    """Línea de desglose contable dentro de un Recibo emitido — Hito 10."""

    __tablename__ = "recibos_items"
    __table_args__ = (
        CheckConstraint(
            "(tipo_item = 'ABONO_CREDITO_PREVIO' AND monto_usd <= 0) OR monto_usd >= 0",
            name="ck_recibos_items_monto_valido",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    recibo_id: Mapped[int] = mapped_column(ForeignKey("recibos.id", ondelete="CASCADE"), index=True)
    tipo_item: Mapped[str] = mapped_column(String(30))
    descripcion: Mapped[str] = mapped_column(String(255))
    monto_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CertificadoSolvencia(Base):
    """Certificado digital de solvencia de condominio firmado con HMAC-SHA256 — Hito 10."""

    __tablename__ = "certificados_solvencia"
    __table_args__ = (
        UniqueConstraint("condominio_id", "folio", name="uq_certificado_solvencia_condominio_folio"),
        CheckConstraint("deuda_verificada_usd >= 0", name="ck_solvencia_deuda_no_neg"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    jti: Mapped[str] = mapped_column(
        String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False
    )
    folio: Mapped[str] = mapped_column(String(40), index=True)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True)
    emitido_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    fecha_emision: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_vencimiento: Mapped[date_type] = mapped_column(Date, nullable=False)
    deuda_verificada_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    firma_hmac: Mapped[str] = mapped_column(String(64), nullable=False)


class ConsultaComunitaria(Base):
    """Carta Consulta escrita (Art. 23 LPH) o Asamblea de Copropietarios (Art. 24 LPH) — Hito 11."""

    __tablename__ = "consultas_comunitarias"
    __table_args__ = (
        CheckConstraint(
            "quorum_minimo_alicuota >= 0 AND quorum_minimo_alicuota <= 100",
            name="ck_consultas_quorum_rango",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    descripcion_legal: Mapped[str] = mapped_column(String, nullable=False)
    tipo_consulta: Mapped[str] = mapped_column(String(30), default="CARTA_CONSULTA_1RA")
    regla_quorum: Mapped[str] = mapped_column(String(30), default="DOS_TERCIOS")
    quorum_minimo_alicuota: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("66.6667"))
    fecha_apertura: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_cierre: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="ABIERTA", index=True)
    creada_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    acta_bitacora_id: Mapped[int | None] = mapped_column(
        ForeignKey("bitacora_actas.id"), nullable=True, default=None, index=True
    )

    opciones: Mapped[list["OpcionConsulta"]] = relationship(
        "OpcionConsulta",
        order_by="OpcionConsulta.id.asc()",
        lazy="selectin",
    )
    votos: Mapped[list["VotoConsulta"]] = relationship(
        "VotoConsulta",
        order_by="VotoConsulta.id.asc()",
        lazy="selectin",
    )


class OpcionConsulta(Base):
    """Opción seleccionable dentro de una Carta Consulta o Asamblea — Hito 11."""

    __tablename__ = "opciones_consulta"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    consulta_id: Mapped[int] = mapped_column(ForeignKey("consultas_comunitarias.id", ondelete="CASCADE"), index=True)
    etiqueta: Mapped[str] = mapped_column(String(120), nullable=False)
    es_opcion_aprobatoria: Mapped[bool] = mapped_column(Boolean, default=False)


class VotoConsulta(Base):
    """Voto inmutable WORM de una unidad inmobiliaria ponderado por su alícuota y firmado con HMAC-SHA256."""

    __tablename__ = "votos_consulta"
    __table_args__ = (
        UniqueConstraint("condominio_id", "consulta_id", "unidad_id", name="uq_voto_consulta_unidad"),
        CheckConstraint(
            "alicuota_capturada >= 0 AND alicuota_capturada <= 100",
            name="ck_votos_alicuota_rango",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    jti: Mapped[str] = mapped_column(
        String(36), default=lambda: str(uuid.uuid4()), unique=True, index=True, nullable=False
    )
    consulta_id: Mapped[int] = mapped_column(ForeignKey("consultas_comunitarias.id"), index=True)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    opcion_id: Mapped[int] = mapped_column(ForeignKey("opciones_consulta.id"), index=True)
    alicuota_capturada: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    fecha_voto: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    firma_hmac: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), default="0" * 64, server_default="0" * 64, nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), default="", server_default="", nullable=False)


class PaseVisita(Base):
    """Pase de acceso peatonal/vehicular con token QR firmado con HMAC-SHA256 y nonce jti anti-replay — Hito 12."""

    __tablename__ = "pases_visita"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True, nullable=False)
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    nombre_visitante: Mapped[str] = mapped_column(String(120), nullable=False)
    cedula_visitante: Mapped[str] = mapped_column(String(25), nullable=False)
    placa_vehiculo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    modalidad: Mapped[str] = mapped_column(String(20), default="UNICO_USO", nullable=False)
    valido_desde: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valido_hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVO", index=True, nullable=False)
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verificado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True, index=True)
    firma_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaqueteRecibido(Base):
    """Encomienda o paquete recepcionado en garita/conserjería con cadena de custodia — Hito 12."""

    __tablename__ = "paquetes_recibidos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True, nullable=False)
    recibido_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    empresa_envio: Mapped[str] = mapped_column(String(60), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    url_foto_evidencia: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="EN_GARITA", index=True, nullable=False)
    fecha_recepcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_entrega: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retirado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True, index=True)


class AreaSocial(Base):
    """Área común recreativa reservable (Salón de Fiestas, Parrillera, Caney, Cancha) — Hito 13."""

    __tablename__ = "areas_sociales"
    __table_args__ = (
        UniqueConstraint("condominio_id", "nombre", name="uq_area_social_condominio_nombre"),
        CheckConstraint(
            "aforo_maximo > 0 AND costo_uso_usd >= 0 AND deposito_garantia_usd >= 0",
            name="ck_areas_sociales_valores",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    aforo_maximo: Mapped[int] = mapped_column(Integer, nullable=False)
    costo_uso_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    deposito_garantia_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    requiere_solvencia_estricta: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    es_activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ReservaAreaSocial(Base):
    """Reserva exclusiva por fecha de un área social con vínculo a inspección post-evento — Hito 13."""

    __tablename__ = "reservas_areas_sociales"
    __table_args__ = (
        Index(
            "uq_reserva_area_fecha_activa",
            "condominio_id",
            "area_id",
            "fecha_evento",
            unique=True,
            postgresql_where=text("estado != 'CANCELADA'"),
            sqlite_where=text("estado != 'CANCELADA'"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    condominio_id: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False, index=True)
    area_id: Mapped[int] = mapped_column(ForeignKey("areas_sociales.id"), index=True, nullable=False)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True, nullable=False)
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    fecha_evento: Mapped[date_type] = mapped_column(Date, index=True, nullable=False)
    motivo_evento: Mapped[str] = mapped_column(String(160), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="CONFIRMADA", index=True, nullable=False)
    tarea_inspeccion_id: Mapped[int | None] = mapped_column(ForeignKey("tareas_diarias.id"), nullable=True, index=True)
    observaciones_inspeccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
