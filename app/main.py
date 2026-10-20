import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from app.models.estado import (
    MovimientoIndividualRequest,
    VehiculoCreate, VehiculoUpdate,
    ComandoCreate, ComandoUpdate,
    DemoCreate, DemoUpdate,
    MovimientoDemoCreate, MovimientoDemoUpdate
)
from app.services.status_service import IoTService
from app.websocket.websocket_manager import websocket_manager  # <-- CORREGIDO: Importa websocket_manager

app = FastAPI(
    title="API Vehículo IoT",
    description="API HTTP y WebSocket con Amazon RDS - Práctica 2.5",
    version="1.0.0"
)

# --- CONFIGURACIÓN DE CORS (PERMITE CONEXIONES DESDE CLIENTES Y EXTENSIONES) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Función auxiliar para convertir datetimes a string ISO al serializar JSON por WebSocket
def serializar_json_seguro(obj):
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

# Control de ejecuciones DEMO en curso por vehículo (Evita concurrencia)
demos_en_ejecucion = set()

# =========================================================================
# 1. VEHÍCULOS (sp_crear, sp_obtener, sp_actualizar, sp_eliminar)
# =========================================================================
@app.get("/vehiculos", tags=["Vehículos"], summary="Obtener todos los vehículos (sp_obtener_vehiculos)")
def listar_vehiculos():
    return IoTService.sp_obtener_vehiculos()

@app.get("/vehiculos/{id_vehiculo}", tags=["Vehículos"], summary="Obtener vehículo por ID (sp_obtener_vehiculo)")
def obtener_vehiculo(id_vehiculo: int):
    v = IoTService.sp_obtener_vehiculo(id_vehiculo)
    if not v:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return v

@app.post("/vehiculos", tags=["Vehículos"], summary="Crear vehículo (sp_crear_vehiculo)")
def crear_vehiculo(req: VehiculoCreate):
    return IoTService.sp_crear_vehiculo(req.nombre, req.modelo, req.descripcion, req.microcontrolador)

@app.put("/vehiculos/{id_vehiculo}", tags=["Vehículos"], summary="Actualizar vehículo (sp_actualizar_vehiculo)")
def actualizar_vehiculo(id_vehiculo: int, req: VehiculoUpdate):
    return IoTService.sp_actualizar_vehiculo(id_vehiculo, req.nombre, req.modelo, req.descripcion, req.microcontrolador, req.activo)

@app.delete("/vehiculos/{id_vehiculo}", tags=["Vehículos"], summary="Eliminar vehículo (sp_eliminar_vehiculo)")
def eliminar_vehiculo(id_vehiculo: int):
    return IoTService.sp_eliminar_vehiculo(id_vehiculo)

# =========================================================================
# 2. COMANDOS (sp_crear, sp_obtener, sp_actualizar, sp_eliminar)
# =========================================================================
@app.get("/vehiculos/{id_vehiculo}/comandos", tags=["Comandos"], summary="Listar comandos de un vehículo (sp_obtener_comandos_vehiculo)")
def listar_comandos(id_vehiculo: int):
    return IoTService.sp_obtener_comandos_vehiculo(id_vehiculo)

@app.post("/comandos", tags=["Comandos"], summary="Crear comando (sp_crear_comando)")
def crear_comando(req: ComandoCreate):
    return IoTService.sp_crear_comando(req.id_vehiculo, req.nombre, req.codigo, req.descripcion)

@app.put("/comandos/{id_comando}", tags=["Comandos"], summary="Actualizar comando (sp_actualizar_comando)")
def actualizar_comando(id_comando: int, req: ComandoUpdate):
    return IoTService.sp_actualizar_comando(id_comando, req.nombre, req.codigo, req.descripcion, req.activo)

@app.delete("/comandos/{id_comando}", tags=["Comandos"], summary="Eliminar comando (sp_eliminar_comando)")
def eliminar_comando(id_comando: int):
    return IoTService.sp_eliminar_comando(id_comando)

