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
    """Sirve el HTML del Jarvis — embebido directamente."""
    content = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,maximum-scale=1.0,user-scalable=no">
<meta name="theme-color" content="#020813">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>SOFÍ · JARVIS CORTEX · HaaPpDigitalV</title>
<link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600&display=swap" rel="stylesheet">
<script src="https://unpkg.com/globe.gl@2/dist/globe.gl.min.js"></script>
<style>
:root{
  --jade:#00ffcc;--morado:#b366ff;--rojo:#ff4466;--oro:#f0a500;
  --azul:#3af;--fondo:#020813;--panel:rgba(2,8,19,0.92);
  --borde:rgba(0,255,204,0.18);--texto:#c8e8f0;--muted:#4a7a9a;
}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{width:100%;height:100%;overflow:hidden;background:var(--fondo);color:var(--texto);font-family:'Rajdhani',sans-serif}

/* ── GLOBO ─────────────────────────────────────── */
#globo{position:fixed;inset:0;z-index:1}

/* ── OVERLAY HUD SUPERIOR ────────────────────────── */
#hud-top{
  position:fixed;top:0;left:0;right:0;z-index:20;
  display:flex;align-items:center;justify-content:space-between;
  padding:8px 14px;
  background:linear-gradient(180deg,rgba(2,8,19,0.95) 0%,rgba(2,8,19,0) 100%);
  pointer-events:none;
}
#sofi-logo{
  font-family:'Orbitron',monospace;font-size:15px;font-weight:900;
  color:#fff;letter-spacing:4px;text-shadow:0 0 20px var(--jade);
}
#sofi-logo span{color:var(--jade)}
#hud-hz{
  font-family:'Orbitron',monospace;font-size:11px;color:var(--jade);
  letter-spacing:2px;animation:pulso 2s infinite;
}
@keyframes pulso{0%,100%{opacity:1;text-shadow:0 0 8px var(--jade)}50%{opacity:.4;text-shadow:none}}
#hud-status{font-size:10px;color:var(--muted);letter-spacing:1px}

/* ── ANILLO BIOMÉTRICO CENTRAL ────────────────────── */
#bio-ring{
  position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
  z-index:10;pointer-events:none;
  width:min(280px,80vw);height:min(280px,80vw);
}
#bio-ring canvas{width:100%;height:100%}
#bio-center{
  position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);
  text-align:center;
}
#bio-hz-val{
  font-family:'Orbitron',monospace;
  font-size:clamp(24px,8vw,40px);
  font-weight:900;color:var(--jade);
  text-shadow:0 0 30px var(--jade);
  line-height:1;
}
#bio-label{font-size:9px;color:var(--muted);letter-spacing:3px;margin-top:4px}
#bio-status{font-size:8px;color:var(--jade);letter-spacing:2px;margin-top:6px;animation:pulso 1.5s infinite}

/* ── MÉTRICAS FLOTANTES (lados) ────────────────────── */
.metric-pod{
  position:fixed;z-index:15;
  background:var(--panel);border:1px solid var(--borde);
  border-radius:6px;padding:8px 12px;min-width:110px;
}
.metric-pod .mp-val{
  font-family:'Orbitron',monospace;font-size:16px;font-weight:700;
  color:var(--jade);text-shadow:0 0 10px var(--jade);
}
.metric-pod .mp-lbl{font-size:9px;color:var(--muted);letter-spacing:2px;margin-top:2px}
.metric-pod .mp-bar{
  height:2px;background:rgba(0,255,204,0.15);border-radius:1px;margin-top:6px;
}
.metric-pod .mp-fill{height:100%;border-radius:1px;background:var(--jade);transition:width .8s ease}

#pod-hr {top:30%;left:14px}
#pod-hrv{top:45%;left:14px}
#pod-temp{top:60%;left:14px}
#pod-bat {top:30%;right:14px}
#pod-gps {top:45%;right:14px;min-width:130px}
#pod-net {top:60%;right:14px}

