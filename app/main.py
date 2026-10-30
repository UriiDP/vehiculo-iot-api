import os
import asyncio
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html

from app.models.estado import Estado, MovimientoRequest
from app.services.status_service import StatusService
from app.websocket.websocket_manager import WebSocketManager

# Inicializamos FastAPI desactivando el docs_url por defecto para personalizarlo
app = FastAPI(
    title="API Vehículo IoT",
    description="""
### 🚘 Servidor IoT - Control de Excavadora RC
API HTTP y WebSocket con Amazon RDS - Práctica 2.5

[📱 ABRIR PANEL DE CONTROL REMOTO (PC / CELULAR)](/control-panel)
""",
    version="1.0.0",
    docs_url=None  # Desactivado para usar nuestro Swagger UI personalizado
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Montar carpeta de archivos estáticos
static_path = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")

status_service = StatusService()
websocket_manager = WebSocketManager()

# ============================================================================
# SWAGGER UI PERSONALIZADO CON BOTÓN DESTACADO AMARILLO
# ============================================================================
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    html_response = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title="API Vehículo IoT - Swagger UI"
    )
    
    # Inyectamos estilos CSS para convertir el enlace en un Botón Amarillo 3D
    custom_styles_and_scripts = """
    <style>
        .swagger-ui .description a[href*="control-panel"] {
            display: inline-block !important;
            background: linear-gradient(135deg, #ffb703 0%, #fb8500 100%) !important;
            color: #000000 !important;
            font-weight: 800 !important;
            font-size: 15px !important;
            padding: 12px 24px !important;
            border-radius: 8px !important;
            text-decoration: none !important;
            box-shadow: 0 4px 12px rgba(251, 133, 0, 0.4) !important;
            border: 2px solid #e07a00 !important;
            margin-top: 14px !important;
            margin-bottom: 10px !important;
            transition: all 0.2s ease-in-out !important;
            cursor: pointer !important;
            font-family: sans-serif !important;
        }
        .swagger-ui .description a[href*="control-panel"]:hover {
            transform: translateY(-2px) scale(1.02) !important;
            box-shadow: 0 6px 18px rgba(251, 133, 0, 0.6) !important;
            background: linear-gradient(135deg, #ffc324 0%, #ff9100 100%) !important;
        }
    </style>
    <script>
        document.addEventListener("DOMContentLoaded", function() {
            var checkInterval = setInterval(function() {
                var btn = document.querySelector('.swagger-ui .description a[href*="control-panel"]');
                if (btn) {
                    btn.setAttribute('target', '_blank');
                    clearInterval(checkInterval);
                }
            }, 200);
        });
    </script>
    """
    
    content = html_response.body.decode("utf-8").replace("</head>", f"{custom_styles_and_scripts}</head>")
    return HTMLResponse(content=content)

