from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from src.database import Base


class Usuario(Base):
    __tablename__ = "usuarios"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String, index=True)
    cedula: Mapped[str] = mapped_column(String, unique=True, index=True)
    correo: Mapped[str] = mapped_column(String, unique=True, index=True)
    telefono: Mapped[str] = mapped_column(String)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    es_activo: Mapped[bool] = mapped_column(Boolean, default=False)
    rol: Mapped[str] = mapped_column(String, default="FANTASMA")


class Estructura(Base):
    __tablename__ = "estructuras"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String)
    tipo: Mapped[str] = mapped_column(String)


class Unidad(Base):
    __tablename__ = "unidades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    identificador: Mapped[str] = mapped_column(String, unique=True, index=True)
    estructura_id: Mapped[int] = mapped_column(ForeignKey("estructuras.id"))
    alicuota: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("0.0000"), server_default="0.0000")
    cuota_fija_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True, default=None)
    credito_disponible_usd: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("0.00"), server_default="0.00"
    )


class ContratoOcupacion(Base):
    __tablename__ = "contratos_ocupacion"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"))
    tipo_ocupante: Mapped[str] = mapped_column(String)
    es_activo: Mapped[bool] = mapped_column(Boolean, default=False)
    puede_votar_asamblea: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    fecha_inicio: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_fin: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TasaCambio(Base):
    """Tasa de cambio USD/VES registrada por día (USD es la moneda base contable)."""

    __tablename__ = "tasas_cambio"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped[date_type] = mapped_column(Date, unique=True, index=True)
    tasa_usd_ves: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Recibo(Base):
    """Recibo de cobranza de una unidad para un periodo (formato YYYY-MM)."""

    __tablename__ = "recibos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"))
    periodo: Mapped[str] = mapped_column(String(7), index=True)
    monto_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    monto_pagado_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    estado: Mapped[str] = mapped_column(String, default="PENDIENTE")
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PagoReportado(Base):
    """Pago reportado por un propietario. Guarda la tasa del día exacto del reporte."""

    __tablename__ = "pagos_reportados"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recibo_id: Mapped[int] = mapped_column(ForeignKey("recibos.id"))
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
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
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    periodo: Mapped[str] = mapped_column(String(7), index=True)
    categoria: Mapped[str] = mapped_column(String)
    descripcion: Mapped[str] = mapped_column(String)
    monto: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3))
    monto_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tasa_cambio: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    url_factura: Mapped[str | None] = mapped_column(String, nullable=True)
    incidencia_id: Mapped[int | None] = mapped_column(ForeignKey("incidencias.id"), nullable=True, default=None)
    es_gasto_comun: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    bloqueado: Mapped[bool] = mapped_column(Boolean, default=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditoriaRecibo(Base):
    """Pista de auditoría inmutable: quién, cuándo, estado viejo/nuevo y motivo."""

    __tablename__ = "auditoria_recibos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recibo_id: Mapped[int] = mapped_column(ForeignKey("recibos.id"), index=True)
    pago_id: Mapped[int | None] = mapped_column(ForeignKey("pagos_reportados.id"), nullable=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    estado_viejo: Mapped[str] = mapped_column(String)
    estado_nuevo: Mapped[str] = mapped_column(String)
    motivo: Mapped[str | None] = mapped_column(String, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReporteMensual(Base):
    """Reporte financiero mensual. El cierre es una acción inmutable (Candado Contable)."""

    __tablename__ = "reportes_mensuales"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    periodo: Mapped[str] = mapped_column(String(7), unique=True, index=True)
    estado: Mapped[str] = mapped_column(String, default="PRELIMINAR")
    url_pdf: Mapped[str | None] = mapped_column(String, nullable=True)
    cerrado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Incidencia(Base):
    """Incidencia comunitaria reportada en el embudo vecinal con soporte de adhesión ('Me sumo')."""

    __tablename__ = "incidencias"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
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
    __table_args__ = (UniqueConstraint("incidencia_id", "usuario_id", name="uq_incidencia_usuario_adhesion"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    incidencia_id: Mapped[int] = mapped_column(ForeignKey("incidencias.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PlantillaTarea(Base):
    """Plantilla recurrente de mantenimiento/conserjería definida por el Presidente."""

    __tablename__ = "plantillas_tareas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String)
    area: Mapped[str] = mapped_column(String)
    frecuencia: Mapped[str] = mapped_column(String, default="DIARIA")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class TareaDiaria(Base):
    """Tarea diaria asignada al conserje (generada desde plantilla o vinculada a una incidencia)."""

    __tablename__ = "tareas_diarias"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    plantilla_id: Mapped[int | None] = mapped_column(ForeignKey("plantillas_tareas.id"), nullable=True)
    incidencia_id: Mapped[int | None] = mapped_column(ForeignKey("incidencias.id"), nullable=True)
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
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    periodo: Mapped[str] = mapped_column(String(7), index=True)
    area: Mapped[str] = mapped_column(String, index=True)
    comentario: Mapped[str] = mapped_column(String)
    url_foto: Mapped[str] = mapped_column(String)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class BitacoraActa(Base):
    """Acta o minuta oficial de reunión registrada por el Secretario."""

    __tablename__ = "bitacora_actas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    fecha: Mapped[date_type] = mapped_column(Date, index=True)
    hora: Mapped[str] = mapped_column(String)
    ubicacion: Mapped[str] = mapped_column(String)
    contenido: Mapped[str] = mapped_column(String)
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Comunicado(Base):
    """Comunicado oficial publicado en el carrusel del Dashboard."""

    __tablename__ = "comunicados"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String)
    contenido: Mapped[str] = mapped_column(String)
    enlace_externo: Mapped[str | None] = mapped_column(String, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class FondoCondominio(Base):
    """Fondo patrimonial del condominio (Reserva Legal, Caja Chica o Especial) — Hito 10."""

    __tablename__ = "fondos_condominio"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    tipo: Mapped[str] = mapped_column(String(30), default="RESERVA_LEGAL")
    porcentaje_recargo: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"))
    saldo_actual_usd: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=Decimal("0.00"))
    es_activo: Mapped[bool] = mapped_column(Boolean, default=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ReciboItem(Base):
    """Línea de desglose contable dentro de un Recibo emitido — Hito 10."""

    __tablename__ = "recibos_items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    recibo_id: Mapped[int] = mapped_column(ForeignKey("recibos.id", ondelete="CASCADE"), index=True)
    tipo_item: Mapped[str] = mapped_column(String(30))
    descripcion: Mapped[str] = mapped_column(String(255))
    monto_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CertificadoSolvencia(Base):
    """Certificado digital de solvencia de condominio firmado con HMAC-SHA256 — Hito 10."""

    __tablename__ = "certificados_solvencia"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    folio: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True)
    emitido_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    fecha_emision: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_vencimiento: Mapped[date_type] = mapped_column(Date, nullable=False)
    deuda_verificada_usd: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    firma_hmac: Mapped[str] = mapped_column(String(64), nullable=False)


class ConsultaComunitaria(Base):
    """Carta Consulta escrita (Art. 23 LPH) o Asamblea de Copropietarios (Art. 24 LPH) — Hito 11."""

    __tablename__ = "consultas_comunitarias"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    titulo: Mapped[str] = mapped_column(String(160), nullable=False)
    descripcion_legal: Mapped[str] = mapped_column(String, nullable=False)
    tipo_consulta: Mapped[str] = mapped_column(String(30), default="CARTA_CONSULTA_1RA")
    regla_quorum: Mapped[str] = mapped_column(String(30), default="DOS_TERCIOS")
    quorum_minimo_alicuota: Mapped[Decimal] = mapped_column(Numeric(7, 4), default=Decimal("66.6700"))
    fecha_apertura: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    fecha_cierre: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="ABIERTA", index=True)
    creada_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    acta_bitacora_id: Mapped[int | None] = mapped_column(ForeignKey("bitacora_actas.id"), nullable=True, default=None)


class OpcionConsulta(Base):
    """Opción seleccionable dentro de una Carta Consulta o Asamblea — Hito 11."""

    __tablename__ = "opciones_consulta"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    consulta_id: Mapped[int] = mapped_column(ForeignKey("consultas_comunitarias.id", ondelete="CASCADE"), index=True)
    etiqueta: Mapped[str] = mapped_column(String(120), nullable=False)
    es_opcion_aprobatoria: Mapped[bool] = mapped_column(Boolean, default=False)


class VotoConsulta(Base):
    """Voto inmutable de una unidad inmobiliaria ponderado por su alícuota y firmado con HMAC-SHA256 — Hito 11."""

    __tablename__ = "votos_consulta"
    __table_args__ = (UniqueConstraint("consulta_id", "unidad_id", name="uq_voto_consulta_unidad"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    consulta_id: Mapped[int] = mapped_column(ForeignKey("consultas_comunitarias.id"), index=True)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), index=True)
    opcion_id: Mapped[int] = mapped_column(ForeignKey("opciones_consulta.id"), index=True)
    alicuota_capturada: Mapped[Decimal] = mapped_column(Numeric(7, 4), nullable=False)
    fecha_voto: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ip_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    firma_hmac: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)


class PaseVisita(Base):
    """Pase de acceso peatonal/vehicular con token QR firmado con HMAC-SHA256 y nonce jti anti-replay — Hito 12."""

    __tablename__ = "pases_visita"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    jti: Mapped[str] = mapped_column(String(36), unique=True, index=True, nullable=False)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True, nullable=False)
    creado_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    nombre_visitante: Mapped[str] = mapped_column(String(120), nullable=False)
    cedula_visitante: Mapped[str] = mapped_column(String(25), nullable=False)
    placa_vehiculo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    modalidad: Mapped[str] = mapped_column(String(20), default="UNICO_USO", nullable=False)
    valido_desde: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valido_hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), default="ACTIVO", index=True, nullable=False)
    usado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    verificado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)
    firma_hmac: Mapped[str] = mapped_column(String(64), nullable=False)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PaqueteRecibido(Base):
    """Encomienda o paquete recepcionado en garita/conserjería con cadena de custodia — Hito 12."""

    __tablename__ = "paquetes_recibidos"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True, nullable=False)
    recibido_por_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    empresa_envio: Mapped[str] = mapped_column(String(60), nullable=False)
    descripcion: Mapped[str] = mapped_column(String(200), nullable=False)
    url_foto_evidencia: Mapped[str | None] = mapped_column(String(500), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="EN_GARITA", index=True, nullable=False)
    fecha_recepcion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    fecha_entrega: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retirado_por_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"), nullable=True)


