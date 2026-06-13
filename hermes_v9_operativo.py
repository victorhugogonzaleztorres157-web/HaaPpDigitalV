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
# SENSORES DISPOSITIVO
# ═══════════════════════════════════════════════════════════════════════════

class SensoresDispositivo:
    """Abstracción de sensores — Soporta Termux real + simulación"""

    def __init__(self, en_termux: bool = True):
        self.en_termux = en_termux
        self.ultimo_gps = {"lat": 20.9674, "lon": -89.6237, "precision": 0}
        self.cache_bateria = 100
        self.cache_temp = 36.6

    async def obtener_gps_real(self) -> Dict:
        """
        [FIX-GPS] termux-location devuelve JSON, no texto LAT:/LON:.
        Parseamos correctamente.
        """
        if not self.en_termux:
            return self.simular_gps()
        try:
            resultado = subprocess.run(
                ['termux-location', '-p', 'network'],
                capture_output=True, text=True, timeout=10
            )
            if resultado.returncode == 0:
                geo = json.loads(resultado.stdout)
                lat = float(geo["latitude"])
                lon = float(geo["longitude"])
                acc = float(geo.get("accuracy", 10))
                self.ultimo_gps = {"lat": lat, "lon": lon, "precision": acc}
                logger.info(f"📍 GPS Real: {lat:.5f}, {lon:.5f} ±{acc}m")
                return self.ultimo_gps
        except Exception as e:
            logger.warning(f"⚠️ GPS Termux falló: {e} — usando fallback")
        return self.simular_gps()

    def simular_gps(self) -> Dict:
        lat = self.ultimo_gps["lat"] + (np.random.randn() * 0.001)
        lon = self.ultimo_gps["lon"] + (np.random.randn() * 0.001)
        return {"lat": lat, "lon": lon, "precision": int(np.random.randint(5, 50))}

    async def obtener_bateria(self) -> int:
        if not self.en_termux:
            return self.simular_bateria()
        try:
            # Intento 1: sysfs
            with open("/sys/class/power_supply/battery/capacity", "r") as f:
                bat = int(f.read().strip())
                self.cache_bateria = bat
                return bat
        except:
            pass
        try:
            # Intento 2: termux-battery-status (JSON)
            raw = subprocess.check_output(["termux-battery-status"], timeout=5)
            datos = json.loads(raw)
            bat = int(datos.get("percentage", self.cache_bateria))
            self.cache_bateria = bat
            return bat
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
                self.cache_temp = temp_raw / 1000
                return self.cache_temp
        except:
            return self.simular_temperatura()

    def simular_temperatura(self) -> float:
        self.cache_temp = 35 + np.random.randn() * 2 + abs(np.sin(time.time() / 100) * 1.5)
        return round(self.cache_temp, 1)

    async def obtener_sensores_completo(self) -> Dict:
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
            "memoria_disponible": os.popen(
                "free -h 2>/dev/null | grep Mem | awk '{print $7}'"
            ).read().strip() or "N/A"
        }


# ═══════════════════════════════════════════════════════════════════════════
# HERMES v9 — FUERZA OPERATIVA COMPLETA
# ═══════════════════════════════════════════════════════════════════════════