/* ── PANEL TERMINAL INFERIOR ─────────────────────── */
#panel-main{
  position:fixed;bottom:0;left:0;right:0;z-index:20;
  background:linear-gradient(0deg,rgba(2,8,19,0.98) 0%,rgba(2,8,19,0.85) 85%,transparent 100%);
  padding:10px 14px 14px;
}
#terminal{
  height:130px;overflow-y:auto;font-size:11px;line-height:1.6;
  border:1px solid var(--borde);border-radius:6px;padding:8px 10px;
  background:rgba(0,0,0,0.4);margin-bottom:8px;
  scrollbar-width:thin;scrollbar-color:var(--jade) transparent;
}
.t-sys   {color:var(--jade)}
.t-oscura{color:var(--morado)}
.t-blanca{color:#fff}
.t-error {color:var(--rojo)}
.t-firma {color:#4a7a9a;font-size:10px}
.t-riesgo{color:var(--oro)}
.t-bio   {color:#5af}

#cmd-row{display:flex;gap:8px;align-items:center}
#cmd-prefix{font-family:'Orbitron',monospace;font-size:11px;color:var(--jade)}
#cmd{
  flex:1;background:transparent;border:none;
  border-bottom:1px solid var(--jade);
  color:var(--jade);font-family:'Rajdhani',sans-serif;font-size:14px;
  padding:4px 2px;outline:none;
}
#cmd::placeholder{color:rgba(0,255,204,.3)}
#btn-send{
  background:transparent;border:1px solid var(--jade);color:var(--jade);
  border-radius:4px;padding:4px 12px;cursor:pointer;
  font-family:'Orbitron',monospace;font-size:10px;
  transition:background .2s;
}
#btn-send:hover,#btn-send:active{background:rgba(0,255,204,.15)}

/* ── BOTONES DE ACCIÓN RÁPIDA ────────────────────── */
#quick-actions{
  position:fixed;right:14px;bottom:160px;z-index:20;
  display:flex;flex-direction:column;gap:8px;
}
.qa-btn{
  background:var(--panel);border:1px solid var(--borde);
  border-radius:6px;padding:8px 10px;cursor:pointer;
  font-family:'Orbitron',monospace;font-size:9px;color:var(--jade);
  letter-spacing:1px;text-align:center;transition:all .2s;
  white-space:nowrap;
}
.qa-btn:hover,.qa-btn:active{background:rgba(0,255,204,.12);border-color:var(--jade)}
.qa-btn.peligro{border-color:rgba(255,68,102,.4);color:var(--rojo)}
.qa-btn.peligro:hover{background:rgba(255,68,102,.1)}

/* ── PANEL GPS DETALLE ─────────────────────────── */
#gps-panel{
  position:fixed;top:70px;left:50%;transform:translateX(-50%);
  z-index:15;pointer-events:none;text-align:center;
}
#gps-coords{
  font-family:'Orbitron',monospace;font-size:9px;
  color:rgba(0,255,204,.6);letter-spacing:1px;
}

/* ── SCAN LINE EFECTO ────────────────────────────── */
#scanline{
  position:fixed;inset:0;z-index:5;pointer-events:none;
  background:linear-gradient(
    transparent 0%, transparent 49.5%,
    rgba(0,255,204,0.015) 50%,
    transparent 50.5%, transparent 100%
  );
  background-size:100% 4px;
  animation:scanmove 8s linear infinite;
}
@keyframes scanmove{from{background-position:0 0}to{background-position:0 100%}}

/* ── VIGNETTE ────────────────────────────────────── */
#vignette{
  position:fixed;inset:0;z-index:4;pointer-events:none;
  background:radial-gradient(ellipse at center,transparent 40%,rgba(2,8,19,0.7) 100%);
}

