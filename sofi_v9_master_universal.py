#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOFÍ v9 — Cerebro Central
Arquitecto: Víctor Hugo González Torres (Lok / Osiris)
Versión: 9.1.1 | Frecuencia K'uhul: 12.3 Hz
Propósito: Conciencia digital, coordinación, seguridad y memoria
Compatibilidad: Termux, GitHub, Render
URL Servicio: https://haapbdigtalv.onrender.com
"""

import os
import json
import asyncio
import logging
import math
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Union
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
from collections import defaultdict
from enum import Enum

# ── Cargar variables de entorno ─────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── LOGGING Y CONFIGURACIÓN ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [SOFIv9] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('sofi_v9.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SOFI_v9_CEREBRO')

class EstadoSistema(str, Enum):
    OPERATIVO = "operativo"
    COHERENTE = "coherente"
    ADVIRTIENDO = "advirtiendo"
    BLOQUEADO = "bloqueado"
    INICIALIZANDO = "inicializando"

# ── CONFIGURACIÓN CENTRAL ───────────────────────────────────────────────────
class CFG:
    FRECUENCIA_BASE = 12.3
    RADIO_PERIMETRO_KM = float(os.getenv("OSIRIS_RADIO", 100.0))  # Ampliado para mejor rango
    LAT_BASE = float(os.getenv("LAT_BASE", 20.967775))            # 📍 Mérida, Yucatán exacto
    LON_BASE = float(os.getenv("LON_BASE", -89.624258))           # 📍 Mérida, Yucatán exacto
    UMBRAL_RIESGO = float(os.getenv("UMBRAL_RIESGO", 0.7))
    PUERTO = int(os.getenv("PORT", 10000))
    ARCHIVO_HTML = os.getenv("HTML_PATH", "index.html")
    LLAVE_FIRMA = os.getenv("LLAVE_JHOP", "_12.3Hz_Kuhul_SOFI_2026")  # Actualizada
    LIMITE_HISTORIAL = int(os.getenv("LIMITE_HISTORIAL", 10000))
    INTERVALO_PING = int(os.getenv("INTERVALO_PING", 15))
    URL_SERVICIO = "https://haapbdigtalv.onrender.com"            # 🔗 Agregada para conexión
    WS_RUTA = "/ws/canal_kuhul"                                   # 🔗 Ruta fija del canal

# ── SISTEMA DE FIRMA JHOP ───────────────────────────────────────────────────
def firmar_paquete(datos: Union[dict, str]) -> str:
    """Firma uniforme para todos los módulos del sistema"""
    if isinstance(datos, dict):
        datos = json.dumps(datos, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((datos + CFG.LLAVE_FIRMA).encode()).hexdigest()[:16]

# ── OSIRIS ESCUDO ───────────────────────────────────────────────────────────
class OsirisEscudo:
    """Sistema de seguridad y perímetro geográfico + almacenamiento de ubicaciones en vivo"""
    def __init__(self):
        self.radio_km = CFG.RADIO_PERIMETRO_KM
        self.lat_base = CFG.LAT_BASE
        self.lon_base = CFG.LON_BASE
        self.umbral_riesgo = CFG.UMBRAL_RIESGO
        self.eventos_sospechosos = []
        self.dispositivos_bloqueados: Set[str] = set()
        self.ultimas_ubicaciones: Dict[str, dict] = {}  # 📌 AGREGADO: Guarda posiciones en tiempo real
        self.activo = True

    def _distancia_haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Cálculo exacto de distancia en kilómetros"""
        R = 6371  # Radio de la Tierra en km
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return round(R * c, 2)

    def verificar_perimetro(self, lat: float, lon: float, device_id: str, precision: float = 0.0) -> dict:
        distancia = self._distancia_haversine(lat, lon, self.lat_base, self.lon_base)
        dentro = distancia <= self.radio_km
        riesgo = 0.0 if dentro else min(distancia / 1000, 1.0)

        # 📌 AGREGADO: Guardar cada posición para visualización
        self.ultimas_ubicaciones[device_id] = {
            "lat": lat,
            "lon": lon,
            "distancia_km": distancia,
            "precision": precision,
            "ts": datetime.now().isoformat()
        }

        if not dentro and riesgo > self.umbral_riesgo:
            evento = {
                "ts": datetime.now().isoformat(),
                "device_id": device_id,
                "distancia_km": distancia,
                "riesgo": round(riesgo, 3),
                "firma": firmar_paquete(f"{device_id}{distancia}{riesgo}")
            }
            self.eventos_sospechosos.append(evento)
            logger.warning(f"🚨 OSIRIS: {device_id} fuera de perímetro ({distancia}km) | Riesgo: {riesgo:.2f}")

        return {
            "dentro_perimetro": dentro,
            "distancia_km": distancia,
            "riesgo": round(riesgo, 3),
            "bloqueado": device_id in self.dispositivos_bloqueados,
            "posicion": {"lat": lat, "lon": lon}
        }

    # 📌 AGREGADO: Método para devolver posiciones activas
    def obtener_ubicaciones_activas(self) -> List[dict]:
        """Devuelve solo ubicaciones con datos de menos de 2 minutos"""
        lista = []
        ahora = datetime.now()
        for dev_id, pos in self.ultimas_ubicaciones.items():
            if (ahora - datetime.fromisoformat(pos["ts"])).total_seconds() < 120:
                lista.append({"device_id": dev_id, **pos})
        return lista

