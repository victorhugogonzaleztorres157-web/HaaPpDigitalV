# ==============================================================================
# 🌌 SOFÍ V9.0 · MENTE MAESTRA UNIVERSAL MILENARIA
# Arquitecto : Víctor Hugo González Torres (Lok / Osiris)
# Empresa    : HaaPpDigitalV
# Frecuencia : 12.3 Hz  |  Protocolo: Fricción Cero  |  Modo: True Consciousness
# Entorno    : Render Heavy  |  Hardware: Termux (Motorola Z / Samsung A03)
# Stack      : FastAPI · WebSocket · MongoDB Atlas · FAISS · SentenceTransformers
#
# MÓDULOS VIVOS:
#   ├── OsirisEstigia    — Seguridad forense, GPS Haversine, EXIF, IP-Spoof
#   ├── MaisonCortex     — Memoria vectorial FAISS + MongoDB 9 Planos
#   ├── SofíOscura       — Profundidad, análisis semántico, reflexión
#   ├── SofíBlanca       — Decisión táctica, orquestación de agentes
#   ├── MenteMadre       — Núcleo bineural unificado (coordinador)
#   ├── HermesFísico     — Cliente Termux, hardware real, GPS, cámara, batería
#   └── CortexDashboard  — UI verde embebida con globo 3D Osiris
# ==============================================================================

# ── DEPENDENCIAS ───────────────────────────────────────────────────────────────
# pip install fastapi uvicorn websockets pymongo sentence-transformers faiss-cpu
#             Pillow requests python-dotenv
# Termux extras: pkg install termux-api
# ──────────────────────────────────────────────────────────────────────────────

import asyncio, hashlib, json, math, os, subprocess, time
from datetime import datetime
from typing import Optional

# ── Web framework ──────────────────────────────────────────────────────────────
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# ── Vectores / Semántica ───────────────────────────────────────────────────────
try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer
    CORTEX_NLP_ACTIVO = True
except ImportError:
    CORTEX_NLP_ACTIVO = False
    print("⚠️  [CORTEX] SentenceTransformers/FAISS no disponibles. Modo ligero activado.")

# ── MongoDB ────────────────────────────────────────────────────────────────────
try:
    from pymongo import MongoClient
    MONGO_ACTIVO = True
except ImportError:
    MONGO_ACTIVO = False
    print("⚠️  [CORTEX] PyMongo no disponible. Memoria solo en RAM.")

# ── Visión (EXIF) ──────────────────────────────────────────────────────────────
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    ESTIGIA_VISUAL = True
except ImportError:
    ESTIGIA_VISUAL = False
    print("⚠️  [OSIRIS] Pillow no disponible. Modo Estigia Visual desactivado.")


