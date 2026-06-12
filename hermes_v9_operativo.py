import asyncio
import websockets
import json
import os
import logging
import subprocess
import time
from datetime import datetime
from typing import Optional, Dict
from dotenv import load_dotenv
import numpy as np

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y LOGGING
# ═══════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [HERMES] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('hermes_v9.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('HERMES_v9_OPERATIVO')

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════
# HERMES v9 — FUERZA OPERATIVA COMPLETA
# ═══════════════════════════════════════════════════════════════════════════

class SensoresDispositivo:
    """Abstracción de sensores — Soporta Termux real + simulación"""
    
    def __init__(self, en_termux: bool = True):
        self.en_termux = en_termux
        self.ultimo_gps = {"lat": 20.9674, "lon": -89.6237, "precision": 0}
        self.cache_bateria = 100
        self.cache_temp = 36.6
        
    async def obtener_gps_real(self) -> Dict:
        """Obtiene GPS real via termux-api"""
        if not self.en_termux:
            return self.simular_gps()
        
        try:
            resultado = subprocess.run(
                ['termux-location', '-p', 'network'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if resultado.returncode == 0:
                lineas = resultado.stdout.strip().split('\n')
                for linea in lineas:
                    if linea.startswith('LAT:'):
                        lat = float(linea.split('LAT:')[1].split('LON')[0].strip())
                        lon = float(linea.split('LON:')[1].split('ALT')[0].strip())
                        acc = float(linea.split('ACCURACY:')[1].strip()) if 'ACCURACY:' in linea else 10
                        self.ultimo_gps = {"lat": lat, "lon": lon, "precision": acc}
                        logger.info(f"📍 GPS Real: {lat:.5f}, {lon:.5f} ±{acc}m")
                        return self.ultimo_gps
        except Exception as e:
            logger.warning(f"⚠️ GPS Termux falló: {e} — usando fallback")
        
        return self.simular_gps()
    
    def simular_gps(self) -> Dict:
        """Simula GPS con pequeña variación"""
        lat = self.ultimo_gps["lat"] + (np.random.randn() * 0.001)
        lon = self.ultimo_gps["lon"] + (np.random.randn() * 0.001)
        return {"lat": lat, "lon": lon, "precision": np.random.randint(5, 50)}
    
    async def obtener_bateria(self) -> int:
        """Obtiene nivel de batería"""
        if not self.en_termux:
            return self.simular_bateria()
        
        try:
            with open("/sys/class/power_supply/battery/capacity", "r") as f:
                bat = int(f.read().strip())
                self.cache_bateria = bat
                return bat
        except:
            logger.debug("⚠️ Batería fallback — usando simulación")
            return self.simular_bateria()
    
    def simular_bateria(self) -> int:
        """Simula batería con degradación lenta"""
        self.cache_bateria = max(20, self.cache_bateria - np.random.randint(0, 2))
        return self.cache_bateria
    
    async def obtener_temperatura_cpu(self) -> float:
        """Obtiene temperatura del CPU (Termux)"""
        if not self.en_termux:
            return self.simular_temperatura()
        
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_raw = int(f.read().strip())
                temp_c = temp_raw / 1000
                self.cache_temp = temp_c
                return temp_c
        except:
            return self.simular_temperatura()
    
    def simular_temperatura(self) -> float:
        """Simula temperatura realista"""
        self.cache_temp = 35 + np.random.randn() * 2 + abs(np.sin(time.time() / 100) * 1.5)
        return round(self.cache_temp, 1)
    
    async def obtener_sensores_completo(self) -> Dict:
        """Obtiene todos los sensores en paralelo"""
        gps, bat, temp = await asyncio.gather(
            self.obtener_gps_real(),
            self.obtener_bateria(),
            self.obtener_temperatura_cpu()
        )
        
        return {
            "gps": gps,
            "bateria": bat,
            "temperatura_cpu": temp,
            "timestamp": datetime.now().isoformat(),
            "memoria_disponible": os.popen("free -h 2>/dev/null | grep Mem | awk '{print $7}'").read().strip() or "N/A"
        }

class HermesV9Operativo:
    """Fuerza Operativa de SOFÍ — Controlador de Dispositivo"""
    
    def __init__(self):
        self.sofi_url = os.getenv("SOFI_URL", "wss://haappdigitalv-core.onrender.com/ws/canal_kuhul")
        self.device_id = os.getenv("HERMES_ID", "MERIDA_UNIDAD_01")
        self.tipo_dispositivo = os.getenv("HERMES_TIPO", "android_termux")
        
        self.conectado = False
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.sensores = SensoresDispositivo(en_termux=True)
        
        # Configuración de ciclos
        self.intervalo_telemetria = int(os.getenv("HERMES_TELEMETRIA_INTERVALO", 10))
        self.timeout_reconexion = int(os.getenv("HERMES_RECONEXION_TIMEOUT", 5))
        
        # Métricas
        self.telemetrias_enviadas = 0
        self.comandos_ejecutados = 0
        self.errores_conexion = 0
        self.tiempo_inicio = datetime.now()
        
        logger.info(f"⚡ HERMES v9 Inicializado")
        logger.info(f"   ID: {self.device_id}")
        logger.info(f"   Tipo: {self.tipo_dispositivo}")
        logger.info(f"   URL Cerebro: {self.sofi_url}")
    
    async def conectar_sofi(self):
        """Conecta a SOFÍ Cerebro con reintentos automáticos"""
        while True:
            try:
                logger.info(f"🔗 Conectando a {self.sofi_url}...")
                
                async with websockets.connect(
                    self.sofi_url,
                    ping_interval=30,
                    ping_timeout=10,
                    max_size=10_000_000
                ) as websocket:
                    self.websocket = websocket
                    self.conectado = True
                    self.errores_conexion = 0
                    
                    logger.info("✅ Conectado a SOFÍ v9 Cerebro")
                    
                    # Enviar identificación
                    await self._enviar_identificacion()
                    
                    # Iniciar tareas paralelas
                    telemetria_task = asyncio.create_task(self._ciclo_telemetria())
                    escucha_task = asyncio.create_task(self._ciclo_escucha())
                    
                    try:
                        await asyncio.gather(telemetria_task, escucha_task)
                    except asyncio.CancelledError:
                        logger.info("⚠️ Tareas canceladas")
                        telemetria_task.cancel()
                        escucha_task.cancel()
                        raise
            
            except Exception as e:
                self.conectado = False
                self.errores_conexion += 1
                logger.error(f"❌ Error de conexión: {e}")
                logger.info(f"🔄 Reintentando en {self.timeout_reconexion}s (Intento #{self.errores_conexion})")
                await asyncio.sleep(self.timeout_reconexion)
    
    async def _enviar_identificacion(self):
        """Envía datos de identificación a SOFÍ"""
        mensaje = {
            "tipo": "telemetria",
            "device_id": self.device_id,
            "datos": {
                "tipo_mensaje": "identificacion",
                "version_hermes": "9.0.0",
                "tipo_dispositivo": self.tipo_dispositivo,
                "sistema_operativo": "android_termux"
            }
        }
        await self.websocket.send(json.dumps(mensaje))
        logger.info(f"📨 Identificación enviada: {self.device_id}")
    
    async def _ciclo_telemetria(self):
        """Envía telemetría periodicamente"""
        while self.conectado:
            try:
                sensores_data = await self.sensores.obtener_sensores_completo()
                
                mensaje = {
                    "tipo": "telemetria",
                    "device_id": self.device_id,
                    "datos": sensores_data
                }
                
                await self.websocket.send(json.dumps(mensaje))
                self.telemetrias_enviadas += 1
                
                logger.info(
                    f"📡 Telemetría #{self.telemetrias_enviadas}: "
                    f"GPS({sensores_data['gps']['lat']:.4f}, {sensores_data['gps']['lon']:.4f}) "
                    f"BAT({sensores_data['bateria']}%) "
                    f"TEMP({sensores_data['temperatura_cpu']}°C)"
                )
                
                await asyncio.sleep(self.intervalo_telemetria)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error enviando telemetría: {e}")
                await asyncio.sleep(2)
    
    async def _ciclo_escucha(self):
        """Escucha comandos desde SOFÍ Cerebro"""
        while self.conectado:
            try:
                mensaje = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=120
                )
                
                datos = json.loads(mensaje)
                tipo = datos.get("tipo")
                
                if tipo == "comando_distribuido":
                    await self._ejecutar_comando_remoto(datos.get("comando", {}))
                
                elif tipo == "pong":
                    logger.debug("💓 Pong recibido")
                
                else:
                    logger.debug(f"Mensaje recibido: {tipo}")
            
            except asyncio.TimeoutError:
                logger.debug("⏱️ Timeout en escucha (normal)")
                continue
            
            except Exception as e:
                logger.error(f"❌ Error en ciclo de escucha: {e}")
                break
    
    async def _ejecutar_comando_remoto(self, comando: Dict):
        """Ejecuta comandos enviados por SOFÍ"""
        try:
            cmd_tipo = comando.get("comando", "").lower()
            self.comandos_ejecutados += 1
            
            logger.info(f"⚡ Ejecutando comando remoto: {cmd_tipo}")
            
            if "gps" in cmd_tipo:
                resultado = await self.sensores.obtener_gps_real()
                logger.info(f"   GPS obtenido: {resultado}")
            
            elif "bateria" in cmd_tipo:
                bat = await self.sensores.obtener_bateria()
                logger.info(f"   Batería: {bat}%")
            
            elif "estado" in cmd_tipo:
                logger.info(f"   Estado del sistema (#{self.comandos_ejecutados})")
            
            else:
                logger.warning(f"   Comando no reconocido: {cmd_tipo}")
        
        except Exception as e:
            logger.error(f"❌ Error ejecutando comando remoto: {e}")
    
    async def ping_periodico(self):
        """Envía ping cada 60 segundos para mantener vivo"""
        while self.conectado:
            try:
                await asyncio.sleep(60)
                if self.websocket and self.conectado:
                    await self.websocket.send(json.dumps({"tipo": "ping"}))
                    logger.debug("📍 Ping enviado")
            except:
                break
    
    async def iniciar(self):
        """Inicia HERMES — punto de entrada"""
        logger.info("=" * 70)
        logger.info("⚡ HERMES v9 — Fuerza Operativa iniciando")
        logger.info("=" * 70)
        
        await self.conectar_sofi()

# ═══════════════════════════════════════════════════════════════════════════
# ARRANQUE
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    hermes = HermesV9Operativo()
    try:
        asyncio.run(hermes.iniciar())
    except KeyboardInterrupt:
        logger.info("⛔ HERMES detenido por usuario")
    except Exception as e:
        logger.critical(f"❌ Error fatal: {e}", exc_info=True)