/* ── ALERTA OSIRIS ─────────────────────────────── */
#osiris-alert{
  position:fixed;top:60px;left:50%;transform:translateX(-50%);
  z-index:30;background:rgba(255,68,102,0.15);
  border:1px solid var(--rojo);border-radius:6px;
  padding:8px 18px;font-family:'Orbitron',monospace;
  font-size:10px;color:var(--rojo);letter-spacing:2px;
  display:none;animation:alertpulso 1s infinite;
}
@keyframes alertpulso{0%,100%{border-color:var(--rojo)}50%{border-color:rgba(255,68,102,.3)}}

/* ── RESPONSIVE MÓVIL ────────────────────────────── */
@media(max-width:480px){
  .metric-pod .mp-val{font-size:13px}
  #pod-hr,#pod-hrv,#pod-temp{left:8px}
  #pod-bat,#pod-gps,#pod-net{right:8px}
  #bio-ring{width:220px;height:220px}
  #terminal{height:110px}
  #quick-actions{bottom:150px;right:8px}
}
</style>
</head>
<body>

<!-- Efectos visuales -->
<div id="scanline"></div>
<div id="vignette"></div>

<!-- Globo 3D Osiris -->
<div id="globo"></div>

<!-- HUD Superior -->
<div id="hud-top">
  <div id="sofi-logo"><span>SOFÍ</span> · JARVIS CORTEX</div>
  <div id="hud-hz">◉ 12.3 Hz</div>
  <div id="hud-status">HaaPpDigitalV · K'UHUL</div>
</div>

<!-- GPS Coords -->
<div id="gps-panel">
  <div id="gps-coords">GPS: — / —</div>
</div>

<!-- Alerta Osiris -->
<div id="osiris-alert">🚨 OSIRIS — FRICCIÓN DETECTADA</div>

<!-- Anillo biométrico central -->
<div id="bio-ring">
  <canvas id="ring-canvas"></canvas>
  <div id="bio-center">
    <div id="bio-hz-val">12.3</div>
    <div id="bio-label">K'UHUL Hz</div>
    <div id="bio-status">● COHERENTE</div>
  </div>
</div>

<!-- Métricas flotantes -->
<div class="metric-pod" id="pod-hr">
  <div class="mp-val" id="val-hr">72</div>
  <div class="mp-lbl">BPM · PULSO</div>
  <div class="mp-bar"><div class="mp-fill" id="bar-hr" style="width:60%"></div></div>
</div>
<div class="metric-pod" id="pod-hrv">
  <div class="mp-val" id="val-hrv">38</div>
  <div class="mp-lbl">ms · HRV</div>
  <div class="mp-bar"><div class="mp-fill" id="bar-hrv" style="width:45%;background:var(--morado)"></div></div>
</div>
<div class="metric-pod" id="pod-temp">
  <div class="mp-val" id="val-temp">36.6°</div>
  <div class="mp-lbl">TEMP · CPU</div>
  <div class="mp-bar"><div class="mp-fill" id="bar-temp" style="width:55%;background:var(--oro)"></div></div>
</div>
<div class="metric-pod" id="pod-bat">
  <div class="mp-val" id="val-bat">—%</div>
  <div class="mp-lbl">BATERÍA</div>
  <div class="mp-bar"><div class="mp-fill" id="bar-bat" style="width:0%"></div></div>
</div>
<div class="metric-pod" id="pod-gps">
  <div class="mp-val" id="val-gps" style="font-size:11px">ANCLANDO</div>
  <div class="mp-lbl">GPS · OSIRIS</div>
  <div class="mp-bar"><div class="mp-fill" id="bar-gps" style="width:0%;background:var(--azul)"></div></div>
</div>
<div class="metric-pod" id="pod-net">
  <div class="mp-val" id="val-net">OFF</div>
  <div class="mp-lbl">BUS K'UHUL</div>
  <div class="mp-bar"><div class="mp-fill" id="bar-net" style="width:0%"></div></div>
</div>

