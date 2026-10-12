from datetime import date as date_type
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String
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


class ContratoOcupacion(Base):
    __tablename__ = "contratos_ocupacion"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    unidad_id: Mapped[int] = mapped_column(ForeignKey("unidades.id"))
    tipo_ocupante: Mapped[str] = mapped_column(String)
    es_activo: Mapped[bool] = mapped_column(Boolean, default=False)
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
