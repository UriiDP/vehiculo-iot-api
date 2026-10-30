from pydantic import BaseModel, Field
from typing import Optional

class Estado(BaseModel):
    status: bool

class MovimientoRequest(BaseModel):
    id_vehiculo: int = Field(default=1, example=1, description="ID del vehículo")
    id_comando: int = Field(..., example=11, description="ID del comando (11 al 21)")
    origen: str = Field(default="SWAGGER_UI", example="SWAGGER_UI", description="Origen de la petición")