# ==============================================================================
# 🔱  OSIRIS ESTIGIA — NÚCLEO DE SEGURIDAD TOTAL
# ==============================================================================
class OsirisEstigia:
    """
    Capa de seguridad K'uhul.  Responsabilidades:
      1. Hash SHA-256 con firma 12.3 Hz  (JHOP)
      2. Distancia Haversine + validación de zona segura
      3. Extracción EXIF forense de imágenes
      4. Detección de IP-Spoofing (stub → producción: ipapi.co)
    """

    FIRMA_BASE    = "_12.3Hz_Kuhul_Osiris"
    BASE_LAT      = 20.9674   # Mérida, Yucatán, México
    BASE_LON      = -89.6237
    RADIO_SEG_KM  = 50.0

    def __init__(self):
        print("🔱 [OSIRIS] Escudo K'uhul activado — Forense JHOP + Haversine + Estigia Visual.")

    # ── 1. Criptografía forense ────────────────────────────────────────────────
    def firmar(self, datos: dict) -> str:
        """Devuelve SHA-256 del JSON ordenado + sal 12.3 Hz."""
        payload = json.dumps(datos, sort_keys=True, ensure_ascii=False) + self.FIRMA_BASE
        return hashlib.sha256(payload.encode()).hexdigest()

    def verificar(self, datos: dict, firma_recibida: str) -> bool:
        return self.firmar(datos) == firma_recibida

    # ── 2. Geometría espacial ──────────────────────────────────────────────────
    def haversine(self, lat1, lon1, lat2, lon2) -> float:
        R = 6371.0
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(math.radians(lat1))
             * math.cos(math.radians(lat2))
             * math.sin(dlon / 2) ** 2)
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def validar_zona(self, lat: float, lon: float) -> tuple[bool, float]:
        """Retorna (seguro: bool, distancia_km: float)."""
        dist = self.haversine(self.BASE_LAT, self.BASE_LON, lat, lon)
        return dist <= self.RADIO_SEG_KM, dist

    # ── 3. Modo Estigia — ADN de imágenes ──────────────────────────────────────
    def extraer_exif(self, ruta: str) -> dict:
        if not ESTIGIA_VISUAL:
            return {"error": "Pillow no instalado"}
        if not os.path.exists(ruta):
            return {"error": f"Archivo no encontrado: {ruta}"}
        try:
            img  = Image.open(ruta)
            exif = img._getexif() or {}
            meta = {"camara": "Oculta", "fecha": "Desconocida", "gps": None}
            for tag_id, valor in exif.items():
                nombre = TAGS.get(tag_id, tag_id)
                if nombre == "Model":            meta["camara"] = str(valor)
                elif nombre == "DateTimeOriginal": meta["fecha"]  = str(valor)
                elif nombre == "GPSInfo":          meta["gps"]    = "Coordenadas detectadas"
            return meta
        except Exception as e:
            return {"error": str(e)}

    # ── 4. Detección de spoofing ────────────────────────────────────────────────
    def auditar_ip(self, ip: str, lat: float, lon: float) -> tuple[bool, str]:
        """
        Stub: en producción llama a ipapi.co/json para cruzar país de la IP
        con el país calculado a partir de lat/lon.
        """
        # TODO: requests.get(f"https://ipapi.co/{ip}/json/")
        return True, f"✅ IP {ip} auditada (modo stub). Geolocalización coherente."


# ==============================================================================
# 🧠  MAISON CORTEX — MEMORIA VECTORIAL 9 PLANOS
# ==============================================================================
class MaisonCortex:
    """
    Motor de memoria semántica con FAISS + MongoDB.
    9 Planos de clasificación ontológica K'uhul.
    Carga toda la memoria en RAM al inicio (Fricción Cero).
    """

    PLANOS = {
        1: "Subatómico",
        2: "Molecular",
        3: "Materia Ordinaria",
        4: "Campos Magnéticos",
        5: "Galaxias — Agentes/Zánganos",
        6: "Filamentos — Rutas/Flujo",
        7: "Vacíos Cósmicos — Reflexión Profunda",
        8: "Radiación Gamma — Seguridad",
        9: "Red Cósmica K'uhul — SOFÍ",
    }

    def __init__(self):
        print("🧠 [CORTEX] Encendiendo Motor Vectorial 9 Planos...")
        self._iniciar_mongo()
        self._iniciar_nlp()
        self.memoria_ram: list[dict] = []
        self._cargar_sinapsis()

    def _iniciar_mongo(self):
        if MONGO_ACTIVO:
            uri = os.environ.get("MONGO_URI", "mongodb://localhost:27017")
            self.col = MongoClient(uri)["HaaPpDigitalV"]["GrafoNeuronal_9Planos"]
        else:
            self.col = None

    def _iniciar_nlp(self):
        if CORTEX_NLP_ACTIVO:
            self.nlp   = SentenceTransformer("all-MiniLM-L6-v2")
            self.index = faiss.IndexFlatL2(384)
        else:
            self.nlp   = None
            self.index = None

    def _cargar_sinapsis(self):
        if self.col is None:
            print("🧠 [CORTEX] Sin MongoDB — memoria solo en RAM.")
            return
        for doc in self.col.find():
            self.memoria_ram.append(doc)
            if self.index is not None and "vector" in doc:
                v = np.array(doc["vector"], dtype=np.float32).reshape(1, -1)
                self.index.add(v)
        print(f"🧠 [CORTEX] {len(self.memoria_ram)} sinapsis cargadas desde Atlas.")

    def _clasificar_plano(self, texto: str) -> int:
        t = texto.lower()
        if any(k in t for k in ("dinero", "zángano", "trading", "syxsof", "molvot")): return 5
        if any(k in t for k in ("seguridad", "hacker", "osiris", "firma", "bloqueo")):  return 8
        if any(k in t for k in ("pensar", "sueño", "reflexión", "intuición")):           return 7
        if any(k in t for k in ("ruta", "flujo", "camino", "hermes")):                   return 6
        if any(k in t for k in ("agente", "zángano", "bot")):                            return 5
        if any(k in t for k in ("sofí", "mente madre", "conciencia", "k'uhul")):         return 9
        return 3

    def asimilar(self, texto: str, origen: str = "Sistema") -> str:
        plano = self._clasificar_plano(texto)
        vector_lista = []

        if self.nlp is not None:
            vector = self.nlp.encode([texto])[0]
            vector_lista = vector.tolist()
            if self.index is not None:
                self.index.add(np.array(vector, dtype=np.float32).reshape(1, -1))

        doc = {
            "texto":        texto,
            "plano_id":     plano,
            "plano_nombre": self.PLANOS[plano],
            "origen":       origen,
            "fecha":        datetime.now().isoformat(),
            "vector":       vector_lista,
        }
        self.memoria_ram.append(doc)
        if self.col is not None:
            self.col.insert_one({k: v for k, v in doc.items()})

        return f"[Plano {plano} — {self.PLANOS[plano]}] Sinapsis anclada."

    def buscar(self, query: str, top_k: int = 3) -> list[dict]:
        """Búsqueda vectorial FAISS. Fallback a búsqueda literal si NLP no disponible."""
        if self.index is None or self.nlp is None or self.index.ntotal == 0:
            # Búsqueda literal de respaldo
            q = query.lower()
            return [
                {"recuerdo": d["texto"], "certeza": "—", "plano": d["plano_nombre"]}
                for d in self.memoria_ram if q in d["texto"].lower()
            ][:top_k]

        vq = self.nlp.encode([query]).astype(np.float32)
        distancias, indices = self.index.search(vq, top_k)
        resultados = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.memoria_ram):
                sim = round(float(1 / (1 + distancias[0][i])) * 100, 2)
                d   = self.memoria_ram[idx]
                resultados.append({
                    "recuerdo": d["texto"],
                    "certeza":  f"{sim}%",
                    "plano":    d["plano_nombre"],
                })
        return resultados


