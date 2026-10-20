from pydantic import BaseModel, Field
from typing import Optional

# Movimiento Individual (POST)
class MovimientoIndividualRequest(BaseModel):
    id_vehiculo: int
    id_comando: int
    origen: Optional[str] = "ThunderClient"

# Vehículos
class VehiculoCreate(BaseModel):
    nombre: str = Field(..., max_length=80)
    modelo: Optional[str] = Field(None, max_length=80)
    descripcion: Optional[str] = Field(None, max_length=255)
    microcontrolador: Optional[str] = Field(None, max_length=50)

class VehiculoUpdate(VehiculoCreate):
    activo: bool

# Comandos
class ComandoCreate(BaseModel):
    id_vehiculo: int
    nombre: str = Field(..., max_length=60)
    codigo: int
    descripcion: Optional[str] = Field(None, max_length=255)

class ComandoUpdate(BaseModel):
    nombre: str
    codigo: int
    descripcion: Optional[str]
    activo: bool

# Demos
class DemoCreate(BaseModel):
    id_vehiculo: int
    nombre: str = Field(..., max_length=80)
    descripcion: Optional[str] = Field(None, max_length=255)

class DemoUpdate(BaseModel):
    nombre: str
    descripcion: Optional[str]
    activo: bool

# Movimientos Demo
class MovimientoDemoCreate(BaseModel):
    id_demo: int
    id_comando: int
    orden: int
    duracion_ms: int
    pausa_ms: int = 0

class MovimientoDemoUpdate(BaseModel):
    id_comando: int
    orden: int
    duracion_ms: int
    pausa_ms: int