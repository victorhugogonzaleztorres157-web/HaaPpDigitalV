#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HERMES v9.1.2 — Fuerza Operativa y Puente de Sensores
Arquitecto: Sistema HaaPpDigitalV
Versión: 9.1.2
Propósito: Captura de datos, ejecución de órdenes y conexión con SOFÍ
Compatibilidad: Termux, SOFÍ v9, Render
"""

import asyncio
import websockets
import json
import os
import logging
import subprocess
import time
import hashlib
from datetime import datetime
from typing import Optional, Dict, Union
from dotenv import load_dotenv
import numpy as np

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN Y LOGGING
# ═══════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [HERMES_v9] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('hermes_v9.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('HERMES_v9_OPERATIVO')

load_dotenv()

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURACIÓN CENTRAL Y PROTOCOLO
# ═══════════════════════════════════════════════════════════════════════════

class CFG:
    # URLs de conexión
    SOFI_URL = os.getenv("SOFI_URL", "wss://haapbdigtalv.onrender.com/ws/canal_kuhul")
    LOCAL_FALLBACK = os.getenv("LOCAL_FALLBACK", "ws://127.0.0.1:8765/ws/canal_kuhul")
    
    # Identificación
    DEVICE_ID = os.getenv("HERMES_ID", "MERIDA_UNIDAD_01")
    TIPO_DISPOSITIVO = os.getenv("HERMES_TIPO", "android_termux")
    VERSION = "9.1.2"
    
    # Seguridad - MISMA LLAVE QUE EN SOFÍ Y LA INTERFAZ
    LLAVE_FIRMA = os.getenv("LLAVE_JHOP", "_12.3Hz_Kuhul_SOFI_2026")
    
    # Intervalos de operación
    INTERVALO_TELEMETRIA = int(os.getenv("HERMES_TELEMETRIA_INTERVALO", 8))
    TIEMPO_RECONEXION = int(os.getenv("HERMES_RECONEXION_TIMEOUT", 5))
    INTERVALO_PING = int(os.getenv("INTERVALO_PING", 15))
    
    # Entorno
    EN_TERMUX = os.getenv("EN_TERMUX", "true").lower() == "true"
    RUTA_FOTOS = os.getenv("RUTA_FOTOS", "/sdcard/DCIM/OSIRIS/")
    RUTA_ARCHIVOS = os.getenv("RUTA_ARCHIVOS", "/sdcard/Download/")
    
    # Coordenadas base Mérida
    LAT_BASE = 20.967775
    LON_BASE = -89.624258

# ── Sistema de firma unificado JHOP ───────────────────────────────────────
def firmar_paquete(datos: Union[dict, str]) -> str:
    """Firma uniforme para verificar integridad en todo el ecosistema"""
    if isinstance(datos, dict):
        datos_str = json.dumps(datos, sort_keys=True, ensure_ascii=False)
    else:
        datos_str = str(datos)
    return hashlib.sha256((datos_str + CFG.LLAVE_FIRMA).encode("utf-8")).hexdigest()[:16]

# ═══════════════════════════════════════════════════════════════════════════
# SENSORES Y ACCESO AL DISPOSITIVO
# ═══════════════════════════════════════════════════════════════════════════

class SensoresDispositivo:
    """Lectura real en Termux + simulación segura para pruebas"""

    def __init__(self, en_termux: bool = True):
        self.en_termux = en_termux
        self.ultimo_gps = {"lat": CFG.LAT_BASE, "lon": CFG.LON_BASE, "precision": 0}
        self.cache_bateria = 100
        self.cache_temp = 36.6
        self.ultima_lectura = datetime.now()
        
        # Crear carpeta para fotos si no existe
        os.makedirs(CFG.RUTA_FOTOS, exist_ok=True)

    async def obtener_gps_real(self) -> Dict:
        """Obtiene ubicación real usando termux-location"""
        if not self.en_termux:
            return self.simular_gps()
        
        try:
            resultado = subprocess.run(
                ["termux-location", "-p", "gps"],
                capture_output=True, text=True, timeout=12
            )
            if resultado.returncode == 0 and resultado.stdout.strip():
                geo = json.loads(resultado.stdout)
                lat = round(float(geo.get("latitude", self.ultimo_gps["lat"])), 6)
                lon = round(float(geo.get("longitude", self.ultimo_gps["lon"])), 6)
                prec = int(float(geo.get("accuracy", 15)))
                self.ultimo_gps = {"lat": lat, "lon": lon, "precision": prec}
                logger.info(f"📍 GPS: {lat:.5f}, {lon:.5f} ±{prec}m")
                return self.ultimo_gps
        except Exception as e:
            logger.warning(f"⚠️ GPS real falló: {str(e)} — usando último valor")
        
        return self.simular_gps()

    def simular_gps(self) -> Dict:
        """Simula pequeños movimientos desde la posición base"""
        lat = round(self.ultimo_gps["lat"] + np.random.normal(0, 0.0008), 6)
        lon = round(self.ultimo_gps["lon"] + np.random.normal(0, 0.0008), 6)
        prec = int(np.random.randint(8, 40))
        return {"lat": lat, "lon": lon, "precision": prec}

    async def obtener_bateria(self) -> int:
        """Lee nivel de batería desde archivos o Termux"""
        if not self.en_termux:
            return self.simular_bateria()
        
        # Método 1: Archivo del sistema
        try:
            with open("/sys/class/power_supply/battery/capacity", "r") as f:
                self.cache_bateria = max(0, min(100, int(f.read().strip())))
                return self.cache_bateria
        except:
            pass
        
        # Método 2: Comando Termux
        try:
            salida = subprocess.check_output(
                ["termux-battery-status"], timeout=5, stderr=subprocess.DEVNULL
            )
            datos = json.loads(salida)
            self.cache_bateria = max(0, min(100, int(datos.get("percentage", self.cache_bateria))))
            return self.cache_bateria
        except:
            pass
        
        return self.simular_bateria()

    def simular_bateria(self) -> int:
        self.cache_bateria = max(10, self.cache_bateria - np.random.randint(0, 2))
        return self.cache_bateria

    async def obtener_temperatura_cpu(self) -> float:
        """Temperatura del procesador"""
        if not self.en_termux:
            return self.simular_temperatura()
        
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                self.cache_temp = round(int(f.read().strip()) / 1000, 1)
                return self.cache_temp
        except:
            pass
        
        return self.simular_temperatura()

    def simular_temperatura(self) -> float:
        base = 36.5
        variacion = np.sin(time.time() / 120) * 1.8 + np.random.normal(0, 0.4)
        self.cache_temp = round(base + variacion, 1)
        return self.cache_temp

    async def tomar_foto(self) -> Dict:
        """Captura imagen con cámara y devuelve ruta accesible"""
        nombre = f"OSIRIS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        ruta_completa = os.path.join(CFG.RUTA_FOTOS, nombre)
        
        try:
            subprocess.run(
                ["termux-camera-photo", "-c", "0", ruta_completa],
                timeout=15, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return {
                "estado": "ok",
                "ruta_local": ruta_completa,
                "nombre": nombre,
                "timestamp": datetime.now().isoformat(),
                "tamano_kb": round(os.path.getsize(ruta_completa) / 1024, 1)
            }
        except Exception as e:
            logger.error(f"❌ Error capturando foto: {str(e)}")
            return {"estado": "error", "mensaje": str(e)}

    async def listar_archivos(self, ruta: str = None) -> Dict:
        """Escanea archivos en la carpeta indicada"""
        ruta = ruta or CFG.RUTA_ARCHIVOS
        try:
            archivos = []
            for f in os.listdir(ruta):
                camino = os.path.join(ruta, f)
                if os.path.isfile(camino):
                    archivos.append({
                        "nombre": f,
                        "tamano_kb": round(os.path.getsize(camino) / 1024, 1),
                        "modificado": datetime.fromtimestamp(os.path.getmtime(camino)).isoformat()
                    })
            return {
                "estado": "ok",
                "ruta": ruta,
                "cantidad": len(archivos),
                "lista": archivos[:20]  # Enviar solo primeros 20 para no saturar
            }
        except Exception as e:
            return {"estado": "error", "mensaje": str(e)}

    async def obtener_sensores_completo(self) -> Dict:
        """Recopila todos los datos en paralelo"""
        gps, bat, temp = await asyncio.gather(
            self.obtener_gps_real(),
            self.obtener_bateria(),
            self.obtener_temperatura_cpu()
        )
        return {
            "gps": gps,
            "bateria": bat,
            "temperatura_cpu": temp,
            "memoria": os.popen("free -h 2>/dev/null | grep Mem | awk '{print $7}'").read().strip() or "N/A",
            "timestamp": datetime.now().isoformat()
        }

# ═══════════════════════════════════════════════════════════════════════════
# NÚCLEO HERMES — COMUNICACIÓN Y EJECUCIÓN
# ═══════════════════════════════════════════════════════════════════════════

class HermesV9Operativo:
    """Controlador principal: conecta sensores, ejecuta órdenes y sincroniza"""

    def __init__(self):
        self.url_actual = CFG.SOFI_URL
        self.conectado = False
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.sensores = SensoresDispositivo(en_termux=CFG.EN_TERMUX)
        
        # Estadísticas de operación
        self.telemetrias_enviadas = 0
        self.comandos_ejecutados = 0
        self.errores_conexion = 0
        self.inicio = datetime.now()

        logger.info("=" * 65)
        logger.info("⚡ HERMES v9.1.2 — FUERZA OPERATIVA ACTIVA")
        logger.info(f"🔹 ID: {CFG.DEVICE_ID}")
        logger.info(f"🔹 Cerebro: {self.url_actual}")
        logger.info(f"🔹 Modo: {'Termux Real' if CFG.EN_TERMUX else 'Simulación'}")
        logger.info("=" * 65)

    def _formatear_mensaje(self, tipo: str, datos: dict = None, comando: str = None) -> dict:
        """Formato estándar compatible con SOFÍ v9"""
        paquete = {
            "tipo": tipo,
            "device_id": CFG.DEVICE_ID,
            "version": CFG.VERSION,
            "timestamp": datetime.now().isoformat()
        }
        if datos:
            paquete["datos"] = datos
        if comando:
            paquete["comando"] = comando
        
        paquete["firma"] = firmar_paquete(paquete)
        return paquete

    async def conectar(self):
        """Ciclo de conexión con respaldo automático"""
        while True:
            try:
                logger.info(f"🔗 Conectando a: {self.url_actual}")
                async with websockets.connect(
                    self.url_actual,
                    ping_interval=25,
                    ping_timeout=12,
                    max_size=15_000_000,
                    open_timeout=10
                ) as ws:
                    self.websocket = ws
                    self.conectado = True
                    self.errores_conexion = 0
                    logger.info("✅ CANAL K'UHUL ESTABLECIDO")

                    # Enviar registro inicial
                    await self.websocket.send(json.dumps(
                        self._formatear_mensaje("registro", {
                            "tipo": CFG.TIPO_DISPOSITIVO,
                            "plataforma": "Android/Termux",
                            "lat_inicial": CFG.LAT_BASE,
                            "lon_inicial": CFG.LON_BASE
                        })
                    ))

                    # Ejecutar tareas en paralelo
                    tareas = [
                        asyncio.create_task(self._ciclo_telemetria()),
                        asyncio.create_task(self._escuchar_comandos()),
                        asyncio.create_task(self._latido_conexion())
                    ]
                    await asyncio.gather(*tareas)

            except Exception as e:
                self.conectado = False
                self.errores_conexion += 1
                logger.error(f"❌ Error conexión #{self.errores_conexion}: {str(e)}")

                # Cambiar a respaldo si falla el principal
                if self.errores_conexion >= 3 and self.url_actual == CFG.SOFI_URL:
                    self.url_actual = CFG.LOCAL_FALLBACK
                    logger.info("🔄 Cambiando a conexión local de respaldo")
                    self.errores_conexion = 0

                await asyncio.sleep(CFG.TIEMPO_RECONEXION)

    async def _ciclo_telemetria(self):
        """Envía datos cada cierto intervalo"""
        while self.conectado:
            try:
                datos = await self.sensores.obtener_sensores_completo()
                paquete = self._formatear_mensaje("telemetria", datos)
                await self.websocket.send(json.dumps(paquete))
                
                self.telemetrias_enviadas += 1
                logger.info(f"📡 Enviado | Bat: {datos['bateria']}% | Temp: {datos['temperatura_cpu']}°C")
                await asyncio.sleep(CFG.INTERVALO_TELEMETRIA)

            except Exception as e:
                logger.debug(f"⚠️ Pausa en telemetría: {str(e)}")
                await asyncio.sleep(2)

    async def _escuchar_comandos(self):
        """Recibe y procesa órdenes desde SOFÍ / Interfaz"""
        while self.conectado:
            try:
                raw = await asyncio.wait_for(self.websocket.recv(), timeout=120)
                mensaje = json.loads(raw)

                # Verificar seguridad
                firma_recibida = mensaje.pop("firma", None)
                firma_valida = firmar_paquete(mensaje)
                if not firma_recibida or firma_recibida != firma_valida:
                    logger.warning("⚠️ Mensaje rechazado: firma inválida")
                    continue

                tipo = mensaje.get("tipo")
                orden = mensaje.get("comando", "").lower().strip()

                if tipo == "ping":
                    await self.websocket.send(json.dumps(self._formatear_mensaje("pong")))
                    continue

                if tipo == "comando" and orden:
                    logger.info(f"📥 Orden recibida: {orden}")
                    respuesta = await self._procesar_orden(orden)
                    await self.websocket.send(json.dumps(
                        self._formatear_mensaje("respuesta", respuesta, comando=orden)
                    ))

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.debug(f"⚠️ Escucha en pausa: {str(e)}")
                await asyncio.sleep(1)

    async def _procesar_orden(self, orden: str) -> Dict:
        """Ejecuta acciones según la orden recibida"""
        self.comandos_ejecutados += 1

        if any(p in orden for p in ["gps", "ubicación", "posición"]):
            return {"accion": "ubicacion", "datos": await self.sensores.obtener_gps_real()}

        elif any(p in orden for p in ["foto", "cámara", "estigia"]):
            return {"accion": "foto", "datos": await self.sensores.tomar_foto()}

        elif any(p in orden for p in ["archivos", "listar", "explorar"]):
            return {"accion": "archivos", "datos": await self.sensores.listar_archivos()}

        elif any(p in orden for p in ["estado", "sensores", "diagnóstico"]):
            return {"accion": "estado", "datos": await self.sensores.obtener_sensores_completo()}

        elif any(p in orden for p in ["posesión", "control"]):
            return {"accion": "posesion", "estado": "activo", "mensaje": "Control confirmado"}

        else:
            return {"accion": "desconocida", "mensaje": "Orden recibida sin acción asignada"}

    async def _latido_conexion(self):
        """Mantiene la conexión viva"""
        while self.conectado:
            try:
                await asyncio.sleep(CFG.INTERVALO_PING)
                await self.websocket.send(json.dumps(self._formatear_mensaje("ping")))
            except:
                break

    async def arrancar(self):
        await self.conectar()

# ═══════════════════════════════════════════════════════════════════════════
# EJECUCIÓN PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    hermes = HermesV9Operativo()
    try:
        asyncio.run(hermes.arrancar())
    except KeyboardInterrupt:
        logger.info("⛔ HERMES detenido por usuario")
    except Exception as e:
        logger.critical(f"❌ Error fatal: {str(e)}", exc_info=True)