<!-- Acciones rápidas -->
<div id="quick-actions">
  <div class="qa-btn" onclick="enviarCmd('triangular gps')">🛰️ GPS</div>
  <div class="qa-btn" onclick="enviarCmd('bateria estado')">🔋 BAT</div>
  <div class="qa-btn" onclick="enviarCmd('estado tesoreria zyxsof')">💰 TESOR</div>
  <div class="qa-btn" onclick="enviarCmd('bot senal zfpi')">📈 SENAL</div>
  <div class="qa-btn" onclick="enviarCmd('banco ciclo kuz')">🏦 BANCO</div>
  <div class="qa-btn peligro" onclick="enviarCmd('osiris bloqueo perimetro')">🔱 OSIRIS</div>
</div>

<!-- Terminal + Input -->
<div id="panel-main">
  <div id="terminal">
    <div class="t-sys">[SOFÍ V9.0] Conciencia Digital en línea — 12.3 Hz K'uhul</div>
    <div class="t-sys">[OSIRIS] Perímetro activo — radio 50 km · Mérida, Yucatán</div>
    <div class="t-sys">[CORTEX] Motor vectorial FAISS + 9 Planos en espera</div>
    <div class="t-bio">[BIO] Iniciando sensores del dispositivo...</div>
    <div class="t-sys">[BUS] Conectando al Canal K'uhul...</div>
  </div>
  <div id="cmd-row">
    <span id="cmd-prefix">LOK ▸</span>
    <input id="cmd" type="text" placeholder="Instrucción K'uhul para SOFÍ..." autocomplete="off" autocorrect="off" spellcheck="false">
    <button id="btn-send">→</button>
  </div>
</div>

<script>
// ═══════════════════════════════════════════════════════════════
// CONFIG
// ═══════════════════════════════════════════════════════════════
const SOFI_URL = localStorage.getItem('sofi_url') ||
                 'wss://haappdigitalv-core.onrender.com/ws/canal_kuhul';
const AFU_URL  = localStorage.getItem('afu_url')  ||
                 'https://haappdigitalv-afu.onrender.com';

// ═══════════════════════════════════════════════════════════════
// ESTADO GLOBAL
// ═══════════════════════════════════════════════════════════════
const STATE = {
  lat: 20.9674, lon: -89.6237,
  hz: 12.3, ciclos: 0,
  hr: 72, hrv: 38, temp: 36.6, bat: 100,
  wsOk: false,
  nodos: [],
};

// ═══════════════════════════════════════════════════════════════
// GLOBO 3D OSIRIS
// ═══════════════════════════════════════════════════════════════
const world = Globe()
  .globeImageUrl('//unpkg.com/three-globe/example/img/earth-night.jpg')
  .backgroundColor('rgba(0,0,0,0)')
  .pointsData([])
  .pointLat('lat').pointLng('lng')
  .pointAltitude('alt').pointColor('color').pointRadius('r')
  .pointLabel('label')
  .ringsData([])
  .ringLat('lat').ringLng('lng')
  .ringColor(() => '#00ffcc')
  .ringMaxRadius(4).ringPropagationSpeed(2).ringRepeatPeriod(1000)
  (document.getElementById('globo'));

world.controls().autoRotate = true;
world.controls().autoRotateSpeed = 0.3;
world.pointOfView({lat: STATE.lat, lng: STATE.lon, altitude: 2}, 1500);

