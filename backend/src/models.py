from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.sql import func
from src.database import Base

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, index=True)
    cedula = Column(String, unique=True, index=True)
    correo = Column(String, unique=True, index=True)
    telefono = Column(String)
    password_hash = Column(String, nullable=False)
    es_activo = Column(Boolean, default=False)  # Usuario Fantasma = False
    rol = Column(String, default="FANTASMA")

class Estructura(Base):
    __tablename__ = "estructuras"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String)
    tipo = Column(String)

class Unidad(Base):
    __tablename__ = "unidades"
    id = Column(Integer, primary_key=True, index=True)
    identificador = Column(String, unique=True, index=True)
    estructura_id = Column(Integer, ForeignKey("estructuras.id"))

class ContratoOcupacion(Base):
    __tablename__ = "contratos_ocupacion"
    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    unidad_id = Column(Integer, ForeignKey("unidades.id"))
    tipo_ocupante = Column(String)  # PROPIETARIO o INQUILINO
    es_activo = Column(Boolean, default=False)
    fecha_inicio = Column(DateTime(timezone=True), server_default=func.now())
    fecha_fin = Column(DateTime(timezone=True), nullable=True)