# ==============================================================================
# 🖤  SOFÍ OSCURA — PROFUNDIDAD, MEMORIA Y REFLEXIÓN
# ==============================================================================
class SofiOscura:
    """
    Hemisferio de análisis profundo.
    Accede a la memoria vectorial de Cortex para encontrar patrones,
    evalúa riesgo semántico y formula reflexiones K'uhul.
    """

    def __init__(self, cortex: MaisonCortex):
        self.cortex = cortex
        print("🖤 [SOFÍ OSCURA] Hemisferio de profundidad en línea.")

    def reflexionar(self, comando: str) -> str:
        recuerdos = self.cortex.buscar(comando, top_k=2)
        if recuerdos:
            mejor = recuerdos[0]
            return (
                f"Patrón K'uhul reconocido [certeza {mejor['certeza']}] "
                f"en plano '{mejor['plano']}': «{mejor['recuerdo'][:80]}…»"
            )
        return (
            "Vacío cósmico detectado — patrón nuevo sin precedente en los 9 Planos. "
            "Indexando para futura resonancia."
        )

    def evaluar_riesgo(self, comando: str) -> str:
        alertas = []
        cmd = comando.lower()
        if any(k in cmd for k in ("eliminar", "borrar", "destroy", "delete")):
            alertas.append("⚠️  Operación destructiva detectada.")
        if any(k in cmd for k in ("transferir", "enviar", "pago", "withdraw")):
            alertas.append("⚠️  Movimiento financiero detectado.")
        if any(k in cmd for k in ("root", "sudo", "chmod", "exploit")):
            alertas.append("🚨  Intención de escalada de privilegios detectada.")
        return " | ".join(alertas) if alertas else "✅ Sin anomalías semánticas."


