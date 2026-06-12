#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ==============================================================================
# ⚡ HERMES CORTEX — TOMA DE POSESIÓN TOTAL DEL SAMSUNG A03
# Arquitecto : Víctor Hugo González Torres (Lok / Osiris)
# Alias SOFÍ : Jarvis · Hermes · Cortex · Osiris Visual
# Archivo    : hermes_cortex.py
# Ejecución  : python hermes_cortex.py
#
# FUNCIONES:
#   ├── Sirve el Jarvis HTML en http://0.0.0.0:7777  (abre en Chrome del Samsung)
#   ├── WebSocket local en ws://0.0.0.0:7778         (puente biométrico↔SOFÍ)
#   ├── Telemetría real: GPS, batería, cámara (Termux-API)
#   ├── Organización Cortex de archivos del teléfono
#   ├── Enlace permanente al bus K'uhul de SOFÍ V9 (Render)
#   └── Enlace al AFU (Agente Financiero) para señales y tesorería
#
# LIBRERÍAS NECESARIAS (ver instrucciones abajo):
#   pip install websockets aiohttp aiofiles python-dotenv
#   pkg install termux-api python
# ==============================================================================

# ── INSTRUCCIONES DE INSTALACIÓN EN TERMUX ────────────────────────────────────
# 1. Instalar dependencias del sistema:
#    pkg update && pkg upgrade -y
#    pkg install python termux-api -y
#
# 2. Instalar librerías Python:
#    pip install websockets aiohttp aiofiles python-dotenv
#
# 3. Guardar este archivo:
#    nano hermes_cortex.py
#    (pegar el contenido, luego Ctrl+X → Y → Enter)
#
# 4. Dar permisos de Termux-API en Android:
#    Ajustes → Apps → Termux:API → Permisos → Activar todo
#
# 5. Ejecutar:
#    python hermes_cortex.py
#
# 6. Abrir en Chrome del Samsung:
#    http://localhost:7777
# ──────────────────────────────────────────────────────────────────────────────

import asyncio, hashlib, json, logging, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

# ── Dotenv opcional ────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── Librerías de red ───────────────────────────────────────────────────────────
try:
    import websockets
    import aiohttp
    from aiohttp import web
    NET_OK = True
except ImportError:
    NET_OK = False
    print("❌  Faltan librerías. Ejecuta:")
    print("    pip install websockets aiohttp aiofiles python-dotenv")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("HERMES")

# ==============================================================================
# ⚙️  CONFIGURACIÓN
# ==============================================================================
class CFG:
    PORT_HTTP = int(os.getenv("PORT_HTTP", 7777))   # Jarvis UI
    PORT_WS   = int(os.getenv("PORT_WS",   7778))   # WS local ↔ UI
    SOFI_URL  = os.getenv("SOFI_URL",
        "wss://haappdigitalv-core.onrender.com/ws/canal_kuhul")
    AFU_URL   = os.getenv("AFU_URL",
        "https://haappdigitalv-afu.onrender.com")
    NOMBRE    = os.getenv("HERMES_NOMBRE", "HaaPp_Samsung_A03_SOFI")
    # Ruta del HTML Jarvis (mismo directorio que este script)
    HTML_PATH = Path(__file__).parent / "sofi_jarvis_interface.html"
    SDCARD    = Path("/sdcard")
    DOWNLOAD  = Path("/sdcard/Download")
    DCIM      = Path("/sdcard/DCIM")
    LAT_BASE  = 20.9674
    LON_BASE  = -89.6237

# ==============================================================================
# 🔱  OSIRIS FORENSE (inline)
# ==============================================================================
def firmar(datos: dict) -> str:
    payload = json.dumps(datos, sort_keys=True, ensure_ascii=False) + "_12.3Hz_Kuhul_JHOP"
    return hashlib.sha256(payload.encode()).hexdigest()


