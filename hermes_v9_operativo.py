import asyncio
import websockets
import json
import os
from datetime import datetime
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class HermesOperativo:
    """Fuerza Operativa: Control de hardware del dispositivo"""
    
    def __init__(self):
        self.sofi_url = os.getenv("SOFI_URL", "wss://haappdigitalv.onrender.com/ws/canal_kuhul")
        self.device_id = os.getenv("HERMES_ID", "MERIDA_UNIDAD_01")
        self.conectado = False
        self.websocket = None
        self.datos_sensores = {
            "gps": {"lat": 0, "lon": 0, "precision": 0},
            "bateria": 100,
            "temperatura": 0,
            "sensores": {}
        }
    
    async def obtener_gps(self):
        """Obtiene ubicación GPS real"""
        try:
            # En Termux: requiere 'termux-location' de termux-api
            # Por ahora simulamos
            return {"lat": 20.9674, "lon": -89.6237, "precision": 10}
        except Exception as e:
            logger.error(f"Error obteniendo GPS: {e}")
            return {"lat": 0, "lon": 0, "precision": 0}
    
    async def obtener_bateria(self):
        """Obtiene nivel de batería"""
        try:
            # En Termux: lee desde /sys/class/power_supply/battery/capacity
            with open("/sys/class/power_supply/battery/capacity", "r") as f:
                return int(f.read().strip())
        except:
            return 100
    
    async def obtener_sensores(self):
        """Obtiene datos de sensores disponibles"""
        return {
            "timestamp": datetime.now().isoformat(),
            "dispositivo": self.device_id,
            "gps": await self.obtener_gps(),
            "bateria": await self.obtener_bateria()
        }
    
    async def ejecutar_comando(self, comando: dict):
        """Ejecuta comandos del Cerebro"""
        tipo = comando.get("tipo")
        parametros = comando.get("parametros", {})
        
        logger.info(f"Ejecutando comando: {tipo}")
        
        if tipo == "get_sensores":
            return await self.obtener_sensores()
        elif tipo == "get_ubicacion":
            return await self.obtener_gps()
        elif tipo == "get_bateria":
            return {"bateria": await self.obtener_bateria()}
        else:
            return {"status": "comando_desconocido", "tipo": tipo}
    
    async def enviar_telemetria(self):
        """Envía telemetría periódica al Cerebro"""
        while self.conectado:
            try:
                datos = await self.obtener_sensores()
                mensaje = {
                    "tipo": "telemetria",
                    "device_id": self.device_id,
                    "datos": datos
                }
                await self.websocket.send(json.dumps(mensaje))
                logger.info(f"Telemetría enviada: GPS {datos['gps']}")
                await asyncio.sleep(10)  # Cada 10 segundos
            except Exception as e:
                logger.error(f"Error enviando telemetría: {e}")
                break
    
    async def conectar(self):
        """Conecta a Sofi Cerebro"""
        while True:
            try:
                logger.info(f"Conectando a {self.sofi_url}")
                async with websockets.connect(self.sofi_url) as websocket:
                    self.websocket = websocket
                    self.conectado = True
                    
                    # Enviar identificación
                    await websocket.send(json.dumps({
                        "tipo": "hermes_connect",
                        "device_id": self.device_id,
                        "info": {"version": "v9", "tipo": "operativo"}
                    }))
                    
                    # Iniciar envío de telemetría
                    telemetria_task = asyncio.create_task(self.enviar_telemetria())
                    
                    # Escuchar comandos
                    while self.conectado:
                        try:
                            mensaje = await asyncio.wait_for(websocket.recv(), timeout=60)
                            datos = json.loads(mensaje)
                            
                            if datos.get("tipo") == "comando":
                                resultado = await self.ejecutar_comando(datos.get("contenido", {}))
                                await websocket.send(json.dumps({
                                    "tipo": "resultado_comando",
                                    "resultado": resultado
                                }))
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            logger.error(f"Error recibiendo mensaje: {e}")
                            break
                    
                    telemetria_task.cancel()
                    self.conectado = False
            
            except Exception as e:
                logger.error(f"Error de conexión: {e}")
                self.conectado = False
                await asyncio.sleep(5)  # Reintentar cada 5 segundos
    
    async def iniciar(self):
        """Inicia Hermes"""
        logger.info(f"⚡ HERMES {self.device_id} iniciando...")
        await self.conectar()

# ============ ARRANQUE ============

if __name__ == "__main__":
    hermes = HermesOperativo()
    try:
        asyncio.run(hermes.iniciar())
    except KeyboardInterrupt:
        logger.info("Hermes detenido")