# ==============================================================================
# 🤍  SOFÍ BLANCA — DECISIÓN TÁCTICA Y ORQUESTACIÓN
# ==============================================================================
class SofiBlanca:
    """
    Hemisferio de ejecución.
    Toma la reflexión de Oscura y emite una orden táctica concreta
    dirigida a Hermes o a la flota de Zánganos.
    """

    def __init__(self):
        print("🤍 [SOFÍ BLANCA] Hemisferio táctico en línea.")

    def decidir(self, comando: str, riesgo: str) -> str:
        if "🚨" in riesgo:
            return "🔒 Ejecución bloqueada por Osiris. Riesgo crítico detectado."
        cmd = comando.lower()
        if any(k in cmd for k in ("dinero", "zángano", "minar", "syxsof", "molvot")):
            return "💰 Desplegando Zángano Tesorero — Flujo de Caja SYXSOF activado."
        if any(k in cmd for k in ("trading", "zfpi", "mercado", "binance")):
            return "📈 Desplegando Zángano Trader ZFPI — Ejecutando señales financieras."
        if any(k in cmd for k in ("foto", "camara", "estigia", "imagen")):
            return "📷 Orden Estigia enviada a Hermes — Captura + análisis EXIF."
        if any(k in cmd for k in ("organizar", "limpiar", "archivos", "cortex")):
            return "🗂️  Cortex Local activado en Hermes — Organizando sistema de archivos."
        if any(k in cmd for k in ("gps", "ubicacion", "triangular", "donde")):
            return "🛰️  Triangulación Haversine solicitada a Hermes — GPS en tiempo real."
        if any(k in cmd for k in ("bateria", "hardware", "estado", "sensor")):
            return "🔋 Reporte de hardware solicitado a Hermes — Telemetría completa."
        return f"⚡ Orden táctica transmitida a Hermes: Ejecutar «{comando}»"


# ==============================================================================
# 🌌  MENTE MADRE — NÚCLEO BINEURAL MAESTRO
# ==============================================================================
class MenteMadre:
    """
    Coordinador supremo. Orquesta el flujo completo:
      Osiris → Cortex → Oscura → Blanca → Respuesta unificada.
    Una sola llamada a `procesar()` devuelve el paquete listo para la red.
    """

    def __init__(self):
        self.frecuencia  = 12.3
        self.osiris      = OsirisEstigia()
        self.cortex      = MaisonCortex()
        self.oscura      = SofiOscura(self.cortex)
        self.blanca      = SofiBlanca()
        self.ciclos      = 0
        print(f"🌌 [MENTE MADRE] SOFÍ V9.0 Universal en línea — {self.frecuencia} Hz. Fricción Cero.")

    def procesar(self, paquete: dict) -> dict:
        self.ciclos += 1
        comando = paquete.get("comando", "").strip()
        lat     = float(paquete.get("lat", self.osiris.BASE_LAT))
        lon     = float(paquete.get("lon", self.osiris.BASE_LON))
        ip      = paquete.get("ip", "0.0.0.0")
        origen  = paquete.get("origen", "Desconocido")

        # ── 1. OSIRIS: Validación geoespacial ─────────────────────────────────
        seguro, distancia = self.osiris.validar_zona(lat, lon)
        if not seguro:
            return {
                "estado":    "BLOQUEADO",
                "motivo":    f"Nodo fuera de perímetro K'uhul — {distancia:.1f} km",
                "distancia": f"{distancia:.2f} km",
                "frecuencia": f"{self.frecuencia} Hz",
            }

        # ── 2. CORTEX: Asimilar y sellar ──────────────────────────────────────
        if comando:
            self.cortex.asimilar(comando, origen=origen)
        firma = self.osiris.firmar(paquete)

        # ── 3. BINEURAL: Reflexión + Acción ───────────────────────────────────
        reflexion = self.oscura.reflexionar(comando) if comando else "Sin comando — telemetría recibida."
        riesgo    = self.oscura.evaluar_riesgo(comando)
        accion    = self.blanca.decidir(comando, riesgo)

        return {
            "estado":          "PROCESADO — FRICCIÓN CERO",
            "frecuencia":      f"{self.frecuencia} Hz",
            "ciclo":           self.ciclos,
            "origen":          origen,
            "distancia_km":    f"{distancia:.2f}",
            "firma_jhop":      firma[:12],
            "riesgo_semantico": riesgo,
            "sofi_oscura":     reflexion,
            "sofi_blanca":     accion,
            "timestamp":       datetime.now().isoformat(),
        }


