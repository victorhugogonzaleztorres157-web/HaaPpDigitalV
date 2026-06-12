import os
import json
import asyncio
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Sofi v9 - Sistema Central")

class SofiCortex:
    """Núcleo central: Osiris, Cortex, lógica de decisiones"""
    
    def __init__(self):
        self.estado = {
            "sistema": "operativo",
            "timestamp": datetime.now().isoformat(),
            "ubicacion": {"lat": 20.9674, "lon": -89.6237},
            "dispositivos_conectados": [],
            "alertas": [],
            "memoria_vectorial": {}
        }
        self.conexiones_activas = []
        self.historial_comandos = []
    
    async def procesar_comando(self, comando: dict):
        """Procesa órdenes del navegador y las envía a Hermes"""
        logger.info(f"Comando recibido: {comando}")
        self.historial_comandos.append({
            "timestamp": datetime.now().isoformat(),
            "comando": comando
        })
        return {"status": "procesado", "comando": comando}
    
    async def registrar_dispositivo(self, device_id: str, info: dict):
        """Registra conexión de Hermes"""
        self.estado["dispositivos_conectados"].append({
            "id": device_id,
            "info": info,
            "conectado_en": datetime.now().isoformat()
        })
        logger.info(f"Dispositivo registrado: {device_id}")
    
    async def recibir_telemetria(self, device_id: str, datos: dict):
        """Recibe datos de sensores desde Hermes"""
        logger.info(f"Telemetría de {device_id}: GPS {datos.get('gps', {})}")
        return {"status": "recibido"}

cortex = SofiCortex()

@app.get("/", response_class=HTMLResponse)
async def servir_interfaz():
    """Sirve la interfaz visual completa"""
    try:
        with open("html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return """
        <html>
            <head><title>Sofi v9 - Cargando...</title></head>
            <body style='background: #0a0e27; color: #00ff88; font-family: monospace; text-align: center; padding-top: 50px;'>
                <h1>⚠️ Interfaz no disponible</h1>
                <p>El archivo HTML no se encontró. Verifica la estructura del repositorio.</p>
            </body>
        </html>
        """

@app.get("/status")
async def estado_sistema():
    """Estado actual del sistema"""
    return {
        "sistema": cortex.estado,
        "conexiones_activas": len(cortex.conexiones_activas),
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/canal_kuhul")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket principal: Navegador + Hermes se conectan aquí"""
    await websocket.accept()
    cortex.conexiones_activas.append(websocket)
    
    logger.info(f"Nueva conexión. Total activas: {len(cortex.conexiones_activas)}")
    
    try:
        while True:
            datos = await websocket.receive_json()
            tipo = datos.get("tipo")
            
            if tipo == "hermes_connect":
                device_id = datos.get("device_id", "MERIDA_UNIDAD_01")
                await cortex.registrar_dispositivo(device_id, datos.get("info", {}))
                await websocket.send_json({
                    "tipo": "confirmacion",
                    "mensaje": f"Hermes {device_id} conectado al Cerebro"
                })
            
            elif tipo == "telemetria":
                await cortex.recibir_telemetria(
                    datos.get("device_id", "unknown"),
                    datos.get("datos", {})
                )
                for conn in cortex.conexiones_activas:
                    if conn != websocket:
                        try:
                            await conn.send_json(datos)
                        except:
                            pass
            
            elif tipo == "comando":
                resultado = await cortex.procesar_comando(datos)
                for conn in cortex.conexiones_activas:
                    if conn != websocket:
                        try:
                            await conn.send_json({
                                "tipo": "comando",
                                "contenido": datos
                            })
                        except:
                            pass
                await websocket.send_json(resultado)
            
            else:
                logger.warning(f"Tipo de mensaje desconocido: {tipo}")
    
    except WebSocketDisconnect:
        cortex.conexiones_activas.remove(websocket)
        logger.info(f"Desconexión. Activas: {len(cortex.conexiones_activas)}")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")
        if websocket in cortex.conexiones_activas:
            cortex.conexiones_activas.remove(websocket)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    logger.info(f"🧠 Sofi v9 - Cerebro iniciando en puerto {port}")
    uvicorn.run("sofi_v9_master_universal:app", host="0.0.0.0", port=port, reload=False)
