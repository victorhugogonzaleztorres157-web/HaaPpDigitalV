#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HERMES v9.1.2 — COMPLETO · LISTO PARA TERMUX Y GITHUB
Arquitecto: Sistema HaaPpDigitalV
Versión: 9.1.2
Propósito: Conexión con SOFÍ, sensores, comandos y Render
Sin dependencias problemáticas, rutas corregidas
"""

import asyncio
import websockets
import json
import os
import logging
import subprocess
import time
import hashlib
import random
from math import sin
from datetime import datetime
from typing import Optional, Dict, Union

# ═══════════════════════════════════════════════════════════════════════════
# ✅ CONFIGURACIÓN — RUTAS AJUSTADAS PARA PERMISOS EN TERMUX
# ═══════════════════════════════════════════════════════════════════════════
class CFG:
    # Conexiones
    SOFI_URL = "wss://haapbdigtalv.onrender.com/ws/canal_kuhul"
    LOCAL_FALLBACK = "ws://127.0.0.1:8765/ws/canal_kuhul"

    # Identificación
    DEVICE_ID = "MERIDA_UNIDAD_01"
    TIPO_DISPOSITIVO = "android_termux"
    VERSION = "9.1.2"

    # Seguridad — MISMA LLAVE EN HTML, HERMES Y SOFÍ
    LLAVE_FIRMA = "_12.3Hz_Kuhul_SOFI_2026"

    # Intervalos
    INTERVALO_TELEMETRIA = 8
    TIEMPO_RECONEXION = 5
    INTERVALO_PING = 15

    # Entorno
    EN_TERMUX = True
    # ✅ RUTAS CORREGIDAS: Funcionan sin errores de permiso
    RUTA_FOTOS = os.path.expanduser("~/osiris_fotos/")
    RUTA_ARCHIVOS = os.path.expanduser("~/storage/downloads/")

    # Posición base Mérida
    LAT_BASE = 20.967775
    LON_BASE = -89.624258

# ═══════════════════════════════════════════════════════════════════════════
# SISTEMA DE LOGS Y FIRMA DE SEGURIDAD
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

def firmar_paquete(datos: Union[dict, str]) -> str:
    if isinstance(datos, dict):
        datos_str = json.dumps(datos, sort_keys=True, ensure_ascii=False)
    else:
        datos_str = str(datos)
    return hashlib.sha256((datos_str + CFG.LLAVE_FIRMA).encode("utf-8")).hexdigest()[:16]

# ═══════════════════════════════════════════════════════════════════════════
# SENSORES Y ACCIONES — TODAS LAS FUNCIONES ACTIVAS
# ═══════════════════════════════════════════════════════════════════════════
class SensoresDispositivo:
    def __init__(self, en_termux: bool = True):
        self.en_termux = en_termux
        self.ultimo_gps = {"lat": CFG.LAT_BASE, "lon": CFG.LON_BASE, "precision": 0}
        self.cache_bateria = 100
        self.cache_temp = 36.6
        os.makedirs(CFG.RUTA_FOTOS, exist_ok=True)

    async def obtener_gps_real(self) -> Dict:
        if not self.en_termux:
            return self.simular_gps()
        try:
            res = subprocess.run(["termux-location", "-p", "gps"], capture_output=True, text=True, timeout=12)
            if res.returncode == 0 and res.stdout.strip():
                geo = json.loads(res.stdout)
                lat = round(float(geo.get("latitude", self.ultimo_gps["lat"])), 6)
                lon = round(float(geo.get("longitude", self.ultimo_gps["lon"])), 6)
                prec = int(float(geo.get("accuracy", 15)))
                self.ultimo_gps = {"lat": lat, "lon": lon, "precision": prec}
                logger.info(f"📍 GPS: {lat:.5f}, {lon:.5f} ±{prec}m")
                return self.ultimo_gps
        except Exception as e:
            logger.warning(f"⚠️ GPS falló: {e}")
        return self.simular_gps()

    def simular_gps(self) -> Dict:
        lat = round(self.ultimo_gps["lat"] + random.uniform(-0.0008, 0.0008), 6)
        lon = round(self.ultimo_gps["lon"] + random.uniform(-0.0008, 0.0008), 6)
        return {"lat": lat, "lon": lon, "precision": random.randint(8, 40)}

    async def obtener_bateria(self) -> int:
        if not self.en_termux:
            return self.simular_bateria()
        try:
            with open("/sys/class/power_supply/battery/capacity", "r") as f:
                return max(0, min(100, int(f.read().strip())))
        except:
            try:
                salida = subprocess.check_output(["termux-battery-status"], timeout=5, stderr=subprocess.DEVNULL)
                return max(0, min(100, int(json.loads(salida).get("percentage", self.cache_bateria))))
            except:
                return self.simular_bateria()

    def simular_bateria(self) -> int:
        self.cache_bateria = max(10, self.cache_bateria - random.randint(0, 2))
        return self.cache_bateria

    async def obtener_temperatura_cpu(self) -> float:
        if not self.en_termux:
            return self.simular_temperatura()
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return round(int(f.read().strip()) / 1000, 1)
        except:
            return self.simular_temperatura()

    def simular_temperatura(self) -> float:
        variacion = sin(time.time() / 120) * 1.8 + random.uniform(-0.4, 0.4)
        return round(36.5 + variacion, 1)

    async def tomar_foto(self) -> Dict:
        ruta = os.path.join(CFG.RUTA_FOTOS, f"OSIRIS_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        try:
            subprocess.run(["termux-camera-photo", "-c", "0", ruta], timeout=15, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return {"estado": "ok", "ruta": ruta, "tamano_kb": round(os.path.getsize(ruta)/1024, 1)}
        except Exception as e:
            return {"estado": "error", "mensaje": str(e)}

    async def listar_archivos(self) -> Dict:
        try:
            archivos = []
            for nombre in os.listdir(CFG.RUTA_ARCHIVOS):
                ruta = os.path.join(CFG.RUTA_ARCHIVOS, nombre)
                if os.path.isfile(ruta):
                    archivos.append({"nombre": nombre, "tamano_kb": round(os.path.getsize(ruta)/1024, 1)})
            return {"estado": "ok", "cantidad": len(archivos), "lista": archivos[:15]}
        except Exception as e:
            return {"estado": "error", "mensaje": str(e)}

    async def obtener_sensores_completo(self) -> Dict:
        gps = await self.obtener_gps_real()
        bat = await self.obtener_bateria()
        temp = await self.obtener_temperatura_cpu()
        mem = os.popen("free -h 2>/dev/null | grep Mem | awk '{print $7}'").read().strip() or "N/A"
        return {"gps": gps, "bateria": bat, "temperatura_cpu": temp, "memoria": mem, "timestamp": datetime.now().isoformat()}

# ═══════════════════════════════════════════════════════════════════════════
# NÚCLEO DE CONEXIÓN Y COMANDOS
# ═══════════════════════════════════════════════════════════════════════════
class HermesV9Operativo:
    def __init__(self):
        self.url_actual = CFG.SOFI_URL
        self.conectado = False
        self.websocket = None
        self.sensores = SensoresDispositivo()
        logger.info("=" * 65)
        logger.info("⚡ HERMES v9.1.2 — COMPLETO · LISTO")
        logger.info(f"🔹 ID: {CFG.DEVICE_ID}")
        logger.info(f"🔹 Cerebro: {self.url_actual}")
        logger.info("=" * 65)

    def _formatear(self, tipo: str, datos=None, comando=None):
        paq = {
            "tipo": tipo,
            "device_id": CFG.DEVICE_ID,
            "version": CFG.VERSION,
            "timestamp": datetime.now().isoformat()
        }
        if datos: paq["datos"] = datos
        if comando: paq["comando"] = comando
        paq["firma"] = firmar_paquete(paq)
        return paq

    async def conectar(self):
        while True:
            try:
                logger.info(f"🔗 Conectando a {self.url_actual}")
                async with websockets.connect(self.url_actual, ping_interval=25, ping_timeout=12, open_timeout=10) as ws:
                    self.websocket = ws
                    self.conectado = True
                    logger.info("✅ CANAL K'UHUL ESTABLECIDO")
                    await ws.send(json.dumps(self._formatear("registro", {"plataforma": "Termux Android"})))
                    await asyncio.gather(self._telemetria(), self._escuchar(), self._latido())
            except Exception as e:
                self.conectado = False
                logger.error(f"❌ Conexión fallida: {e}")
                await asyncio.sleep(CFG.TIEMPO_RECONEXION)

    async def _telemetria(self):
        while self.conectado:
            datos = await self.sensores.obtener_sensores_completo()
            await self.websocket.send(json.dumps(self._formatear("telemetria", datos)))
            logger.info(f"📡 Enviado | Bat: {datos['bateria']}% | Temp: {datos['temperatura_cpu']}°C")
            await asyncio.sleep(CFG.INTERVALO_TELEMETRIA)

    async def _escuchar(self):
        while self.conectado:
            try:
                msg = json.loads(await asyncio.wait_for(self.websocket.recv(), timeout=120))
                firma_recibida = msg.pop("firma", None)
                if firma_recibida != firmar_paquete(msg):
                    logger.warning("⚠️ Firma inválida — mensaje ignorado")
                    continue
                if msg.get("tipo") == "ping":
                    await self.websocket.send(json.dumps(self._formatear("pong")))
                elif msg.get("tipo") == "comando":
                    orden = msg.get("comando", "").lower()
                    if any(p in orden for p in ["gps", "ubicación"]):
                        res = await self.sensores.obtener_gps_real()
                    elif any(p in orden for p in ["foto", "cámara"]):
                        res = await self.sensores.tomar_foto()
                    elif any(p in orden for p in ["archivos", "listar"]):
                        res = await self.sensores.listar_archivos()
                    elif any(p in orden for p in ["estado", "sensores"]):
                        res = await self.sensores.obtener_sensores_completo()
                    else:
                        res = {"mensaje": "Orden recibida y procesada"}
                    await self.websocket.send(json.dumps(self._formatear("respuesta", res, comando=orden)))
            except:
                await asyncio.sleep(1)

    async def _latido(self):
        while self.conectado:
            await asyncio.sleep(CFG.INTERVALO_PING)
            await self.websocket.send(json.dumps(self._formatear("ping")))

    async def arrancar(self):
        await self.conectar()

if __name__ == "__main__":
    try:
        asyncio.run(HermesV9Operativo().arrancar())
    except KeyboardInterrupt:
        logger.info("⛔ HERMES detenido por usuario")
    except Exception as e:
        logger.critical(f"❌ Error fatal: {e}", exc_info=True)
