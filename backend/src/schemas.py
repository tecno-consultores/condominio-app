from datetime import date as date_type
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UsuarioBase(BaseModel):
    nombre: str
    cedula: str
    correo: EmailStr
    telefono: str


class UsuarioCreate(UsuarioBase):
    password: str
    unidad_solicitada_id: int
    tipo_ocupante_solicitado: str


class UsuarioResponse(UsuarioBase):
    id: int
    es_activo: bool
    rol: str

    model_config = ConfigDict(from_attributes=True)


Moneda = Literal["USD", "VES"]


class TasaCambioCreate(BaseModel):
    fecha: date_type | None = None
    tasa_usd_ves: Decimal = Field(gt=0)


class TasaCambioResponse(BaseModel):
    fecha: date_type
    tasa_usd_ves: Decimal

    model_config = ConfigDict(from_attributes=True)


class ReciboCreate(BaseModel):
    unidad_id: int
    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
    monto_usd: Decimal = Field(gt=0)


class ReciboResponse(BaseModel):
    id: int
    unidad_id: int
    periodo: str
    monto_usd: Decimal
    monto_pagado_usd: Decimal
    estado: str
    bloqueado: bool

    model_config = ConfigDict(from_attributes=True)


class PagoReportar(BaseModel):
    recibo_id: int
    monto: Decimal = Field(gt=0)
    moneda: Moneda
    metodo_pago: str
    numero_referencia: str | None = None
    url_comprobante: str | None = None


class PagoResponse(BaseModel):
    id: int
    recibo_id: int
    usuario_id: int
    monto: Decimal
    moneda: str
    monto_usd: Decimal
    tasa_cambio: Decimal
    metodo_pago: str
    numero_referencia: str | None
    estado: str

    model_config = ConfigDict(from_attributes=True)


class PagoRechazo(BaseModel):
    motivo: str = Field(min_length=1)


class EgresoCreate(BaseModel):
    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
    categoria: str = Field(min_length=1)
    descripcion: str = Field(min_length=1)
    monto: Decimal = Field(gt=0)
    moneda: Moneda
    url_factura: str | None = None


class CierreMensualRequest(BaseModel):
    periodo: str = Field(pattern=r"^\d{4}-\d{2}$")