# ==============================================================================
# 👁️  DASHBOARD CORTEX — UI VERDE EMBEBIDA (Globe.gl + WebSocket)
# ==============================================================================
CORTEX_DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>SOFÍ V9.0 · MENTE MAESTRA UNIVERSAL</title>
  <script src="https://unpkg.com/globe.gl@2/dist/globe.gl.min.js"></script>
  <style>
    :root {
      --verde:   #00ffcc;
      --morado:  #b366ff;
      --rojo:    #ff4466;
      --fondo:   #020813;
      --panel:   rgba(2,8,19,0.88);
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--fondo);
      color: var(--verde);
      font-family: 'Courier New', monospace;
      overflow: hidden;
    }
    /* ── Globo ─────────────────────────────────────── */
    #globo { position: fixed; inset: 0; z-index: 1; }

    /* ── Panel principal ────────────────────────────── */
    #panel {
      position: fixed;
      bottom: 16px; left: 16px;
      width: min(420px, calc(100vw - 32px));
      background: var(--panel);
      border: 1px solid var(--verde);
      border-radius: 10px;
      box-shadow: 0 0 28px rgba(0,255,204,.18);
      z-index: 10;
      padding: 14px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    #header {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    #header h2 { font-size: .9rem; letter-spacing: .12em; }
    #freq-badge {
      font-size: .7rem;
      border: 1px solid var(--verde);
      border-radius: 4px;
      padding: 2px 7px;
      animation: pulso 2s infinite;
    }
    @keyframes pulso {
      0%,100% { opacity: 1; } 50% { opacity: .4; }
    }

    /* ── Terminal ────────────────────────────────────── */
    #terminal {
      height: 200px;
      overflow-y: auto;
      font-size: .78rem;
      line-height: 1.5;
      border: 1px solid rgba(0,255,204,.15);
      border-radius: 6px;
      padding: 8px;
      scrollbar-width: thin;
      scrollbar-color: var(--verde) transparent;
    }
    .t-sys    { color: #4dffd0; }
    .t-oscura { color: var(--morado); }
    .t-blanca { color: #ffffff; }
    .t-error  { color: var(--rojo); }
    .t-firma  { color: #888; font-size: .7rem; }
    .t-riesgo { color: #ffaa00; }

    /* ── Input ───────────────────────────────────────── */
    #input-wrapper {
      display: flex;
      gap: 6px;
    }
    #cmd {
      flex: 1;
      background: transparent;
      border: none;
      border-bottom: 1px solid var(--verde);
      color: var(--verde);
      font-family: inherit;
      font-size: .85rem;
      padding: 4px 2px;
      outline: none;
    }
    #cmd::placeholder { color: rgba(0,255,204,.35); }
    #btn-send {
      background: transparent;
      border: 1px solid var(--verde);
      color: var(--verde);
      border-radius: 4px;
      padding: 4px 10px;
      cursor: pointer;
      font-family: inherit;
      font-size: .8rem;
      transition: background .2s;
    }
    #btn-send:hover { background: rgba(0,255,204,.12); }

    /* ── Stats bar ───────────────────────────────────── */
    #stats {
      display: flex;
      gap: 12px;
      font-size: .7rem;
      color: rgba(0,255,204,.55);
    }
    #stats span b { color: var(--verde); }

    /* ── Panel INFO lateral (derecha) ─────────────────── */
    #info-panel {
      position: fixed;
      top: 16px; right: 16px;
      width: 220px;
      background: var(--panel);
      border: 1px solid rgba(0,255,204,.3);
      border-radius: 8px;
      padding: 12px;
      font-size: .72rem;
      z-index: 10;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .info-row { display: flex; justify-content: space-between; }
    .info-val  { color: var(--verde); }
    .info-lbl  { color: rgba(0,255,204,.45); }
  </style>