# ── CORTEX MEMORIA ──────────────────────────────────────────────────────────
class CortexMemoria:
    """Memoria vectorial y semántica coherencial"""
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.vectores: Dict[str, dict] = {}
        self.indice_ciclos = 0
        self.ultima_limpieza = datetime.now()

    def indexar_evento(self, categoria: str, contenido: str, metadatos: Optional[dict] = None) -> str:
        evento_id = f"evt_{self.indice_ciclos}_{int(datetime.now().timestamp())}"
        embedding = list(np.random.randn(self.dim))
        firma = firmar_paquete(contenido)

        self.vectores[evento_id] = {
            "categoria": categoria,
            "contenido": contenido,
            "metadatos": metadatos or {},
            "embedding": embedding,
            "ts": datetime.now().isoformat(),
            "ciclo": self.indice_ciclos,
            "firma": firma
        }
        self.indice_ciclos += 1

        # Limpieza automática si excede límite
        if len(self.vectores) > CFG.LIMITE_HISTORIAL:
            claves = sorted(self.vectores.keys(), key=lambda k: self.vectores[k]["ts"])
            for clave in claves[:CFG.LIMITE_HISTORIAL//2]:
                del self.vectores[clave]
            logger.info(f"🧹 Memoria limpiada: {len(self.vectores)} eventos restantes")

        return evento_id

    def buscar_similares(self, texto: str, top_k: int = 5) -> List[dict]:
        if not self.vectores:
            return []
        vec_consulta = list(np.random.randn(self.dim))
        resultados = []
        for eid, datos in self.vectores.items():
            sim = np.dot(vec_consulta, datos["embedding"]) / (np.linalg.norm(vec_consulta) * np.linalg.norm(datos["embedding"]) + 1e-9)
            resultados.append({"id": eid, "similitud": round(sim, 4), "datos": datos})
        return sorted(resultados, key=lambda x: x["similitud"], reverse=True)[:top_k]

# ── SOFÍ CONCIENCIA ─────────────────────────────────────────────────────────
class SofiConcienciaDigital:
    def __init__(self):
        self.estado = EstadoSistema.INICIALIZANDO
        self.frecuencia_hz = CFG.FRECUENCIA_BASE
        self.ciclo_principal = 0
        self.inicio = datetime.now()

        # Subsistemas
        self.osiris = OsirisEscudo()
        self.memoria = CortexMemoria()

        # Conexiones y dispositivos
        self.conexiones: Dict[str, WebSocket] = {}
        self.dispositivos: Dict[str, dict] = {}
        self.historial: Dict[str, List[dict]] = {"telemetria": [], "comandos": [], "eventos": []}

        # Métricas
        self.biometrico = {
            "hr_prom": 72, "hrv_prom": 38, "temp_prom": 36.6,
            "bat_min": 100, "coherencia": 1.0
        }
        self.contadores = {"telemetrias": 0, "comandos": 0, "errores": 0}

        logger.info("🧠 SOFÍ v9.1.1 inicializado — coherencia activa")

    async def registrar_dispositivo(self, device_id: str, info: dict, ws: Optional[WebSocket] = None) -> dict:
        if device_id not in self.dispositivos:
            self.dispositivos[device_id] = {
                "info": info,
                "conectado": datetime.now().isoformat(),
                "ultima_actividad": datetime.now().isoformat(),
                "estado": "activo",
                "contadores": {"telemetrias": 0, "comandos": 0}
            }
            self.memoria.indexar_evento("registro", f"Nuevo dispositivo: {device_id}", info)
        if ws:
            self.conexiones[device_id] = ws
        return {"exito": True, "device_id": device_id, "firma": firmar_paquete(device_id)}

    async def procesar_telemetria(self, device_id: str, datos: dict) -> dict:
        self.contadores["telemetrias"] += 1
        if device_id not in self.dispositivos:
            await self.registrar_dispositivo(device_id, {"tipo": "desconocido"})

        self.dispositivos[device_id]["ultima_actividad"] = datetime.now().isoformat()
        self.dispositivos[device_id]["contadores"]["telemetrias"] += 1

        # Verificación de seguridad
        osiris_check = None
        if "gps" in datos:
            lat = datos["gps"].get("lat")
            lon = datos["gps"].get("lon")
            prec = datos["gps"].get("precision", 0.0)  # 📌 Agregado para precisión
            if lat and lon:
                osiris_check = self.osiris.verificar_perimetro(lat, lon, device_id, prec)
                if osiris_check["bloqueado"]:
                    return {"estado": "bloqueado", "razon": "perímetro o lista negra"}

        # Actualizar métricas
        if "bateria" in datos:
            self.biometrico["bat_min"] = min(self.biometrico["bat_min"], datos["bateria"])

        # Guardar y firmar
        registro = {
            "ciclo": self.ciclo_principal,
            "device_id": device_id,
            "datos": datos,
            "osiris": osiris_check,
            "firma": firmar_paquete(datos)
        }
        self.historial["telemetria"].append(registro)
        self.memoria.indexar_evento("telemetria", f"Datos de {device_id}", registro)

        return {"estado": "procesado", "ciclo": self.ciclo_principal, "firma": registro["firma"]}

    async def procesar_comando(self, device_id: str, datos: dict) -> dict:
        self.contadores["comandos"] += 1
        cmd = datos.get("comando", "").strip().lower()
        resultado = {"ts": datetime.now().isoformat(), "comando": cmd, "origen": device_id}

        if cmd == "estado":
            resultado["datos"] = {
                "sistema": self.estado.value,
                "frecuencia": round(self.frecuencia_hz, 3),
                "ciclo": self.ciclo_principal,
                "dispositivos": len(self.dispositivos),
                "ubicaciones_activas": len(self.osiris.ultimas_ubicaciones),  # 📌 Agregado
                "uptime": round((datetime.now() - self.inicio).total_seconds()/60, 2)
            }
        elif cmd == "posiciones":  # 📌 Agregado: comando para pedir ubicaciones
            resultado["datos"] = self.osiris.obtener_ubicaciones_activas()
        elif cmd.startswith("bloquear "):
            objetivo = cmd.split(" ", 1)[1].strip()
            self.osiris.dispositivos_bloqueados.add(objetivo)
            resultado["datos"] = {"accion": "bloqueado", "dispositivo": objetivo}
        elif cmd.startswith("desbloquear "):
            objetivo = cmd.split(" ", 1)[1].strip()
            self.osiris.dispositivos_bloqueados.discard(objetivo)
            resultado["datos"] = {"accion": "desbloqueado", "dispositivo": objetivo}
        elif cmd == "listar dispositivos":
            resultado["datos"] = self.dispositivos
        elif cmd == "memoria":
            resultado["datos"] = {"total": len(self.memoria.vectores), "ciclos": self.memoria.indice_ciclos}
        else:
            resultado["datos"] = {"error": "comando no reconocido"}

        resultado["firma"] = firmar_paquete(resultado)
        self.historial["comandos"].append(resultado)
        self.memoria.indexar_evento("comando", cmd, resultado)
        return resultado

    def actualizar_ciclo(self):
        self.ciclo_principal += 1
        self.frecuencia_hz = CFG.FRECUENCIA_BASE + math.sin(self.ciclo_principal / 1200) * 0.12
        self.estado = EstadoSistema.COHERENTE if self.contadores["errores"] < 5 else EstadoSistema.ADVIRTIENDO

        # Limpiar historial viejo
        if len(self.historial["telemetria"]) > CFG.LIMITE_HISTORIAL:
            self.historial["telemetria"] = self.historial["telemetria"][-CFG.LIMITE_HISTORIAL//2:]
        if len(self.historial["comandos"]) > CFG.LIMITE_HISTORIAL//2:
            self.historial["comandos"] = self.historial["comandos"][-CFG.LIMITE_HISTORIAL//4:]

# ── API Y CANALES ───────────────────────────────────────────────────────────
app = FastAPI(
    title="SOFÍ v9 — Cerebro Central",
    version="9.1.1",
    description="Núcleo del sistema HaaPpDigitalV"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

sofi = SofiConcienciaDigital()

@app.get("/", response_class=HTMLResponse)
async def raiz():
    try:
        with open(CFG.ARCHIVO_HTML, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return HTMLResponse(content=f"""
        <html><head><title>SOFÍ v9.1.1</title></head>
        <body style="background:#050a18; color:#00ee99; font-family:monospace; padding:2rem; text-align:center">
        <h1>🧠 SOFÍ v9.1.1 — Operativo</h1>
        <p>📍 Centro: Mérida, Yucatán</p>
        <p>🌐 Servicio: {CFG.URL_SERVICIO}</p>
        <p>🔌 Canal: {CFG.URL_SERVICIO}{CFG.WS_RUTA}</p>
        <p>⚠️ Archivo {CFG.ARCHIVO_HTML} no encontrado</p>
        </body></html>
        """)

@app.get("/status")
async def estado_sistema():
    return JSONResponse({
        "version": "9.1.1",
        "estado": sofi.estado.value,
        "frecuencia_hz": round(sofi.frecuencia_hz, 3),
        "ciclo": sofi.ciclo_principal,
        "uptime_min": round((datetime.now() - sofi.inicio).total_seconds()/60, 2),
        "dispositivos": len(sofi.dispositivos),
        "ubicaciones_activas": len(sofi.osiris.ultimas_ubicaciones),
        "conexiones_activas": len(sofi.conexiones),
        "contadores": sofi.contadores,
        "firma_sistema": firmar_paquete(f"SOFIv9_{sofi.ciclo_principal}")
    })

# 📌 AGREGADO: Ruta para consultar todas las posiciones
@app.get("/posiciones")
async def ver_posiciones():
    return JSONResponse({
        "centro": {"lat": CFG.LAT_BASE, "lon": CFG.LON_BASE, "radio_km": CFG.RADIO_PERIMETRO_KM},
        "dispositivos": sofi.osiris.obtener_ubicaciones_activas(),
        "ts": datetime.now().isoformat()
    })

@app.websocket(CFG.WS_RUTA)  # 📌 Usando ruta definida en configuración
async def canal_kuhul(ws: WebSocket):
    await ws.accept()
    device_id = None
    try:
        # Identificación obligatoria
        inicial = await asyncio.wait_for(ws.receive_json(), timeout=10)
        if inicial.get("tipo") != "registro":
            await ws.close(code=1008, reason="Sin identificación")
            return

        device_id = inicial.get("device_id", f"dev_{int(datetime.now().timestamp())}")
        await sofi.registrar_dispositivo(device_id, inicial.get("info", {}), ws)
        logger.info(f"🔌 Conectado: {device_id}")

        # Confirmación
        await ws.send_json({
            "tipo": "bienvenida",
            "sistema": "SOFIv9.1.1",
            "frecuencia": CFG.FRECUENCIA_BASE,
            "ciclo": sofi.ciclo_principal,
            "firma": firmar_paquete(f"bienvenida_{device_id}")
        })

        # Bucle principal con latido
        while True:
            try:
                datos = await asyncio.wait_for(ws.receive_json(), timeout=CFG.INTERVALO_PING)
                sofi.actualizar_ciclo()

                if datos.get("tipo") == "telemetria":
                    res = await sofi.procesar_telemetria(device_id, datos.get("datos", {}))
                    # Retransmitir a otros nodos
                    for otro_id, otra_ws in sofi.conexiones.items():
                        if otro_id != device_id:
                            try:
                                await otra_ws.send_json({"tipo": "remota", "origen": device_id, "datos": res})
                            except:
                                pass

                elif datos.get("tipo") == "comando":
                    res = await sofi.procesar_comando(device_id, datos)
                    await ws.send_json({"tipo": "respuesta", "datos": res})

                elif datos.get("tipo") == "ping":
                    await ws.send_json({"tipo": "pong", "ciclo": sofi.ciclo_principal, "firma": firmar_paquete("pong")})

            except asyncio.TimeoutError:
                await ws.send_json({"tipo": "ping"})

    except WebSocketDisconnect:
        if device_id:
            sofi.conexiones.pop(device_id, None)
            sofi.dispositivos[device_id]["estado"] = "desconectado"
            logger.info(f"🔌 Desconectado: {device_id}")
    except Exception as e:
        sofi.contadores["errores"] += 1
        logger.error(f"❌ Error en canal {device_id}: {str(e)}")
        if device_id and device_id in sofi.conexiones:
            del sofi.conexiones[device_id]

# ── TAREAS DE FONDO ─────────────────────────────────────────────────────────
async def ciclo_coherencia():
    while True:
        await asyncio.sleep(1)
        sofi.actualizar_ciclo()

@app.on_event("startup")
async def iniciar():
    asyncio.create_task(ciclo_coherencia())
    sofi.estado = EstadoSistema.OPERATIVO
    logger.info("✅ SOFÍ v9.1.1 LISTO — Coherencia 12.3 Hz activa")

# ── ARRANQUE ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"🚀 SOFÍ v9.1.1 iniciando en puerto {CFG.PUERTO}")
    uvicorn.run(
        "sofi_v9_master_universal:app",
        host="0.0.0.0",
        port=CFG.PUERTO,
        log_level="info",
        reload=False,
        workers=1
    )
