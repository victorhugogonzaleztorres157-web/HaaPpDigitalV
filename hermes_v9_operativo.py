#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HERMES v9 — Fuerza Operativa y Puente de Sensores
Arquitecto: Sistema HaaPpDigitalV
Versión: 9.1.0
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
    SOFI_URL = os.getenv("SOFI_URL", "wss://haappdigitalv-core.onrender.com/ws/canal_kuhul")
    DEVICE_ID = os.getenv("HERMES_ID", "MERIDA_UNIDAD_01")
    TIPO_DISPOSITIVO = os.getenv("HERMES_TIPO", "android_termux")
    VERSION = "9.1.0"
    LLAVE_FIRMA = os.getenv("LLAVE_JHOP", "_12.3Hz_Kuhul_SOFI_2026")
    INTERVALO_TELEMETRIA = int(os.getenv("HERMES_TELEMETRIA_INTERVALO", 10))
    TIEMPO_RECONEXION = int(os.getenv("HERMES_RECONEXION_TIMEOUT", 5))
    INTERVALO_PING = int(os.getenv("INTERVALO_PING", 15))
    EN_TERMUX = os.getenv("EN_TERMUX", "true").lower() == "true"

# ── Sistema de firma JHOP — igual que en SOFÍ ─────────────────────────────
def firmar_paquete(datos: Union[dict, str]) -> str:
    """Firma uniforme para verificar integridad en todo el sistema"""
    if isinstance(datos, dict):
        datos = json.dumps(datos, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((datos + CFG.LLAVE_FIRMA).encode()).hexdigest()[:16]

# ═══════════════════════════════════════════════════════════════════════════
# SENSORES DISPOSITIVO
# ═══════════════════════════════════════════════════════════════════════════

class SensoresDispositivo:
    """Abstracción de sensores — Soporta Termux real + simulación"""

    def __init__(self, en_termux: bool = True):
        self.en_termux = en_termux
        self.ultimo_gps = {"lat": 20.9674, "lon": -89.6237, "precision": 0}
        self.cache_bateria = 100
        self.cache_temp = 36.6
        self.ultima_lectura = datetime.now()

    async def obtener_gps_real(self) -> Dict:
        """
        [CORREGIDO] termux-location devuelve JSON, parseo seguro
        """
        if not self.en_termux:
            return self.simular_gps()
        try:
            resultado = subprocess.run(
                ['termux-location', '-p', 'network'],
                capture_output=True, text=True, timeout=10
            )
            if resultado.returncode == 0 and resultado.stdout.strip():
                geo = json.loads(resultado.stdout)
                lat = float(geo.get("latitude", self.ultimo_gps["lat"]))
                lon = float(geo.get("longitude", self.ultimo_gps["lon"]))
                acc = float(geo.get("accuracy", 10))
                self.ultimo_gps = {"lat": round(lat, 6), "lon": round(lon, 6), "precision": int(acc)}
                logger.info(f"📍 GPS Real: {lat:.5f}, {lon:.5f} ±{acc}m")
                return self.ultimo_gps
        except Exception as e:
            logger.warning(f"⚠️ GPS Termux falló: {e} — usando último valor o simulación")
        return self.simular_gps()

    def simular_gps(self) -> Dict:
        lat = self.ultimo_gps["lat"] + (np.random.randn() * 0.001)
        lon = self.ultimo_gps["lon"] + (np.random.randn() * 0.001)
        return {"lat": round(lat, 6), "lon": round(lon, 6), "precision": int(np.random.randint(5, 50))}

    async def obtener_bateria(self) -> int:
        if not self.en_termux:
            return self.simular_bateria()
        try:
            # Intento 1: sysfs
            with open("/sys/class/power_supply/battery/capacity", "r") as f:
                bat = int(f.read().strip())
                self.cache_bateria = max(0, min(100, bat))
                return self.cache_bateria
        except:
            pass
        try:
            # Intento 2: termux-battery-status
            raw = subprocess.check_output(["termux-battery-status"], timeout=5, stderr=subprocess.DEVNULL)
            datos = json.loads(raw)
            bat = int(datos.get("percentage", self.cache_bateria))
            self.cache_bateria = max(0, min(100, bat))
            return self.cache_bateria
        except:
            return self.simular_bateria()

    def simular_bateria(self) -> int:
        self.cache_bateria = max(20, self.cache_bateria - int(np.random.randint(0, 2)))
        return self.cache_bateria

    async def obtener_temperatura_cpu(self) -> float:
        if not self.en_termux:
            return self.simular_temperatura()
        try:
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                temp_raw = int(f.read().strip())
                self.cache_temp = round(temp_raw / 1000, 1)
                return self.cache_temp
        except:
            return self.simular_temperatura()

    def simular_temperatura(self) -> float:
        self.cache_temp = round(35 + np.random.randn() * 2 + abs(np.sin(time.time() / 100) * 1.5), 1)
        return self.cache_temp

    async def obtener_sensores_completo(self) -> Dict:
        gps, bat, temp = await asyncio.gather(
            self.obtener_gps_real(),
            self.obtener_bateria(),
            self.obtener_temperatura_cpu()
        )
        memoria = os.popen("free -h 2>/dev/null | grep Mem | awk '{print $7}'").read().strip() or "N/A"
        return {
            "gps": gps,
            "bateria": bat,
            "temperatura_cpu": temp,
            "memoria_disponible": memoria,
            "timestamp": datetime.now().isoformat(),
            "firma": firmar_paquete(f"{gps}{bat}{temp}")
        }


# ═══════════════════════════════════════════════════════════════════════════
# HERMES v9 — FUERZA OPERATIVA COMPLETA
# ═══════════════════════════════════════════════════════════════════════════

class HermesV9Operativo:
    """
    Fuerza Operativa de SOFÍ — Controlador de Dispositivo Termux.
    PROTOCOLO COMPATIBLE: Envía y recibe en formato estándar de SOFÍ v9
    """

    def __init__(self):
        self.sofi_url = CFG.SOFI_URL
        self.device_id = CFG.DEVICE_ID
        self.tipo_dispositivo = CFG.TIPO_DISPOSITIVO
        self.version = CFG.VERSION

        self.conectado = False
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.sensores = SensoresDispositivo(en_termux=CFG.EN_TERMUX)

        self.intervalo_telemetria = CFG.INTERVALO_TELEMETRIA
        self.tiempo_reconexion = CFG.TIEMPO_RECONEXION
        self.intervalo_ping = CFG.INTERVALO_PING

        # Métricas
        self.telemetrias_enviadas = 0
        self.comandos_ejecutados = 0
        self.errores_conexion = 0
        self.tiempo_inicio = datetime.now()

        logger.info("⚡ HERMES v9.1 Inicializado")
        logger.info(f"   ID       : {self.device_id}")
        logger.info(f"   Tipo     : {self.tipo_dispositivo}")
        logger.info(f"   Cerebro  : {self.sofi_url}")

    # ── Formato estándar compatible con SOFÍ ─────────────────────────────
    def _formatear_mensaje(self, tipo: str, datos: dict = None, comando: str = None) -> dict:
        """Genera paquetes en el formato exacto que espera SOFÍ v9"""
        paquete = {
            "tipo": tipo,
            "device_id": self.device_id,
            "timestamp": datetime.now().isoformat(),
            "firma": ""
        }
        if datos:
            paquete["datos"] = datos
        if comando:
            paquete["comando"] = comando
        paquete["firma"] = firmar_paquete(paquete)
        return paquete

    # ── Conexión principal ────────────────────────────────────────────────
    async def conectar_sofi(self):
        while True:
            try:
                logger.info(f"🔗 Conectando a SOFÍ en {self.sofi_url}...")
                async with websockets.connect(
                    self.sofi_url,
                    ping_interval=30,
                    ping_timeout=10,
                    max_size=10_000_000,
                    close_timeout=5
                ) as websocket:
                    self.websocket = websocket
                    self.conectado = True
                    self.errores_conexion = 0
                    logger.info("✅ Conectado a SOFÍ v9 — Canal K'uhul activo")

                    # Identificación inicial
                    datos_registro = {
                        "version": self.version,
                        "tipo": self.tipo_dispositivo,
                        "plataforma": "Termux/Android" if CFG.EN_TERMUX else "Simulación"
                    }
                    msg_registro = self._formatear_mensaje("registro", datos_registro)
                    await self.websocket.send(json.dumps(msg_registro, ensure_ascii=False))
                    logger.info("📨 Identificación enviada correctamente")

                    # Tareas paralelas
                    tareas = [
                        asyncio.create_task(self._ciclo_telemetria()),
                        asyncio.create_task(self._ciclo_escucha()),
                        asyncio.create_task(self._ping_periodico())
                    ]

                    try:
                        await asyncio.gather(*tareas)
                    except asyncio.CancelledError:
                        for t in tareas:
                            t.cancel()
                        raise

            except Exception as e:
                self.conectado = False
                self.errores_conexion += 1
                logger.error(f"❌ Error de conexión #{self.errores_conexion}: {str(e)}")
                logger.info(f"🔄 Reintentando en {self.tiempo_reconexion}s...")
                await asyncio.sleep(self.tiempo_reconexion)

    # ── Ciclo telemetría ──────────────────────────────────────────────────
    async def _ciclo_telemetria(self):
        """Envía datos de sensores en formato compatible con SOFÍ"""
        while self.conectado:
            try:
                sensores = await self.sensores.obtener_sensores_completo()
                msg = self._formatear_mensaje("telemetria", datos=sensores)
                await self.websocket.send(json.dumps(msg, ensure_ascii=False))

                self.telemetrias_enviadas += 1
                logger.info(
                    f"📡 Telemetría #{self.telemetrias_enviadas} | "
                    f"GPS: {sensores['gps']['lat']:.4f},{sensores['gps']['lon']:.4f} | "
                    f"BAT: {sensores['bateria']}% | TEMP: {sensores['temperatura_cpu']}°C"
                )

                await asyncio.sleep(self.intervalo_telemetria)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error enviando telemetría: {e}")
                await asyncio.sleep(2)

    # ── Ciclo escucha ─────────────────────────────────────────────────────
    async def _ciclo_escucha(self):
        """Recibe y procesa comandos enviados desde SOFÍ"""
        while self.conectado:
            try:
                mensaje = await asyncio.wait_for(self.websocket.recv(), timeout=120)
                datos = json.loads(mensaje)

                # Verificar firma si viene incluida
                if "firma" in datos:
                    firma_recibida = datos.pop("firma")
                    firma_calculada = firmar_paquete(datos)
                    if firma_recibida != firma_calculada:
                        logger.warning("⚠️ Mensaje con firma inválida — ignorado")
                        continue

                tipo = datos.get("tipo", "")

                if tipo == "bienvenida":
                    logger.info(f"🤝 Confirmación de SOFÍ: Ciclo {datos.get('ciclo')}")

                elif tipo == "comando":
                    logger.info(f"📥 Comando recibido: {datos.get('comando', '')}")
                    await self._ejecutar_orden(datos.get("comando", ""))

                elif tipo == "ping":
                    await self.websocket.send(json.dumps(self._formatear_mensaje("pong")))

                elif datos.get("estado") == "BLOQUEADO":
                    logger.critical(f"🚨 BLOQUEADO POR OSIRIS: {datos.get('razon', 'Sin motivo')}")
                    self.conectado = False
                    break

            except asyncio.TimeoutError:
                logger.debug("⏱️ Sin mensajes recientes — conexión activa")
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error en escucha: {e} — reintentando")
                await asyncio.sleep(2)

    # ── Ejecutar órdenes ──────────────────────────────────────────────────
    async def _ejecutar_orden(self, orden: str):
        """Ejecuta todas las acciones que ya tenía el código original"""
        self.comandos_ejecutados += 1
        orden_lower = orden.lower().strip()
        logger.info(f"⚡ Ejecutando orden #{self.comandos_ejecutados}: {orden[:60]}...")

        resultado = {"estado": "ejecutado", "orden": orden}

        if any(pal in orden_lower for pal in ["gps", "ubicación", "posición"]):
            resultado["datos"] = await self.sensores.obtener_gps_real()

        elif any(pal in orden_lower for pal in ["batería", "energía", "temperatura", "hardware"]):
            sensores = await self.sensores.obtener_sensores_completo()
            resultado["datos"] = {
                "bateria": sensores["bateria"],
                "temperatura": sensores["temperatura_cpu"],
                "memoria": sensores["memoria_disponible"]
            }

        elif any(pal in orden_lower for pal in ["foto", "cámara", "estigia"]):
            resultado["datos"] = self._tomar_foto()

        elif any(pal in orden_lower for pal in ["archivos", "organizar", "listar"]):
            ruta = "/sdcard/Download"
            try:
                archivos = os.listdir(ruta)
                resultado["datos"] = {"ruta": ruta, "cantidad": len(archivos), "lista": archivos[:10]}
            except Exception as e:
                resultado["datos"] = {"error": str(e)}

        else:
            resultado["datos"] = {"mensaje": "Orden recibida, sin acción específica definida"}

        # Enviar resultado de vuelta al cerebro
        if self.conectado and self.websocket:
            msg_respuesta = self._formatear_mensaje("respuesta", datos=resultado)
            await self.websocket.send(json.dumps(msg_respuesta, ensure_ascii=False))
            logger.info(f"📤 Resultado enviado a SOFÍ")

    def _tomar_foto(self) -> dict:
        """Función original mantenida tal cual"""
        ruta = f"/sdcard/DCIM/OSIRIS_{int(time.time())}.jpg"
        try:
            subprocess.run(
                ["termux-camera-photo", "-c", "0", ruta],
                timeout=10, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            return {"ruta": ruta, "estado": "foto_capturada", "timestamp": datetime.now().isoformat()}
        except Exception as e:
            return {"error": str(e), "estado": "fallido"}

    # ── Ping periódico ────────────────────────────────────────────────────
    async def _ping_periodico(self):
        """Mantiene conexión activa igual que el protocolo de SOFÍ"""
        while self.conectado:
            try:
                await asyncio.sleep(self.intervalo_ping)
                if self.conectado and self.websocket:
                    await self.websocket.send(json.dumps(self._formatear_mensaje("ping")))
                    logger.debug("💓 Latido enviado")
            except asyncio.CancelledError:
                break
            except Exception:
                break

    # ── Arranque principal ─────────────────────────────────────────────────
    async def iniciar(self):
        logger.info("=" * 70)
        logger.info("⚡ HERMES v9.1 — Fuerza Operativa")
        logger.info("=" * 70)
        await self.conectar_sofi()


# ═══════════════════════════════════════════════════════════════════════════
# EJECUCIÓN
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    hermes = HermesV9Operativo()
    try:
        asyncio.run(hermes.iniciar())
    except KeyboardInterrupt:
        logger.info("⛔ HERMES detenido por usuario")
    except Exception as e:
        logger.critical(f"❌ Error fatal: {e}", exc_info=True)