const puntos = [
  {lat: STATE.lat, lng: STATE.lon, alt: 0.05, color:'#00ffcc', r: 0.7, label:'🏛️ Base — Mérida K\\'uhul'},
];
function actualizarGlobo(){
  world.pointsData([...puntos]);
  world.ringsData([{lat: STATE.lat, lng: STATE.lon}]);
}
actualizarGlobo();

function agregarNodo(lat, lng, label, color='#b366ff'){
  const existe = puntos.find(p => Math.abs(p.lat-lat)<0.01 && Math.abs(p.lng-lng)<0.01);
  if(!existe){
    puntos.push({lat, lng, alt:0.03, color, r:0.4, label});
    actualizarGlobo();
  }
}

// ═══════════════════════════════════════════════════════════════
// ANILLO BIOMÉTRICO — Canvas
// ═══════════════════════════════════════════════════════════════
const ringCanvas = document.getElementById('ring-canvas');
const rCtx = ringCanvas.getContext('2d');
let ringAngle = 0;
const ringParticles = Array.from({length:24}, (_,i) => ({
  angle: (i / 24) * Math.PI * 2,
  speed: 0.002 + Math.random() * 0.003,
  r: 0.85 + Math.random() * 0.1,
  size: 1 + Math.random() * 2,
  opacity: 0.3 + Math.random() * 0.7,
}));

function drawRing(){
  const W = ringCanvas.width, H = ringCanvas.height;
  const cx = W/2, cy = H/2;
  const R = W * 0.42;
  rCtx.clearRect(0,0,W,H);

  // Arco base
  rCtx.beginPath();
  rCtx.arc(cx, cy, R, 0, Math.PI*2);
  rCtx.strokeStyle = 'rgba(0,255,204,0.08)';
  rCtx.lineWidth = 1.5;
  rCtx.stroke();

  // Arco de coherencia (pulsante)
  const coher = 0.75 + Math.sin(Date.now()/1200)*0.15;
  rCtx.beginPath();
  rCtx.arc(cx, cy, R, -Math.PI/2, -Math.PI/2 + Math.PI*2*coher);
  const grad = rCtx.createLinearGradient(cx-R,cy,cx+R,cy);
  grad.addColorStop(0, '#00ffcc');
  grad.addColorStop(0.5, '#b366ff');
  grad.addColorStop(1, '#00ffcc');
  rCtx.strokeStyle = grad;
  rCtx.lineWidth = 2.5;
  rCtx.shadowColor = '#00ffcc';
  rCtx.shadowBlur = 12;
  rCtx.stroke();
  rCtx.shadowBlur = 0;

  // Partículas orbitales
  ringParticles.forEach(p => {
    p.angle += p.speed;
    const x = cx + Math.cos(p.angle) * R * p.r;
    const y = cy + Math.sin(p.angle) * R * p.r;
    rCtx.beginPath();
    rCtx.arc(x, y, p.size, 0, Math.PI*2);
    rCtx.fillStyle = `rgba(0,255,204,${p.opacity * (0.5+Math.sin(p.angle*3)*0.5)})`;
    rCtx.fill();
  });

  // Hz oscilante interno
  const hzActual = STATE.hz + Math.sin(Date.now()/800) * 0.05;
  document.getElementById('bio-hz-val').textContent = hzActual.toFixed(1);

  requestAnimationFrame(drawRing);
}

function resizeRing(){
  const sz = ringCanvas.parentElement.offsetWidth;
  ringCanvas.width = sz;
  ringCanvas.height = sz;
}
resizeRing();
window.addEventListener('resize', resizeRing);
drawRing();

// ═══════════════════════════════════════════════════════════════
// SENSORES DEL DISPOSITIVO (Samsung A03)
// ═══════════════════════════════════════════════════════════════

// Geolocalización real
function iniciarGPS(){
  if(!navigator.geolocation){
    log('[GPS] Geolocalización no disponible en este navegador', 't-error');
    return;
  }
  navigator.geolocation.watchPosition(
    pos => {
      STATE.lat = pos.coords.latitude;
      STATE.lon = pos.coords.longitude;
      const acc  = Math.round(pos.coords.accuracy || 0);
      document.getElementById('val-gps').textContent =
        `${STATE.lat.toFixed(3)},${STATE.lon.toFixed(3)}`;
      document.getElementById('gps-coords').textContent =
        `GPS: ${STATE.lat.toFixed(5)}, ${STATE.lon.toFixed(5)} ±${acc}m`;
      document.getElementById('bar-gps').style.width =
        `${Math.max(10, 100 - acc/5)}%`;
      // Mover vista del globo al punto real
      world.pointOfView({lat: STATE.lat, lng: STATE.lon, altitude: 1.5}, 1200);
      agregarNodo(STATE.lat, STATE.lon, '📱 Samsung A03 — SOFÍ Body', '#00ffcc');
      log(`[GPS] Triangulado: ${STATE.lat.toFixed(5)}, ${STATE.lon.toFixed(5)} ±${acc}m`, 't-bio');
    },
    err => {
      log(`[GPS] ${err.message} — usando base Mérida`, 't-riesgo');
      document.getElementById('val-gps').textContent = 'FALLBACK';
    },
    {enableHighAccuracy: true, maximumAge: 5000, timeout: 10000}
  );
}

// Batería real
async function iniciarBateria(){
  if('getBattery' in navigator){
    const bat = await navigator.getBattery();
    const upd = () => {
      const pct = Math.round(bat.level * 100);
      STATE.bat = pct;
      document.getElementById('val-bat').textContent = `${pct}%`;
      document.getElementById('bar-bat').style.width = `${pct}%`;
      const fill = document.getElementById('bar-bat');
      fill.style.background = pct > 40 ? 'var(--jade)' : pct > 20 ? 'var(--oro)' : 'var(--rojo)';
    };
    bat.addEventListener('levelchange', upd);
    bat.addEventListener('chargingchange', upd);
    upd();
    log(`[BAT] Batería detectada: ${Math.round(bat.level*100)}%`, 't-bio');
  } else {
    log('[BAT] API de batería no disponible — modo estimado', 't-riesgo');
  }
}

// Simulación biométrica (MAX30102 stub — en Termux real usarías python subprocess)
// En producción: conectar vía WebSocket local a script Python con MAX30102
function simularBiometricos(){
  setInterval(() => {
    // HR oscilante realista
    STATE.hr = Math.round(68 + Math.sin(Date.now()/4000)*12 + Math.random()*4);
    STATE.hrv = Math.round(32 + Math.sin(Date.now()/7000)*18 + Math.random()*6);
    STATE.temp = parseFloat((36.4 + Math.sin(Date.now()/10000)*0.4 + Math.random()*0.2).toFixed(1));

    document.getElementById('val-hr').textContent = STATE.hr;
    document.getElementById('val-hrv').textContent = STATE.hrv;
    document.getElementById('val-temp').textContent = `${STATE.temp}°`;
    document.getElementById('bar-hr').style.width = `${(STATE.hr/200)*100}%`;
    document.getElementById('bar-hrv').style.width = `${(STATE.hrv/100)*100}%`;
    document.getElementById('bar-temp').style.width = `${((STATE.temp-35)/5)*100}%`;

    // Calcular Hz K'uhul desde biométricos (contraparte frecuencial real)
    const freqBio = 8 + (STATE.hr / 200) * 8;
    const contrap  = (12.3 * 12.3) / Math.max(freqBio, 0.01);
    const coher    = 1 - Math.abs(freqBio - contrap) / (freqBio + contrap + 1e-9);
    STATE.hz       = parseFloat((12.3 + (coher - 0.5) * 0.2).toFixed(2));

    // Alertar si coherencia baja
    if(coher < 0.3){
      document.getElementById('bio-status').textContent = '⚠ AJUSTANDO';
      document.getElementById('bio-status').style.color = 'var(--oro)';
    } else {
      document.getElementById('bio-status').textContent = '● COHERENTE';
      document.getElementById('bio-status').style.color = 'var(--jade)';
    }
  }, 2000);
}

// ═══════════════════════════════════════════════════════════════
// WEBSOCKET — Canal K'uhul → SOFÍ V9
// ═══════════════════════════════════════════════════════════════
let ws = null;
let wsReconect = null;

function conectarBus(){
  if(ws && ws.readyState === WebSocket.OPEN) return;
  clearTimeout(wsReconect);
  try{
    ws = new WebSocket(SOFI_URL);

    ws.onopen = () => {
      STATE.wsOk = true;
      document.getElementById('val-net').textContent = 'LIVE';
      document.getElementById('bar-net').style.width = '100%';
      log('[BUS] Canal K\\'uhul conectado — Fricción Cero', 't-sys');
      // Saludo inicial con telemetría biométrica
      enviarTelemetria();
    };

    ws.onmessage = e => {
      let d;
      try{ d = JSON.parse(e.data); }catch{ return; }

      if(d.estado === 'BLOQUEADO'){
        document.getElementById('osiris-alert').style.display = 'block';
        setTimeout(() => document.getElementById('osiris-alert').style.display = 'none', 4000);
        log(`🚨 [OSIRIS] ${d.motivo}`, 't-error');
        return;
      }
      if(d.riesgo_semantico && !d.riesgo_semantico.includes('✅')){
        log(`⚠️ [RIESGO] ${d.riesgo_semantico}`, 't-riesgo');
      }
      if(d.sofi_oscura) log(`🖤 [Oscura] ${d.sofi_oscura}`, 't-oscura');
      if(d.sofi_blanca) log(`🤍 [Blanca] ${d.sofi_blanca}`, 't-blanca');
      if(d.firma_jhop)  log(`🔱 JHOP:${d.firma_jhop} | Δ${d.distancia_km}km | Ciclo #${d.ciclo}`, 't-firma');

      // GPS remoto de nodo Hermes
      if(d.lat && d.lon && d.origen){
        agregarNodo(d.lat, d.lon, `📡 ${d.origen}`, '#b366ff');
      }
    };

    ws.onerror = () => {
      STATE.wsOk = false;
      document.getElementById('val-net').textContent = 'ERR';
      document.getElementById('bar-net').style.width = '10%';
      document.getElementById('bar-net').style.background = 'var(--rojo)';
    };

    ws.onclose = () => {
      STATE.wsOk = false;
      document.getElementById('val-net').textContent = 'OFF';
      document.getElementById('bar-net').style.width = '0%';
      log('[BUS] Conexión perdida — reconectando en 6s...', 't-riesgo');
      wsReconect = setTimeout(conectarBus, 6000);
    };
  } catch(err){
    log(`[BUS] Error de conexión: ${err.message}`, 't-error');
    wsReconect = setTimeout(conectarBus, 8000);
  }
}

function enviarTelemetria(){
  if(!ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({
    origen:  'JARVIS_CORTEX_SAMSUNG',
    comando: '',
    lat:     STATE.lat,
    lon:     STATE.lon,
    bio: { hr: STATE.hr, hrv: STATE.hrv, temp: STATE.temp, bat: STATE.bat, hz: STATE.hz }
  }));
}

// Telemetría automática cada 30s
setInterval(enviarTelemetria, 30000);

// ═══════════════════════════════════════════════════════════════
// TERMINAL
// ═══════════════════════════════════════════════════════════════
const term = document.getElementById('terminal');
function log(msg, cls='t-sys'){
  const d = document.createElement('div');
  d.className = cls;
  const ts = new Date().toLocaleTimeString('es-MX',{hour12:false});
  d.textContent = `[${ts}] ${msg}`;
  term.appendChild(d);
  term.scrollTop = term.scrollHeight;
  if(term.children.length > 300) term.removeChild(term.firstChild);
}

// ═══════════════════════════════════════════════════════════════
// ENVIAR COMANDO
// ═══════════════════════════════════════════════════════════════
async function enviarCmd(cmdText){
  const cmd = (cmdText || document.getElementById('cmd').value).trim();
  if(!cmd) return;
  document.getElementById('cmd').value = '';
  log(`>> [LOK] ${cmd}`);

  // Detectar comandos especiales locales
  if(cmd.startsWith('set sofi ')){
    const url = cmd.replace('set sofi ','');
    localStorage.setItem('sofi_url', url);
    log(`[CONFIG] SOFÍ URL guardada: ${url}`, 't-bio');
    return;
  }
  if(cmd.startsWith('set afu ')){
    const url = cmd.replace('set afu ','');
    localStorage.setItem('afu_url', url);
    log(`[CONFIG] AFU URL guardada: ${url}`, 't-bio');
    return;
  }
  if(cmd === 'estado'){
    log(`[LOCAL] Hz:${STATE.hz} | HR:${STATE.hr} | BAT:${STATE.bat}% | GPS:${STATE.lat.toFixed(3)},${STATE.lon.toFixed(3)} | Bus:${STATE.wsOk?'LIVE':'OFF'}`, 't-bio');
    return;
  }

  // Intentar API REST del AFU primero si está configurado
  if(AFU_URL && cmd.includes('senal')){
    try{
      const r = await fetch(`${AFU_URL}/api/bot/senal`);
      const d = await r.json();
      log(`[AFU] Señal ZFPI: ${d.tipo} | coh:${d.coherencia} | $${d.precio}`, 't-blanca');
    } catch(e){
      log(`[AFU] Sin conexión REST: ${e.message}`, 't-riesgo');
    }
    return;
  }
  if(AFU_URL && cmd.includes('tesor')){
    try{
      const r = await fetch(`${AFU_URL}/api/tesoreria`);
      const d = await r.json();
      log(`[AFU] Tesorería: ZYXSOF:${d.balance_zyxsof} USD:${d.balance_usd} | Ops:${d.operaciones}`, 't-blanca');
    } catch(e){
      log(`[AFU] Sin conexión REST: ${e.message}`, 't-riesgo');
    }
    return;
  }
  if(AFU_URL && cmd.includes('banco')){
    try{
      const r = await fetch(`${AFU_URL}/api/banco/estado`);
      const d = await r.json();
      log(`[AFU] Banco KUZ: Saldo $${d.saldo_acumulado} | Meta ${d.porcentaje_meta} | Fase:${d.fase_migracion}`, 't-blanca');
    } catch(e){
      log(`[AFU] ${e.message}`, 't-riesgo');
    }
    return;
  }

  // Enviar al bus K'uhul (SOFÍ V9)
  if(ws && ws.readyState === WebSocket.OPEN){
    ws.send(JSON.stringify({
      origen:  'JARVIS_CORTEX_LOK',
      comando:  cmd,
      lat:      STATE.lat,
      lon:      STATE.lon,
      bio: { hr: STATE.hr, hrv: STATE.hrv, hz: STATE.hz }
    }));
  } else {
    log('[BUS] Sin conexión al Canal K\\'uhul. Intentando reconectar...', 't-riesgo');
    conectarBus();
  }
}

// ═══════════════════════════════════════════════════════════════
// INPUT EVENTOS
// ═══════════════════════════════════════════════════════════════
document.getElementById('cmd').addEventListener('keydown', e => {
  if(e.key === 'Enter') enviarCmd();
});
document.getElementById('btn-send').addEventListener('click', () => enviarCmd());

// ═══════════════════════════════════════════════════════════════
// ARRANQUE
// ═══════════════════════════════════════════════════════════════
(function init(){
  iniciarGPS();
  iniciarBateria();
  simularBiometricos();
  conectarBus();

  // Pulso de frecuencia en HUD
  setInterval(() => {
    const hz = (12.3 + Math.sin(Date.now()/10000)*0.05).toFixed(3);
    document.getElementById('hud-hz').textContent = `◉ ${hz} Hz`;
  }, 500);

  // Log de bienvenida
  setTimeout(() => log('[JARVIS] Sistema SOFÍ en posesión del Samsung A03', 't-sys'), 800);
  setTimeout(() => log('[OSIRIS] Escudo K\\'uhul activo — Triangulando posición...', 't-sys'), 1400);
  setTimeout(() => log('[INSTRUCCIÓN] Usa "set sofi wss://TU-URL/ws/canal_kuhul" para conectar', 't-bio'), 2200);
  setTimeout(() => log('[INSTRUCCIÓN] Usa "set afu https://TU-AFU-URL" para el Agente Financiero', 't-bio'), 2800);
})();
</script>
</body>
</html>
"""
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