class HermesV9Operativo:
    """
    Fuerza Operativa de SOFÍ — Controlador de Dispositivo Termux.

    PROTOCOLO K'UHUL (sincronizado con sofi_v9_master_universal.py):
      ENVÍO   → {"origen": str, "comando": str, "lat": float, "lon": float}
      RECIBO  → {"sofi_blanca": str, "sofi_oscura": str, "firma_jhop": str, ...}

    El master no entiende {"tipo": "telemetria"} — todo va como paquete K'uhul.
    """

    def __init__(self):
        self.sofi_url        = os.getenv("SOFI_URL", "wss://haappdigitalv-core.onrender.com/ws/canal_kuhul")
        self.device_id       = os.getenv("HERMES_ID", "MERIDA_UNIDAD_01")
        self.tipo_dispositivo = os.getenv("HERMES_TIPO", "android_termux")

        self.conectado   = False
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.sensores    = SensoresDispositivo(en_termux=True)

        self.intervalo_telemetria  = int(os.getenv("HERMES_TELEMETRIA_INTERVALO", 10))
        self.timeout_reconexion    = int(os.getenv("HERMES_RECONEXION_TIMEOUT", 5))

        # Métricas
        self.telemetrias_enviadas = 0
        self.comandos_ejecutados  = 0
        self.errores_conexion     = 0
        self.tiempo_inicio        = datetime.now()

        logger.info("⚡ HERMES v9 Inicializado")
        logger.info(f"   ID       : {self.device_id}")
        logger.info(f"   Tipo     : {self.tipo_dispositivo}")
        logger.info(f"   Cerebro  : {self.sofi_url}")

    # ── Paquete K'uhul — formato que entiende el master ───────────────────
    def _paquete(self, comando: str, lat: float, lon: float, extra: dict = None) -> str:
        """
        Construye el paquete estándar K'uhul que espera MenteMadre.procesar().
        Todo mensaje al master usa este formato.
        """
        datos = {
            "origen":  self.device_id,
            "comando": comando,
            "lat":     lat,
            "lon":     lon,
        }
        if extra:
            datos.update(extra)
        return json.dumps(datos, ensure_ascii=False)

    # ── Conexión principal ────────────────────────────────────────────────
    async def conectar_sofi(self):
        while True:
            try:
                logger.info(f"🔗 Conectando a {self.sofi_url}...")
                async with websockets.connect(
                    self.sofi_url,
                    ping_interval=30,
                    ping_timeout=10,
                    max_size=10_000_000
                ) as websocket:
                    self.websocket    = websocket
                    self.conectado    = True
                    self.errores_conexion = 0
                    logger.info("✅ Conectado a SOFÍ v9 Cerebro — Canal K'uhul abierto")

                    # Identificación inicial en formato K'uhul
                    gps = await self.sensores.obtener_gps_real()
                    await websocket.send(self._paquete(
                        comando=f"Inicializando nodo Hermes {self.device_id} v9.0",
                        lat=gps["lat"], lon=gps["lon"],
                        extra={"version_hermes": "9.0.0", "tipo": self.tipo_dispositivo}
                    ))
                    logger.info(f"📨 Identificación K'uhul enviada")

                    # Tareas paralelas
                    telemetria_task  = asyncio.create_task(self._ciclo_telemetria())
                    escucha_task     = asyncio.create_task(self._ciclo_escucha())
                    ping_task        = asyncio.create_task(self._ping_periodico())  # [FIX-PING]

                    try:
                        await asyncio.gather(telemetria_task, escucha_task, ping_task)
                    except asyncio.CancelledError:
                        for t in (telemetria_task, escucha_task, ping_task):
                            t.cancel()
                        raise

            except Exception as e:
                self.conectado = False
                self.errores_conexion += 1
                logger.error(f"❌ Error de conexión #{self.errores_conexion}: {e}")
                logger.info(f"🔄 Reintentando en {self.timeout_reconexion}s...")
                await asyncio.sleep(self.timeout_reconexion)

    # ── Ciclo telemetría ──────────────────────────────────────────────────
    async def _ciclo_telemetria(self):
        """Envía telemetría periódica en formato K'uhul."""
        while self.conectado:
            try:
                sensores_data = await self.sensores.obtener_sensores_completo()
                gps = sensores_data["gps"]

                # Comando descriptivo para que Cortex lo indexe en el Plano correcto
                cmd = (
                    f"[TELEMETRIA] bateria={sensores_data['bateria']}% "
                    f"temp={sensores_data['temperatura_cpu']}°C "
                    f"mem={sensores_data['memoria_disponible']}"
                )

                await self.websocket.send(self._paquete(
                    comando=cmd,
                    lat=gps["lat"],
                    lon=gps["lon"],
                    extra={"reporte_sensores": sensores_data}
                ))
                self.telemetrias_enviadas += 1

                logger.info(
                    f"📡 Telemetría #{self.telemetrias_enviadas}: "
                    f"GPS({gps['lat']:.4f}, {gps['lon']:.4f}) "
                    f"BAT({sensores_data['bateria']}%) "
                    f"TEMP({sensores_data['temperatura_cpu']}°C)"
                )

                await asyncio.sleep(self.intervalo_telemetria)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error enviando telemetría: {e}")
                await asyncio.sleep(2)

    # ── Ciclo escucha ─────────────────────────────────────────────────────
    async def _ciclo_escucha(self):
        """
        Escucha respuestas del master (formato K'uhul) y ejecuta órdenes.
        [FIX-ESCUCHA] Ya no rompe el loop en errores transitorios.
        """
        while self.conectado:
            try:
                mensaje = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=120
                )
                datos = json.loads(mensaje)

                # Respuesta K'uhul estándar del master
                estado   = datos.get("estado", "")
                blanca   = datos.get("sofi_blanca", "")
                oscura   = datos.get("sofi_oscura", "")
                firma    = datos.get("firma_jhop", "")
                riesgo   = datos.get("riesgo_semantico", "")
                modo_nlp = datos.get("modo_nlp", "")

                if estado == "BLOQUEADO":
                    logger.warning(f"🚨 [OSIRIS] BLOQUEADO: {datos.get('motivo')}")
                    continue

                if firma:
                    logger.info(f"🔱 JHOP: {firma} | dist: {datos.get('distancia_km')} km")
                if oscura:
                    logger.info(f"🖤 Oscura: {oscura}")
                if blanca:
                    logger.info(f"🤍 Blanca: {blanca}")
                    # Si la orden es para este nodo — ejecutar
                    if "Hermes" in blanca or "hardware" in blanca.lower():
                        await self._ejecutar_orden_blanca(blanca)
                if riesgo and riesgo != "✅ Sin anomalías semánticas.":
                    logger.warning(f"⚠️ Riesgo: {riesgo}")
                if modo_nlp:
                    logger.debug(f"🧠 Modo NLP activo en Cerebro: {modo_nlp}")

            except asyncio.TimeoutError:
                logger.debug("⏱️ Timeout escucha (normal) — continuando")
                continue
            except asyncio.CancelledError:
                break
            except Exception as e:
                # [FIX-ESCUCHA] Error transitorio — no romper, solo loguear
                logger.error(f"❌ Error en escucha: {e} — reintentando en 2s")
                await asyncio.sleep(2)

    # ── Ejecutar orden de SofíBlanca ──────────────────────────────────────
    async def _ejecutar_orden_blanca(self, orden: str):
        """Ejecuta la orden táctica de SofíBlanca y reporta de vuelta al master."""
        self.comandos_ejecutados += 1
        orden_lower = orden.lower()
        logger.info(f"⚡ Ejecutando orden #{self.comandos_ejecutados}: {orden[:60]}")

        resultado = {}

        if "gps" in orden_lower or "triangular" in orden_lower:
            resultado = await self.sensores.obtener_gps_real()

        elif "bateria" in orden_lower or "hardware" in orden_lower:
            sensores = await self.sensores.obtener_sensores_completo()
            resultado = {
                "bateria":         sensores["bateria"],
                "temperatura_cpu": sensores["temperatura_cpu"],
                "memoria":         sensores["memoria_disponible"],
            }

        elif "foto" in orden_lower or "estigia" in orden_lower:
            resultado = self._tomar_foto()

        elif "organizar" in orden_lower or "archivos" in orden_lower:
            ruta = "/sdcard/Download"
            try:
                resultado = {"archivos": len(os.listdir(ruta)), "ruta": ruta}
            except Exception as e:
                resultado = {"error": str(e)}

        else:
            resultado = {"nota": f"Orden recibida sin handler específico: {orden[:80]}"}

        # Reportar resultado de vuelta al master en formato K'uhul
        if self.websocket and self.conectado:
            gps = await self.sensores.obtener_gps_real()
            try:
                await self.websocket.send(self._paquete(
                    comando=f"[REPORTE] {orden[:100]}",
                    lat=gps["lat"], lon=gps["lon"],
                    extra={"reporte_ejecucion": resultado}
                ))
                logger.info(f"📤 Reporte enviado al Cerebro: {resultado}")
            except Exception as e:
                logger.error(f"❌ Error enviando reporte: {e}")

    def _tomar_foto(self) -> dict:
        ruta = f"/sdcard/DCIM/OSIRIS_{int(time.time())}.jpg"
        try:
            subprocess.run(
                ["termux-camera-photo", "-c", "0", ruta],
                timeout=10, check=True
            )
            return {"ruta": ruta, "estado": "foto_capturada"}
        except Exception as e:
            return {"error": str(e)}

    # ── [FIX-PING] Ping lanzado correctamente ────────────────────────────
    async def _ping_periodico(self):
        """Mantiene viva la conexión enviando ping K'uhul cada 60s."""
        while self.conectado:
            try:
                await asyncio.sleep(60)
                if self.websocket and self.conectado:
                    gps = self.sensores.ultimo_gps  # sin llamada real — rápido
                    await self.websocket.send(self._paquete(
                        comando="[PING] Latido K'uhul Hermes activo",
                        lat=gps["lat"], lon=gps["lon"]
                    ))
                    logger.debug("💓 Ping K'uhul enviado")
            except asyncio.CancelledError:
                break
            except Exception:
                break

    # ── Punto de entrada ──────────────────────────────────────────────────
    async def iniciar(self):
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