# =========================================================================
# 3. ESTADO E HISTORIAL (sp_obtener_estado, sp_obtener_historial)
# =========================================================================
@app.get("/vehiculos/{id_vehiculo}/estado", tags=["Estado"], summary="Consultar último estado (sp_obtener_estado)")
def consultar_estado(id_vehiculo: int):
    e = IoTService.sp_obtener_estado(id_vehiculo)
    if not e:
        raise HTTPException(status_code=404, detail="Estado no encontrado")
    return e

@app.get("/vehiculos/{id_vehiculo}/historial", tags=["Historial"], summary="Consultar historial (MÁXIMO 10 registros)")
def consultar_historial(id_vehiculo: int):
    # Cumple el requisito: máximo 10 registros más recientes
    return IoTService.obtener_historial_limitado(id_vehiculo)

# =========================================================================
# 4. ACCIÓN CONTROL: MOVIMIENTO INDIVIDUAL (POST)
# Transacción Atómica: sp_actualizar_estado + sp_registrar_historial + WS
# =========================================================================
@app.post("/vehiculos/movimiento", tags=["Acciones Control"], summary="Registrar movimiento individual en RDS + WebSocket")
async def registrar_movimiento_individual(req: MovimientoIndividualRequest):
    vehiculo = IoTService.sp_obtener_vehiculo(req.id_vehiculo)
    if not vehiculo:
        raise HTTPException(status_code=404, detail="El vehículo especificado no existe")

    comandos = IoTService.sp_obtener_comandos_vehiculo(req.id_vehiculo)
    comando_valido = next((c for c in comandos if c['id_comando'] == req.id_comando), None)
    if not comando_valido:
        raise HTTPException(status_code=400, detail="El comando no pertenece a este vehículo")

    try:
        IoTService.registrar_movimiento_individual(req.id_vehiculo, req.id_comando, req.origen)

        mensaje_ws = {
            "evento": "MOVIMIENTO_INDIVIDUAL",
            "id_vehiculo": req.id_vehiculo,
            "id_comando": req.id_comando,
            "origen": req.origen,
            "timestamp": datetime.now().isoformat()
        }
        await websocket_manager.broadcast_to_vehicle(req.id_vehiculo, mensaje_ws)

        return {"status": "success", "message": "Movimiento individual registrado correctamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================================================================
# 5. DEMO Y MOVIMIENTOS DEMO (CRUD 8 SPs)
# =========================================================================
@app.get("/vehiculos/{id_vehiculo}/demos", tags=["DEMO"], summary="Obtener DEMOs del vehículo (sp_obtener_demos)")
def listar_demos(id_vehiculo: int):
    return IoTService.sp_obtener_demos(id_vehiculo)

@app.post("/demos", tags=["DEMO"], summary="Crear DEMO (sp_crear_demo)")
def crear_demo(req: DemoCreate):
    return IoTService.sp_crear_demo(req.id_vehiculo, req.nombre, req.descripcion)

@app.put("/demos/{id_demo}", tags=["DEMO"], summary="Actualizar DEMO (sp_actualizar_demo)")
def actualizar_demo(id_demo: int, req: DemoUpdate):
    return IoTService.sp_actualizar_demo(id_demo, req.nombre, req.descripcion, req.activo)

@app.delete("/demos/{id_demo}", tags=["DEMO"], summary="Eliminar DEMO (sp_eliminar_demo)")
def eliminar_demo(id_demo: int):
    return IoTService.sp_eliminar_demo(id_demo)

@app.get("/demos/{id_demo}/movimientos", tags=["DEMO Movimientos"], summary="Obtener movimientos de la DEMO (sp_obtener_movimientos_demo)")
def listar_movimientos_demo(id_demo: int):
    return IoTService.sp_obtener_movimientos_demo(id_demo)

@app.post("/demos/movimientos", tags=["DEMO Movimientos"], summary="Agregar movimiento a DEMO (sp_agregar_movimiento_demo)")
def agregar_movimiento_demo(req: MovimientoDemoCreate):
    return IoTService.sp_agregar_movimiento_demo(req.id_demo, req.id_comando, req.orden, req.duracion_ms, req.pausa_ms)

@app.put("/demos/movimientos/{id_demo_movimiento}", tags=["DEMO Movimientos"], summary="Actualizar movimiento de DEMO (sp_actualizar_movimiento_demo)")
def actualizar_movimiento_demo(id_demo_movimiento: int, req: MovimientoDemoUpdate):
    return IoTService.sp_actualizar_movimiento_demo(id_demo_movimiento, req.id_comando, req.orden, req.duracion_ms, req.pausa_ms)

@app.delete("/demos/movimientos/{id_demo_movimiento}", tags=["DEMO Movimientos"], summary="Eliminar movimiento de DEMO (sp_eliminar_movimiento_demo)")
def eliminar_movimiento_demo(id_demo_movimiento: int):
    return IoTService.sp_eliminar_movimiento_demo(id_demo_movimiento)

# =========================================================================
# 6. ACCIÓN CONTROL: EJECUCIÓN DE DEMO POR WEBSOCKET (SIN HISTORIAL)
# =========================================================================
@app.post("/demos/{id_demo}/ejecutar", tags=["Acciones Control"], summary="Ejecutar DEMO por WebSocket sin historial")
async def ejecutar_demo(id_demo: int, id_vehiculo: int = Query(...)):
    if id_vehiculo in demos_en_ejecucion:
        raise HTTPException(status_code=409, detail="Ya hay una DEMO ejecutándose en este vehículo")

    movimientos = IoTService.sp_obtener_movimientos_demo(id_demo)
    if not movimientos:
        raise HTTPException(status_code=404, detail="La DEMO no contiene movimientos")

    demos_en_ejecucion.add(id_vehiculo)

    try:
        await websocket_manager.broadcast_to_vehicle(id_vehiculo, {
            "evento": "INICIO_DEMO",
            "id_demo": id_demo,
            "id_vehiculo": id_vehiculo,
            "timestamp": datetime.now().isoformat()
        })

        for mov in movimientos:
            cmd_id = mov['id_comando']
            duracion_sec = mov['duracion_ms'] / 1000.0
            pausa_sec = mov['pausa_ms'] / 1000.0

            # Actualiza estado SIN guardar en historial
            IoTService.sp_actualizar_estado(id_vehiculo, cmd_id, True)

            await websocket_manager.broadcast_to_vehicle(id_vehiculo, {
                "evento": "MOVIMIENTO_DEMO",
                "id_vehiculo": id_vehiculo,
                "id_comando": cmd_id,
                "orden": mov['orden'],
                "duracion_ms": mov['duracion_ms'],
                "pausa_ms": mov['pausa_ms'],
                "timestamp": datetime.now().isoformat()
            })

            await asyncio.sleep(duracion_sec)
            if pausa_sec > 0:
                await asyncio.sleep(pausa_sec)

        await websocket_manager.broadcast_to_vehicle(id_vehiculo, {
            "evento": "FIN_DEMO",
            "id_demo": id_demo,
            "id_vehiculo": id_vehiculo,
            "timestamp": datetime.now().isoformat()
        })

        return {"status": "success", "message": "DEMO ejecutada exitosamente"}
    finally:
        demos_en_ejecucion.discard(id_vehiculo)

# =========================================================================
# 7. WEBSOCKET ENDPOINT
# =========================================================================
@app.websocket("/ws/{id_vehiculo}")
async def websocket_endpoint(websocket: WebSocket, id_vehiculo: int):
    await websocket_manager.connect(websocket, id_vehiculo)
    try:
        # Obtener el último estado en RDS
        estado_raw = IoTService.ejecutar_sp_lectura('sp_obtener_estado', (id_vehiculo,))
        if estado_raw:
            # Convertimos el diccionario a JSON usando el serializador seguro de datetime
            datos_limpios = json.loads(json.dumps(estado_raw[0], default=serializar_json_seguro))
            await websocket.send_json({
                "evento": "ESTADO_INICIAL",
                "id_vehiculo": id_vehiculo,
                "datos": datos_limpios,
                "timestamp": datetime.now().isoformat()
            })
        
        while True:
            await websocket.receive_text()  # Mantener la conexión viva
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket, id_vehiculo)