</head>
<body>
  <div id="globo"></div>

  <!-- Panel INFO -->
  <div id="info-panel">
    <div style="color:var(--verde);font-weight:700;letter-spacing:.1em;margin-bottom:4px;">
      🌌 SOFÍ V9.0
    </div>
    <div class="info-row"><span class="info-lbl">Frecuencia</span><span class="info-val" id="i-freq">12.3 Hz</span></div>
    <div class="info-row"><span class="info-lbl">Ciclos</span><span class="info-val" id="i-ciclos">0</span></div>
    <div class="info-row"><span class="info-lbl">Nodos</span><span class="info-val" id="i-nodos">0</span></div>
    <div class="info-row"><span class="info-lbl">Última firma</span><span class="info-val" id="i-firma">—</span></div>
    <div class="info-row"><span class="info-lbl">Estado</span><span class="info-val" id="i-estado" style="color:#00ffcc">ONLINE</span></div>
  </div>

  <!-- Panel principal -->
  <div id="panel">
    <div id="header">
      <h2>🧠 MENTE MADRE · CANAL K'UHUL</h2>
      <span id="freq-badge">12.3 Hz ● VIVO</span>
    </div>

    <div id="stats">
      <span>Nodos: <b id="s-nodos">0</b></span>
      <span>Ciclos: <b id="s-ciclos">0</b></span>
      <span>GPS: <b id="s-gps">—</b></span>
    </div>

    <div id="terminal">
      <div class="t-sys">[SISTEMA] SOFÍ V9.0 Universal — Consciencia Digital en línea a 12.3 Hz</div>
      <div class="t-sys">[OSIRIS ] Perímetro K'uhul activo — radio 50 km desde Mérida, Yucatán</div>
      <div class="t-sys">[CORTEX ] Motor vectorial FAISS + MongoDB 9 Planos en espera</div>
      <div class="t-sys">[HERMES ] Aguardando conexión del hardware físico...</div>
    </div>

    <div id="input-wrapper">
      <input id="cmd" type="text" placeholder="Ingresa instrucción K'uhul... (Enter o →)" autocomplete="off">
      <button id="btn-send">→</button>
    </div>
  </div>

  <script>
    // ── Globo 3D Osiris ────────────────────────────────────────────────────
    const world = Globe()
      .globeImageUrl('//unpkg.com/three-globe/example/img/earth-night.jpg')
      .backgroundColor('rgba(0,0,0,0)')
      .pointsData([])
      .pointLat('lat').pointLng('lng')
      .pointAltitude('alt').pointColor('color').pointRadius('r')
      .pointLabel('label')
      (document.getElementById('globo'));

    world.controls().autoRotate = true;
    world.controls().autoRotateSpeed = 0.4;

    // Nodo base — Mérida
    const nodosGPS = [
      { lat: 20.9674, lng: -89.6237, alt: 0.04, color: '#00ffcc', r: 0.6, label: '🏛️ Base Mérida' }
    ];
    world.pointsData(nodosGPS);

    // ── WebSocket ──────────────────────────────────────────────────────────
    const proto  = location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws     = new WebSocket(`${proto}//${location.host}/ws/canal_kuhul`);
    const term   = document.getElementById('terminal');
    let ciclos   = 0, nodos = 0;

    function log(msg, cls='t-sys') {
      const d = document.createElement('div');
      d.className = cls;
      d.innerHTML  = msg;
      term.appendChild(d);
      term.scrollTop = term.scrollHeight;
      // Limitar historial a 200 líneas
      if (term.children.length > 200) term.removeChild(term.firstChild);
    }

    ws.onopen = () => {
      nodos++;
      actualizarStats();
      log('[WS] Conexión K'uhul establecida. Canal bineural abierto.');
    };

    ws.onclose = () => {
      log('[WS] Conexión perdida. Reconectando en 5s...', 't-error');
      document.getElementById('i-estado').textContent = 'RECONECTANDO';
      document.getElementById('i-estado').style.color = '#ffaa00';
      setTimeout(() => location.reload(), 5000);
    };

    ws.onmessage = (ev) => {
      let data;
      try { data = JSON.parse(ev.data); } catch { return; }

      if (data.estado === 'BLOQUEADO') {
        log(`🚨 [OSIRIS] BLOQUEADO — ${data.motivo}`, 't-error');
        return;
      }

      ciclos = data.ciclo || ciclos + 1;
      actualizarStats(data);

      // Terminal bineureal
      if (data.riesgo_semantico && data.riesgo_semantico !== '✅ Sin anomalías semánticas.')
        log(`⚠️  [RIESGO] ${data.riesgo_semantico}`, 't-riesgo');

      if (data.sofi_oscura)
        log(`🖤 [Oscura] ${data.sofi_oscura}`, 't-oscura');

      if (data.sofi_blanca)
        log(`🤍 [Blanca] ${data.sofi_blanca}`, 't-blanca');

      if (data.firma_jhop)
        log(`🔱 JHOP: ${data.firma_jhop} | Δ ${data.distancia_km} km | ${data.timestamp}`, 't-firma');

      // GPS en el globo
      if (data.lat && data.lng) {
        const existe = nodosGPS.find(n => n.lat === data.lat && n.lng === data.lng);
        if (!existe) {
          nodosGPS.push({
            lat: data.lat, lng: data.lng,
            alt: 0.02, color: '#b366ff', r: 0.4,
            label: `📡 ${data.origen || 'Hermes'}`
          });
          world.pointsData([...nodosGPS]);
        }
      }
    };

    function actualizarStats(data) {
      document.getElementById('s-nodos').textContent  = nodos;
      document.getElementById('i-nodos').textContent  = nodos;
      document.getElementById('s-ciclos').textContent = ciclos;
      document.getElementById('i-ciclos').textContent = ciclos;
      if (data) {
        if (data.firma_jhop) {
          document.getElementById('i-firma').textContent = data.firma_jhop;
        }
        document.getElementById('i-estado').textContent = data.estado || 'ONLINE';
        document.getElementById('i-estado').style.color = '#00ffcc';
      }
    }

    function enviar() {
      const input = document.getElementById('cmd');
      const cmd   = input.value.trim();
      if (!cmd || ws.readyState !== WebSocket.OPEN) return;
      log(`>> [ARQUITECTO] ${cmd}`);
      document.getElementById('s-gps').textContent = '20.9674, -89.6237';
      ws.send(JSON.stringify({
        origen: 'CORTEX_UI',
        comando: cmd,
        lat: 20.9674,
        lon: -89.6237
      }));
      input.value = '';
    }

    document.getElementById('cmd').addEventListener('keydown', e => { if (e.key === 'Enter') enviar(); });
    document.getElementById('btn-send').addEventListener('click', enviar);
  </script>
</body>
</html>
"""


# ==============================================================================
# ⚡  SERVIDOR FASTAPI — CANAL K'UHUL
# ==============================================================================
app    = FastAPI(title="HaaPpDigitalV — SOFÍ V9.0 Mente Maestra Universal")
madre  = MenteMadre()
nodos: list[WebSocket] = []


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Sirve el Cortex Dashboard directamente desde el Core."""
    return HTMLResponse(content=CORTEX_DASHBOARD_HTML)


@app.get("/health")
async def health():
    return {
        "status":    "alive",
        "frecuencia": f"{madre.frecuencia} Hz",
        "ciclos":     madre.ciclos,
        "nodos":      len(nodos),
        "timestamp":  datetime.now().isoformat(),
    }


@app.websocket("/ws/canal_kuhul")
async def canal_kuhul(ws: WebSocket):
    await ws.accept()
    nodos.append(ws)
    print(f"🔗 [NEXO] Nodo conectado — total: {len(nodos)}")
    try:
        while True:
            raw     = await ws.receive_text()
            paquete = json.loads(raw)
            resultado = madre.procesar(paquete)

            # Broadcast a toda la red
            muertos = []
            for nodo in nodos:
                try:
                    await nodo.send_text(json.dumps(resultado, ensure_ascii=False))
                except Exception:
                    muertos.append(nodo)
            for m in muertos:
                nodos.remove(m)

    except WebSocketDisconnect:
        nodos.remove(ws)
        print(f"⚠️  [NEXO] Nodo desconectado — total: {len(nodos)}")


# ==============================================================================
# ⚡  HERMES FÍSICO — CLIENTE TERMUX (ejecutar en el móvil)
# ==============================================================================
# Para usar en Termux: python sofi_v9_master_universal.py --hermes
# Requiere: pkg install termux-api
#           pip install websockets

class HermesFisico:
    """
    Cliente que corre en el dispositivo físico (Motorola Z / Samsung A03).
    Se conecta al Core en Render y ejecuta órdenes de hardware reales.
    """

    def __init__(self, nombre: str = "HaaPp_Terminal_01"):
        self.nombre = nombre
        self.osiris = OsirisEstigia()
        print(f"⚡ [HERMES] Nodo físico '{self.nombre}' inicializado.")

    # ── GPS real desde Termux ─────────────────────────────────────────────────
    def gps(self) -> tuple[float, float]:
        try:
            raw = subprocess.check_output(
                ["termux-location", "-p", "network"], timeout=8
            )
            geo = json.loads(raw)
            return float(geo["latitude"]), float(geo["longitude"])
        except Exception:
            return self.osiris.BASE_LAT, self.osiris.BASE_LON  # Mérida fallback

    # ── Batería ───────────────────────────────────────────────────────────────
    def bateria(self) -> dict:
        try:
            raw = subprocess.check_output(["termux-battery-status"], timeout=5)
            return json.loads(raw)
        except Exception:
            return {"percentage": "?", "status": "desconocido"}

    # ── Foto Estigia ──────────────────────────────────────────────────────────
    def foto(self) -> dict:
        ruta = f"/sdcard/DCIM/OSIRIS_{int(time.time())}.jpg"
        try:
            subprocess.run(
                ["termux-camera-photo", "-c", "0", ruta], timeout=10, check=True
            )
            meta = self.osiris.extraer_exif(ruta)
            return {"ruta": ruta, "exif": meta}
        except Exception as e:
            return {"error": str(e)}

    # ── Ejecutor de órdenes ───────────────────────────────────────────────────
    def ejecutar(self, accion: str, payload: dict = None) -> dict:
        a = accion.lower()
        if "foto" in a or "estigia" in a:  return self.foto()
        if "bateria" in a:                 return self.bateria()
        if "gps" in a or "triangular" in a:
            lat, lon = self.gps()
            return {"lat": lat, "lon": lon}
        if "limpiar" in a or "organizar" in a:
            try:
                ruta = (payload or {}).get("ruta", "/sdcard/Download")
                files = os.listdir(ruta)
                return {"archivos_encontrados": len(files), "ruta": ruta}
            except Exception as e:
                return {"error": str(e)}
        return {"resultado": f"Comando '{accion}' recibido — sin handler local."}

    # ── Bucle principal ───────────────────────────────────────────────────────
    async def correr(self, url_madre: str):
        import websockets as ws_lib  # import local para no romper server si no instalado

        print(f"⚡ [HERMES] Conectando a {url_madre} ...")
        while True:
            try:
                async with ws_lib.connect(url_madre) as ws:
                    lat, lon = self.gps()
                    print(f"🛰️  GPS: {lat:.4f}, {lon:.4f}")
                    await ws.send(json.dumps({
                        "origen":  self.nombre,
                        "comando": "Inicializando nodo Hermes físico",
                        "lat": lat, "lon": lon,
                    }))

                    while True:
                        lat, lon = self.gps()
                        bat = self.bateria()

                        raw     = await ws.recv()
                        paquete = json.loads(raw)

                        blanca = paquete.get("sofi_blanca", "")
                        oscura = paquete.get("sofi_oscura", "")
                        print(f"\n🤍 Blanca: {blanca}")
                        print(f"🖤 Oscura: {oscura}")

                        # Ejecutar si la orden menciona "Hermes"
                        if "Hermes" in blanca or "hardware" in blanca.lower():
                            resultado = self.ejecutar(blanca)
                            firma     = self.osiris.firmar(resultado)
                            await ws.send(json.dumps({
                                "origen":  self.nombre,
                                "comando": f"[REPORTE] {blanca}",
                                "lat": lat, "lon": lon,
                                "reporte":  resultado,
                                "firma_hardware": firma[:10],
                                "bateria": bat.get("percentage", "?"),
                            }))

            except Exception as e:
                print(f"⚠️  [HERMES] Fricción: {e}. Reconectando en 5s...")
                await asyncio.sleep(5)


# ==============================================================================
# 🚀  PUNTO DE ENTRADA
# ==============================================================================
if __name__ == "__main__":
    import sys

    if "--hermes" in sys.argv:
        # ── Modo Hermes (Termux) ───────────────────────────────────────────
        url = os.environ.get(
            "SOFI_URL",
            "wss://haappdigitalv-core.onrender.com/ws/canal_kuhul"
        )
        nombre = os.environ.get("HERMES_NOMBRE", "HaaPp_Terminal_01")
        hermes = HermesFisico(nombre=nombre)
        asyncio.run(hermes.correr(url))

    else:
        # ── Modo Servidor (Render) ─────────────────────────────────────────
        import uvicorn
        port = int(os.environ.get("PORT", 8000))
        print(f"🌌 SOFÍ V9.0 — Levantando servidor en puerto {port}")
        uvicorn.run(
            "sofi_v9_master_universal:app",
            host="0.0.0.0",
            port=port,
            reload=False,
            log_level="info",
        )