# ==============================================================================
# 📡  TERMUX-API — Hardware real del Samsung
# ==============================================================================
class TermuxHardware:
    """Wrapper para todas las APIs de Termux-API."""

    @staticmethod
    def _run(cmd: list, timeout: int = 8) -> dict | list | str | None:
        try:
            raw = subprocess.check_output(cmd, timeout=timeout, stderr=subprocess.DEVNULL)
            text = raw.decode().strip()
            try:
                return json.loads(text)
            except Exception:
                return text
        except Exception as e:
            log.debug(f"termux-api error [{' '.join(cmd)}]: {e}")
            return None

    def gps(self) -> dict:
        """Ubicación real vía termux-location."""
        data = self._run(["termux-location", "-p", "network"], timeout=12)
        if data and "latitude" in data:
            return {
                "lat": float(data["latitude"]),
                "lon": float(data["longitude"]),
                "acc": float(data.get("accuracy", 0)),
                "provider": data.get("provider", "network"),
            }
        log.warning("[GPS] Fallback a base Mérida")
        return {"lat": CFG.LAT_BASE, "lon": CFG.LON_BASE, "acc": 999, "provider": "fallback"}

    def bateria(self) -> dict:
        """Estado de batería real."""
        data = self._run(["termux-battery-status"])
        if data:
            return {
                "pct":     data.get("percentage", 0),
                "cargando": data.get("status", "") == "CHARGING",
                "temp_bat": data.get("temperature", 0),
            }
        return {"pct": 0, "cargando": False, "temp_bat": 0}

    def foto(self, cam: int = 0) -> str | None:
        """Captura foto con cámara trasera (cam=0) o frontal (cam=1)."""
        ruta = str(CFG.DCIM / f"OSIRIS_{int(time.time())}.jpg")
        result = self._run(["termux-camera-photo", "-c", str(cam), ruta], timeout=15)
        if Path(ruta).exists():
            log.info(f"[ESTIGIA] Foto capturada: {ruta}")
            return ruta
        log.warning("[ESTIGIA] No se pudo capturar foto")
        return None

    def vibrar(self, ms: int = 300):
        """Vibración del dispositivo."""
        subprocess.Popen(["termux-vibrate", "-d", str(ms)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def notificacion(self, titulo: str, texto: str):
        """Notificación push en Android."""
        subprocess.Popen(
            ["termux-notification", "-t", titulo, "-c", texto, "--id", "sofi_hc"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def brillo(self, valor: int = 128):
        """Control de brillo (0-255)."""
        subprocess.Popen(
            ["termux-brightness", str(max(0, min(255, valor)))],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def volumen(self, tipo: str = "music", valor: int = 8):
        """Control de volumen."""
        subprocess.Popen(
            ["termux-volume", tipo, str(valor)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def hablar(self, texto: str, idioma: str = "es"):
        """Text-to-Speech — SOFÍ habla por el altavoz."""
        subprocess.Popen(
            ["termux-tts-speak", "-l", idioma, texto],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

    def sensores(self) -> dict:
        """Lee sensores disponibles del dispositivo."""
        data = self._run(["termux-sensor", "-s", "all", "-n", "1"], timeout=6)
        return data if isinstance(data, dict) else {}

    def listar_archivos(self, ruta: str = "/sdcard/Download") -> list:
        """Lista archivos de una carpeta."""
        try:
            p = Path(ruta)
            return [str(f) for f in sorted(p.iterdir()) if f.is_file()]
        except Exception:
            return []

    def organizar_archivos(self, ruta: str = "/sdcard/Download") -> dict:
        """
        Cortex local: clasifica archivos por extensión.
        Crea subcarpetas: IMG, VID, DOC, APK, AUDIO, OTROS
        """
        p = Path(ruta)
        cats = {
            "IMG":   [".jpg",".jpeg",".png",".gif",".webp",".heic"],
            "VID":   [".mp4",".mkv",".avi",".mov",".3gp"],
            "DOC":   [".pdf",".docx",".xlsx",".pptx",".txt",".csv"],
            "APK":   [".apk"],
            "AUDIO": [".mp3",".ogg",".wav",".flac",".m4a"],
        }
        movidos = {}
        for f in p.iterdir():
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            destino = "OTROS"
            for cat, exts in cats.items():
                if ext in exts:
                    destino = cat
                    break
            dest_dir = p / destino
            dest_dir.mkdir(exist_ok=True)
            target = dest_dir / f.name
            if not target.exists():
                f.rename(target)
                movidos[destino] = movidos.get(destino, 0) + 1
        total = sum(movidos.values())
        log.info(f"[CORTEX] Organización: {total} archivos clasificados en {ruta}")
        return {"ruta": ruta, "movidos": movidos, "total": total}


hw = TermuxHardware()


# ==============================================================================
# 🔗  ENLACE AL BUS K'UHUL (SOFÍ V9 en Render)
# ==============================================================================
class BusSofi:
    def __init__(self):
        self.ws        = None
        self.conectado = False
        self.ciclos    = 0
        self._clientes : set = set()   # clientes WS locales (UI Jarvis)

    def registrar_cliente(self, ws_local):
        self._clientes.add(ws_local)

    def desregistrar_cliente(self, ws_local):
        self._clientes.discard(ws_local)

    async def broadcast_local(self, msg: dict):
        """Envía mensaje a todos los clientes UI conectados."""
        texto = json.dumps(msg, ensure_ascii=False)
        muertos = set()
        for c in self._clientes:
            try:
                await c.send_str(texto)
            except Exception:
                muertos.add(c)
        self._clientes -= muertos

    async def conectar(self):
        """Bucle de conexión permanente al bus SOFÍ en Render."""
        log.info(f"[BUS] Conectando a SOFÍ: {CFG.SOFI_URL}")
        while True:
            try:
                async with websockets.connect(
                    CFG.SOFI_URL,
                    open_timeout=10,
                    ping_interval=20,
                    ping_timeout=15,
                ) as ws:
                    self.ws        = ws
                    self.conectado = True
                    log.info("[BUS] ✅ Canal K'uhul VIVO")
                    await self.broadcast_local({"tipo":"bus","estado":"CONECTADO"})

                    # Saludo inicial con telemetría
                    gps = hw.gps()
                    bat = hw.bateria()
                    await ws.send(json.dumps({
                        "origen":  CFG.NOMBRE,
                        "comando": "Hermes Cortex en línea — Samsung A03 tomando posesión",
                        "lat":     gps["lat"],
                        "lon":     gps["lon"],
                        "bio": {
                            "bat":    bat["pct"],
                            "cargando": bat["cargando"],
                            "temp_bat": bat["temp_bat"],
                        }
                    }))

                    async for raw in ws:
                        try:
                            paquete = json.loads(raw)
                        except Exception:
                            continue
                        self.ciclos += 1
                        await self._procesar_respuesta_sofi(paquete)

            except Exception as e:
                self.ws        = None
                self.conectado = False
                log.warning(f"[BUS] Desconectado: {e}. Reintento en 8s...")
                await self.broadcast_local({"tipo":"bus","estado":"DESCONECTADO"})
                await asyncio.sleep(8)

    async def _procesar_respuesta_sofi(self, paquete: dict):
        """Procesa la respuesta de SOFÍ V9 y actúa sobre el hardware."""
        blanca = paquete.get("sofi_blanca", "")
        oscura = paquete.get("sofi_oscura", "")

        # Reenviar a la UI Jarvis local
        await self.broadcast_local({**paquete, "tipo": "sofi_resp"})

        # SOFÍ ordena acción de hardware → Hermes ejecuta
        if "foto" in blanca.lower() or "estigia" in blanca.lower():
            ruta = hw.foto()
            await self.enviar(f"[HERMES] Foto Estigia capturada: {ruta}", hw.gps())
            hw.vibrar(200)

        elif "organizar" in blanca.lower() or "cortex" in blanca.lower():
            resultado = hw.organizar_archivos()
            await self.enviar(f"[CORTEX] {resultado['total']} archivos organizados", hw.gps())

        elif "vibrar" in blanca.lower() or "alerta" in blanca.lower():
            hw.vibrar(500)
            hw.notificacion("SOFÍ", blanca[:80])

        elif "hablar" in blanca.lower() or "habla" in blanca.lower():
            texto_tts = oscura if oscura else blanca
            hw.hablar(texto_tts[:200])

        elif "gps" in blanca.lower() or "triangular" in blanca.lower():
            gps = hw.gps()
            await self.enviar(
                f"[GPS] {gps['lat']:.5f}, {gps['lon']:.5f} ±{gps['acc']}m",
                gps
            )

        elif "bateria" in blanca.lower():
            bat = hw.bateria()
            await self.enviar(
                f"[BAT] {bat['pct']}% {'⚡' if bat['cargando'] else '🔋'} | Temp:{bat['temp_bat']}°C",
                hw.gps()
            )

        elif "brillo" in blanca.lower():
            hw.brillo(200)
        elif "noche" in blanca.lower() or "oscurecer" in blanca.lower():
            hw.brillo(30)

    async def enviar(self, comando: str, gps: dict = None, payload: dict = None):
        """Envía comando al bus K'uhul con telemetría."""
        if not self.ws:
            log.warning("[BUS] Sin conexión — comando en cola")
            return
        g   = gps or {"lat": CFG.LAT_BASE, "lon": CFG.LON_BASE}
        bat = hw.bateria()
        msg = {
            "origen":  CFG.NOMBRE,
            "comando": comando,
            "lat":     g["lat"],
            "lon":     g["lon"],
            "bio": {
                "bat":    bat["pct"],
                "hz":     12.3,
            },
        }
        if payload:
            msg["payload"] = payload
        try:
            await self.ws.send(json.dumps(msg, ensure_ascii=False))
        except Exception as e:
            log.warning(f"[BUS] Error al enviar: {e}")


bus = BusSofi()


# ==============================================================================
# 📈  POLLING AFU (Agente Financiero Universal)
# ==============================================================================
async def polling_afu():
    """Consulta el AFU cada 60s y envía estado financiero a la UI."""
    await asyncio.sleep(15)   # esperar a que todo esté listo
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{CFG.AFU_URL}/api/estado", timeout=aiohttp.ClientTimeout(total=8)
                ) as r:
                    if r.status == 200:
                        data = await r.json()
                        await bus.broadcast_local({"tipo": "afu_estado", "datos": data})
                        log.debug(f"[AFU] Estado recibido — ZYXSOF:{data.get('tesoreria',{}).get('balance_zyxsof','?')}")
        except Exception as e:
            log.debug(f"[AFU] No disponible: {e}")
        await asyncio.sleep(60)


# ==============================================================================
# 📡  TELEMETRÍA AUTOMÁTICA (cada 30s)
# ==============================================================================
async def telemetria_loop():
    """Envía telemetría real del Samsung al bus K'uhul cada 30s."""
    await asyncio.sleep(10)
    while True:
        await asyncio.sleep(30)
        try:
            gps = hw.gps()
            bat = hw.bateria()
            tele = {
                "origen":  CFG.NOMBRE,
                "comando": "",   # solo telemetría, sin comando
                "lat":     gps["lat"],
                "lon":     gps["lon"],
                "bio": {
                    "bat":     bat["pct"],
                    "cargando": bat["cargando"],
                    "temp_bat": bat["temp_bat"],
                    "hz":      12.3,
                }
            }
            if bus.ws:
                await bus.ws.send(json.dumps(tele))
            await bus.broadcast_local({"tipo": "telemetria", "gps": gps, "bat": bat})
        except Exception as e:
            log.debug(f"[TELE] Error: {e}")


# ==============================================================================
# 🌐  SERVIDOR HTTP — Sirve el Jarvis HTML + WebSocket local
# ==============================================================================
async def handle_jarvis(request):
    """Sirve el HTML del Jarvis."""
    if CFG.HTML_PATH.exists():
        content = CFG.HTML_PATH.read_text(encoding="utf-8")
    else:
        content = "<h1 style='color:#00ffcc;background:#020813;padding:20px'>sofi_jarvis_interface.html no encontrado.<br>Asegúrate de que esté en el mismo directorio.</h1>"
    return web.Response(text=content, content_type="text/html", charset="utf-8")


async def handle_estado(request):
    """API REST local — estado del Hermes."""
    gps = hw.gps()
    bat = hw.bateria()
    return web.json_response({
        "nombre":    CFG.NOMBRE,
        "bus_ok":    bus.conectado,
        "ciclos":    bus.ciclos,
        "gps":       gps,
        "bateria":   bat,
        "clientes":  len(bus._clientes),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


async def handle_cmd(request):
    """API REST local — ejecutar comando directo."""
    data = await request.json()
    cmd  = data.get("comando", "")
    gps  = hw.gps()
    await bus.enviar(cmd, gps)
    return web.json_response({"ok": True, "enviado": cmd})


async def handle_ws_local(request):
    """
    WebSocket local entre el Jarvis HTML (en Chrome del Samsung)
    y este Hermes Cortex. Actúa como puente bidireccional.
    """
    ws_local = web.WebSocketResponse()
    await ws_local.prepare(request)
    bus.registrar_cliente(ws_local)
    log.info("[WS-LOCAL] Cliente UI conectado")

    # Bienvenida
    gps = hw.gps()
    bat = hw.bateria()
    await ws_local.send_json({
        "tipo":    "bienvenida",
        "mensaje": f"⚡ Hermes Cortex activo — {CFG.NOMBRE}",
        "bus_ok":  bus.conectado,
        "gps":     gps,
        "bat":     bat,
    })

    try:
        async for msg in ws_local:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    paquete = json.loads(msg.data)
                    cmd     = paquete.get("comando", "").strip()
                    if not cmd:
                        continue

                    # Comandos locales del Hermes
                    cmd_l = cmd.lower()
                    if cmd_l == "foto" or cmd_l == "estigia":
                        ruta = hw.foto()
                        await ws_local.send_json({"tipo":"hw","resultado": f"Foto: {ruta}"})

                    elif cmd_l.startswith("organizar"):
                        ruta = cmd_l.replace("organizar","").strip() or str(CFG.DOWNLOAD)
                        res  = hw.organizar_archivos(ruta)
                        await ws_local.send_json({"tipo":"cortex","resultado": res})

                    elif cmd_l == "gps" or cmd_l == "triangular":
                        g = hw.gps()
                        await ws_local.send_json({"tipo":"gps","gps": g})

                    elif cmd_l == "bateria":
                        b = hw.bateria()
                        await ws_local.send_json({"tipo":"bat","bat": b})

                    elif cmd_l.startswith("hablar "):
                        hw.hablar(cmd[7:])
                        await ws_local.send_json({"tipo":"tts","ok": True})

                    elif cmd_l.startswith("vibrar"):
                        hw.vibrar(500)
                        await ws_local.send_json({"tipo":"vib","ok": True})

                    elif cmd_l == "estado":
                        g = hw.gps(); b = hw.bateria()
                        await ws_local.send_json({
                            "tipo":"estado","gps":g,"bat":b,
                            "bus_ok":bus.conectado,"ciclos":bus.ciclos
                        })

                    elif cmd_l.startswith("afu "):
                        # Relay al AFU
                        endpoint = cmd_l.replace("afu ","")
                        async with aiohttp.ClientSession() as s:
                            async with s.get(
                                f"{CFG.AFU_URL}/api/{endpoint}",
                                timeout=aiohttp.ClientTimeout(total=6)
                            ) as r:
                                d = await r.json()
                                await ws_local.send_json({"tipo":"afu","datos":d})

                    else:
                        # Reenviar al bus K'uhul (SOFÍ V9)
                        gps_now = hw.gps()
                        await bus.enviar(cmd, gps_now)

                except Exception as e:
                    await ws_local.send_json({"tipo":"error","msg": str(e)})

            elif msg.type in (aiohttp.WSMsgType.ERROR, aiohttp.WSMsgType.CLOSE):
                break

    except Exception:
        pass
    finally:
        bus.desregistrar_cliente(ws_local)
        log.info("[WS-LOCAL] Cliente UI desconectado")

    return ws_local


# ==============================================================================
# 🚀  ARRANQUE PRINCIPAL
# ==============================================================================
async def main():
    print("""
╔══════════════════════════════════════════════════════╗
║  ⚡ HERMES CORTEX — HaaPpDigitalV                    ║
║  Toma de Posesión: Samsung A03                       ║
║  Frecuencia Base : 12.3 Hz K'uhul                    ║
╚══════════════════════════════════════════════════════╝
    """)

    if not CFG.HTML_PATH.exists():
        log.warning(f"⚠️  HTML no encontrado en: {CFG.HTML_PATH}")
        log.warning("    Asegúrate de que sofi_jarvis_interface.html esté en el mismo directorio.")

    # ── App HTTP / WS local ──────────────────────────────────────────────────
    app = web.Application()
    app.router.add_get("/",         handle_jarvis)
    app.router.add_get("/estado",   handle_estado)
    app.router.add_post("/cmd",     handle_cmd)
    app.router.add_get("/ws",       handle_ws_local)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", CFG.PORT_HTTP)
    await site.start()

    log.info(f"🌐 Jarvis UI → http://localhost:{CFG.PORT_HTTP}")
    log.info(f"📡 WS local  → ws://localhost:{CFG.PORT_HTTP}/ws")
    log.info(f"🔗 Bus SOFÍ  → {CFG.SOFI_URL}")
    log.info(f"💰 AFU URL   → {CFG.AFU_URL}")

    # Notificación Android
    hw.notificacion("SOFÍ · Hermes Cortex",
                    f"Sistema activo — Abre Chrome en localhost:{CFG.PORT_HTTP}")
    hw.vibrar(400)

    # ── Tareas paralelas ─────────────────────────────────────────────────────
    await asyncio.gather(
        bus.conectar(),       # Enlace permanente a SOFÍ V9 en Render
        telemetria_loop(),    # Telemetría GPS/batería cada 30s
        polling_afu(),        # Estado financiero cada 60s
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("⚡ Hermes Cortex detenido.")
