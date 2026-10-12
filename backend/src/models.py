from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
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