# ============================================================================
# ENDPOINT DE PANEL DE CONTROL WEB
# ============================================================================
@app.get("/control-panel", response_class=HTMLResponse, include_in_schema=False)
def abrir_panel_control():
    index_file = os.path.join(static_path, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return HTMLResponse("<h2>Error: No se encontró la interfaz web en static/index.html</h2>")

# ============================================================================
# 1. SECCIÓN: VEHÍCULOS (5 SPs)
# ============================================================================
@app.get("/vehiculos", tags=["Vehículos"], summary="Obtener todos los vehículos (sp_obtener_vehiculos)")
def obtener_vehiculos():
    return {"status": "success", "sp": "sp_obtener_vehiculos", "data": []}

@app.post("/vehiculos", tags=["Vehículos"], summary="Crear vehículo (sp_crear_vehiculo)")
def crear_vehiculo():
    return {"status": "success", "sp": "sp_crear_vehiculo"}

@app.get("/vehiculos/{id_vehiculo}", tags=["Vehículos"], summary="Obtener vehículo por ID (sp_obtener_vehiculo)")
def obtener_vehiculo_id(id_vehiculo: int):
    return {"status": "success", "sp": "sp_obtener_vehiculo", "id_vehiculo": id_vehiculo}

@app.put("/vehiculos/{id_vehiculo}", tags=["Vehículos"], summary="Actualizar vehículo (sp_actualizar_vehiculo)")
def actualizar_vehiculo(id_vehiculo: int):
    return {"status": "success", "sp": "sp_actualizar_vehiculo"}

@app.delete("/vehiculos/{id_vehiculo}", tags=["Vehículos"], summary="Eliminar vehículo (sp_eliminar_vehiculo)")
def eliminar_vehiculo(id_vehiculo: int):
    return {"status": "success", "sp": "sp_eliminar_vehiculo"}

# ============================================================================
# 2. SECCIÓN: COMANDOS (4 SPs)
# ============================================================================
@app.get("/vehiculos/{id_vehiculo}/comandos", tags=["Comandos"], summary="Listar comandos de un vehículo (sp_obtener_comandos_vehiculo)")
def listar_comandos(id_vehiculo: int):
    return {"status": "success", "sp": "sp_obtener_comandos_vehiculo"}

@app.post("/comandos", tags=["Comandos"], summary="Crear comando (sp_crear_comando)")
def crear_comando():
    return {"status": "success", "sp": "sp_crear_comando"}

@app.put("/comandos/{id_comando}", tags=["Comandos"], summary="Actualizar comando (sp_actualizar_comando)")
def actualizar_comando(id_comando: int):
    return {"status": "success", "sp": "sp_actualizar_comando"}

@app.delete("/comandos/{id_comando}", tags=["Comandos"], summary="Eliminar comando (sp_eliminar_comando)")
def eliminar_comando(id_comando: int):
    return {"status": "success", "sp": "sp_eliminar_comando"}

# ============================================================================
# 3. SECCIÓN: ESTADO (2 SPs) Y ACCIONES CONTROL
# ============================================================================
@app.get("/status", tags=["Estado"], summary="Obtener Estado")
def obtener_estado():
    return status_service.obtener_estado()

@app.post("/status", tags=["Estado"], summary="Cambiar Estado")
async def cambiar_estado(estado: Estado):
    nuevo_estado = status_service.guardar_estado(estado.status)
    await websocket_manager.enviar_a_todos(nuevo_estado)
    return nuevo_estado

@app.get("/vehiculos/{id_vehiculo}/estado", tags=["Estado"], summary="Consultar último estado (sp_obtener_estado)")
def obtener_estado_vehiculo(id_vehiculo: int):
    return {"status": "success", "sp": "sp_obtener_estado"}

@app.put("/vehiculos/{id_vehiculo}/estado", tags=["Estado"], summary="Actualizar estado (sp_actualizar_estado)")
def actualizar_estado_sp(id_vehiculo: int):
    return {"status": "success", "sp": "sp_actualizar_estado"}

@app.post("/vehiculos/movimiento", tags=["Acciones Control"], summary="Registrar movimiento individual en RDS + WebSocket")
async def registrar_movimiento(movimiento: MovimientoRequest):
    mensaje = {
        "evento": "MOVIMIENTO_INDIVIDUAL",
        "id_vehiculo": movimiento.id_vehiculo,
        "id_comando": movimiento.id_comando,
        "origen": movimiento.origen
    }
    await websocket_manager.enviar_a_todos(mensaje)
    return {"status": "success", "datos": movimiento}

# ============================================================================
# 4. SECCIÓN: HISTORIAL (2 SPs)
# ============================================================================
@app.post("/historial", tags=["Historial"], summary="Registrar en historial (sp_registrar_historial)")
def registrar_historial_sp():
    return {"status": "success", "sp": "sp_registrar_historial"}

@app.get("/vehiculos/{id_vehiculo}/historial", tags=["Historial"], summary="Consultar historial (sp_obtener_historial - MÁXIMO 10 registros)")
def obtener_historial(id_vehiculo: int):
    return {"status": "success", "sp": "sp_obtener_historial", "historial": []}

# ============================================================================
# 5. SECCIÓN: DEMO (4 SPs)
# ============================================================================
@app.get("/demos", tags=["Demo"], summary="Obtener todas las DEMOs (sp_obtener_demos)")
def obtener_demos():
    return {"status": "success", "sp": "sp_obtener_demos"}

@app.post("/demos", tags=["Demo"], summary="Crear DEMO (sp_crear_demo)")
def crear_demo():
    return {"status": "success", "sp": "sp_crear_demo"}

@app.put("/demos/{id_demo}", tags=["Demo"], summary="Actualizar DEMO (sp_actualizar_demo)")
def actualizar_demo(id_demo: int):
    return {"status": "success", "sp": "sp_actualizar_demo"}

@app.delete("/demos/{id_demo}", tags=["Demo"], summary="Eliminar DEMO (sp_eliminar_demo)")
def eliminar_demo(id_demo: int):
    return {"status": "success", "sp": "sp_eliminar_demo"}

# ============================================================================
# 6. SECCIÓN: MOVIMIENTOS DEMO (4 SPs) Y EJECUCIÓN
# ============================================================================
@app.get("/demos/{id_demo}/movimientos", tags=["Movimientos Demo"], summary="Obtener movimientos de DEMO (sp_obtener_movimientos_demo)")
def obtener_movimientos_demo(id_demo: int):
    return {"status": "success", "sp": "sp_obtener_movimientos_demo"}

@app.post("/demos/{id_demo}/movimientos", tags=["Movimientos Demo"], summary="Agregar movimiento a DEMO (sp_agregar_movimiento_demo)")
def agregar_movimiento_demo(id_demo: int):
    return {"status": "success", "sp": "sp_agregar_movimiento_demo"}

@app.put("/demos/movimientos/{id_movimiento}", tags=["Movimientos Demo"], summary="Actualizar movimiento DEMO (sp_actualizar_movimiento_demo)")
def actualizar_movimiento_demo(id_movimiento: int):
    return {"status": "success", "sp": "sp_actualizar_movimiento_demo"}

@app.delete("/demos/movimientos/{id_movimiento}", tags=["Movimientos Demo"], summary="Eliminar movimiento DEMO (sp_eliminar_movimiento_demo)")
def eliminar_movimiento_demo(id_movimiento: int):
    return {"status": "success", "sp": "sp_eliminar_movimiento_demo"}

@app.post("/demos/{id_demo}/ejecutar", tags=["Acciones Control"], summary="Ejecutar secuencia DEMO por WebSocket")
async def ejecutar_demo(id_demo: int, id_vehiculo: int = Query(default=1)):
    mensaje = {
        "evento": "MOVIMIENTO_DEMO",
        "id_vehiculo": id_vehiculo,
        "id_demo": id_demo,
        "id_comando": 11
    }
    await websocket_manager.enviar_a_todos(mensaje)
    return {"status": "success", "mensaje": f"Demo {id_demo} transmitida por WebSocket."}

# ============================================================================
# 7. WEBSOCKET ENDPOINT (Soporta /ws/1 y /ws)
# ============================================================================
@app.websocket("/ws/{id_vehiculo}")
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, id_vehiculo: int = 1):
    await websocket_manager.conectar(websocket)
    await websocket.send_json({"evento": "ESTADO_INICIAL", "id_vehiculo": id_vehiculo})
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_manager.desconectar(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)