class AreaSocial(Base):
    """Área común recreativa reservable (Salón de Fiestas, Parrillera, Caney, Cancha) — Hito 13."""

    __tablename__ = "areas_sociales"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nombre: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    aforo_maximo: Mapped[int] = mapped_column(Integer, nullable=False)
    costo_uso_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    deposito_garantia_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    requiere_solvencia_estricta: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    es_activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ReservaAreaSocial(Base):
    """Reserva exclusiva por fecha de un área social con vínculo a inspección post-evento — Hito 13."""

    __tablename__ = "reservas_areas_sociales"
    __table_args__ = (UniqueConstraint("area_id", "fecha_evento", name="uq_reserva_area_fecha"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    area_id: Mapped[int] = mapped_column(ForeignKey("areas_sociales.id"), index=True, nullable=False)
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"), index=True, nullable=False)
    solicitante_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    fecha_evento: Mapped[date_type] = mapped_column(Date, index=True, nullable=False)
    motivo_evento: Mapped[str] = mapped_column(String(160), nullable=False)
    estado: Mapped[str] = mapped_column(String(30), default="CONFIRMADA", index=True, nullable=False)
    tarea_inspeccion_id: Mapped[int | None] = mapped_column(ForeignKey("tareas_diarias.id"), nullable=True)
    observaciones_inspeccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
