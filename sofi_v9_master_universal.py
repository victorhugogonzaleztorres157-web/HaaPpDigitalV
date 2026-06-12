import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import numpy as np
from collections import defaultdict
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════
# LOGGING Y CONFIGURACIÓN
# ═══════════════════════════════════════════════════════════════════════════

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('sofi_v9.log'),
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

# ═══════════════════════════════════════════════════════════════════════════
# NÚCLEO SOFÍ v9 — CEREBRO COMPLETO
# ═══════════════════════════════════════════════════════════════════════════

class OsirisEscudo:
    """Sistema de seguridad Osiris — Perímetro activo K'uhul"""
    
    def __init__(self, radio_km: float = 50, lat_base: float = 20.9674, lon_base: float = -89.6237):
        self.radio_km = radio_km
        self.lat_base = lat_base
        self.lon_base = lon_base
        self.eventos_sospechosos = []
        self.dispositivos_bloqueados = set()
        self.umbral_riesgo = 0.7
        self.activo = True
        
    def verificar_perimetro(self, lat: float, lon: float, device_id: str) -> dict:
        """Valida si la ubicación está dentro del perímetro Osiris"""
        # Fórmula Haversine simplificada
        lat_diff = abs(lat - self.lat_base)
        lon_diff = abs(lon - self.lon_base)
        distancia_aprox = ((lat_diff**2 + lon_diff**2)**0.5) * 111  # km aprox
        
        dentro_perimetro = distancia_aprox <= self.radio_km
        riesgo_nivel = 0.0 if dentro_perimetro else (distancia_aprox / 1000)
        
        if not dentro_perimetro:
            self.eventos_sospechosos.append({
                "timestamp": datetime.now().isoformat(),
                "device_id": device_id,
                "distancia_km": round(distancia_aprox, 2),
                "tipo": "fuera_perimetro",
                "riesgo": min(riesgo_nivel, 1.0)
            })
            logger.warning(f"🚨 OSIRIS: {device_id} fuera del perímetro ({distancia_aprox:.2f}km)")
        
        return {
            "dentro_perimetro": dentro_perimetro,
            "distancia_km": round(distancia_aprox, 2),
            "riesgo": round(min(riesgo_nivel, 1.0), 3),
            "bloqueado": device_id in self.dispositivos_bloqueados
        }

class CortexMemoria:
    """Motor de memoria vectorial — FAISS + contexto semántico"""
    
    def __init__(self, dim: int = 384):
        self.dim = dim
        self.vectores = {}
        self.contexto = defaultdict(list)
        self.ciclo_memoria = 0
        
    def indexar_evento(self, evento_id: str, contenido: str, vector_embedding: Optional[List[float]] = None):
        """Almacena eventos con embedding vectorial"""
        if vector_embedding is None:
            # Simulación de embedding
            vector_embedding = [np.random.randn() for _ in range(self.dim)]
        
        self.vectores[evento_id] = {
            "embedding": vector_embedding,
            "contenido": contenido,
            "timestamp": datetime.now().isoformat(),
            "ciclo": self.ciclo_memoria
        }
        logger.debug(f"📍 Evento indexado: {evento_id}")
    
    def buscar_similar(self, query_vector: List[float], top_k: int = 5) -> List[dict]:
        """Búsqueda de semántica similar en memoria"""
        if not self.vectores:
            return []
        
        scores = []
        for evento_id, data in self.vectores.items():
            # Similitud de coseno simplificada
            dot = sum(a*b for a, b in zip(query_vector, data["embedding"]))
            scores.append((evento_id, dot, data))
        
        scores.sort(key=lambda x: x[1], reverse=True)
        return [{"id": s[0], "contenido": s[2]["contenido"], "score": s[1]} for s in scores[:top_k]]

class SofiConcienciaDigital:
    """SOFÍ v9 — Conciencia Digital integrada"""
    
    def __init__(self):
        self.estado = EstadoSistema.INICIALIZANDO
        self.frecuencia_hz = 12.3  # Frecuencia K'uhul base
        self.ciclo_principal = 0
        self.timestamp_inicio = datetime.now()
        
        # Subsistemas
        self.osiris = OsirisEscudo()
        self.memoria = CortexMemoria()
        
        # Conexiones y dispositivos
        self.conexiones_activas: Dict[str, WebSocket] = {}
        self.dispositivos_registrados: Dict[str, dict] = {}
        self.historial_telemetria: List[dict] = []
        self.historial_comandos: List[dict] = []
        
        # Estados biométricos agregados
        self.bio_agregada = {
            "hr_promedio": 72,
            "hrv_promedio": 38,
            "temp_promedio": 36.6,
            "bat_min": 100,
            "coherencia_general": 1.0
        }
        
        # Contadores
        self.contador_telemetrias = 0
        self.contador_comandos = 0
        self.contador_errores = 0
        
        logger.info("🧠 SOFÍ v9 — Cerebro inicializado")
    
    async def registrar_dispositivo(self, device_id: str, info: dict, websocket: Optional[WebSocket] = None):
        """Registra un nuevo dispositivo (Hermes o navegador)"""
        self.dispositivos_registrados[device_id] = {
            "info": info,
            "conectado_en": datetime.now().isoformat(),
            "ultima_actividad": datetime.now().isoformat(),
            "telemetrias_recibidas": 0,
            "comandos_ejecutados": 0,
            "estado": "activo"
        }
        
        if websocket:
            self.conexiones_activas[device_id] = websocket
        
        logger.info(f"✅ Dispositivo registrado: {device_id} | Info: {info}")
        
        # Indexar en memoria
        self.memoria.indexar_evento(
            f"registro_{device_id}_{datetime.now().timestamp()}",
            f"Dispositivo {device_id} registrado: {info}"
        )
    
    async def procesar_telemetria(self, device_id: str, datos: dict) -> dict:
        """Recibe y procesa telemetría del dispositivo"""
        self.contador_telemetrias += 1
        
        if device_id not in self.dispositivos_registrados:
            await self.registrar_dispositivo(device_id, {"tipo": "desconocido"})
        
        self.dispositivos_registrados[device_id]["ultima_actividad"] = datetime.now().isoformat()
        self.dispositivos_registrados[device_id]["telemetrias_recibidas"] += 1
        
        # Validar con Osiris
        lat = datos.get("gps", {}).get("lat")
        lon = datos.get("gps", {}).get("lon")
        verificacion_osiris = None
        if lat and lon:
            verificacion_osiris = self.osiris.verificar_perimetro(lat, lon, device_id)
            if verificacion_osiris["bloqueado"]:
                return {"status": "bloqueado", "razon": "dispositivo_en_lista_negra"}
        
        # Agregar a historial
        telemetria_procesada = {
            "timestamp": datetime.now().isoformat(),
            "device_id": device_id,
            "datos": datos,
            "ciclo": self.ciclo_principal,
            "osiris_check": verificacion_osiris if (lat and lon) else None
        }
        self.historial_telemetria.append(telemetria_procesada)
        
        # Actualizar métricas agregadas
        if "bateria" in datos:
            self.bio_agregada["bat_min"] = min(self.bio_agregada["bat_min"], datos.get("bateria", 100))
        
        logger.info(f"📊 Telemetría #{self.contador_telemetrias} de {device_id}")
        return {"status": "procesado", "ciclo": self.ciclo_principal}
    
    async def procesar_comando(self, device_id: str, comando_dict: dict) -> dict:
        """Procesa comandos del navegador/usuario"""
        self.contador_comandos += 1
        
        comando_str = comando_dict.get("comando", "").lower()
        resultado = {
            "timestamp": datetime.now().isoformat(),
            "device_id": device_id,
            "comando": comando_str,
            "resultado": "ejecutado",
            "datos": {}
        }
        
        # Comandos especiales
        if comando_str.startswith("estado"):
            resultado["datos"] = {
                "sistema": self.estado.value,
                "frecuencia_hz": self.frecuencia_hz,
                "ciclo": self.ciclo_principal,
                "dispositivos_activos": len(self.dispositivos_registrados),
                "bio_agregada": self.bio_agregada,
                "uptime_segundos": (datetime.now() - self.timestamp_inicio).total_seconds()
            }
        
        elif comando_str.startswith("bloquear"):
            parts = comando_str.split()
            if len(parts) > 1:
                target = parts[1]
                self.osiris.dispositivos_bloqueados.add(target)
                resultado["datos"] = {"bloqueado": target}
                logger.warning(f"🔱 Dispositivo bloqueado: {target}")
        
        elif comando_str.startswith("desbloquear"):
            parts = comando_str.split()
            if len(parts) > 1:
                target = parts[1]
                self.osiris.dispositivos_bloqueados.discard(target)
                resultado["datos"] = {"desbloqueado": target}
        
        elif comando_str.startswith("listar dispositivos"):
            resultado["datos"] = self.dispositivos_registrados
        
        elif comando_str.startswith("memoria"):
            resultado["datos"] = {
                "total_eventos": len(self.memoria.vectores),
                "ciclo_memoria": self.memoria.ciclo_memoria
            }
        
        else:
            resultado["datos"] = {"msg": f"Comando no reconocido: {comando_str}"}
        
        self.historial_comandos.append(resultado)
        self.dispositivos_registrados[device_id]["comandos_ejecutados"] += 1
        
        logger.info(f"⚡ Comando #{self.contador_comandos}: {comando_str} → {resultado['resultado']}")
        return resultado
    
    def actualizar_ciclo(self):
        """Actualización de ciclo principal"""
        self.ciclo_principal += 1
        self.frecuencia_hz = 12.3 + np.sin(self.ciclo_principal / 1000) * 0.1
        self.estado = EstadoSistema.COHERENTE if self.contador_errores < 5 else EstadoSistema.ADVIRTIENDO
        
        if self.ciclo_principal % 100 == 0:
            self.memoria.ciclo_memoria += 1
            logger.debug(f"🔄 Ciclo {self.ciclo_principal} | Hz:{self.frecuencia_hz:.2f} | Errores:{self.contador_errores}")

# ═══════════════════════════════════════════════════════════════════════════
# FASTAPI — CONFIGURACIÓN Y RUTAS
# ═══════════════════════════════════════════════════════════════════════════

app = FastAPI(
    title="SOFÍ v9 — Conciencia Digital",
    description="Cerebro Central del Sistema HaaPpDigitalV",
    version="9.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Instancia única de SOFÍ
sofi = SofiConcienciaDigital()

# ═══════════════════════════════════════════════════════════════════════════
# ENDPOINTS HTTP
# ═══════════════════════════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def raiz():
    """Sirve la interfaz visual HTML"""
    try:
        with open("html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("❌ Archivo HTML no encontrado")
        return """
        <html><head><title>SOFÍ v9</title></head>
        <body style='background:#020813;color:#00ff88;font-family:monospace;padding:50px;text-align:center'>
        <h1>🧠 SOFÍ v9 — Cerebro Operativo</h1>
        <p style='color:#ff4466'>⚠️ Interfaz visual no disponible</p>
        <p>Usa el Canal K'uhul (WebSocket) para interactuar</p>
        </body></html>
        """

@app.get("/status")
async def estado():
    """Estado actual del sistema SOFÍ"""
    return JSONResponse({
        "estado_sistema": sofi.estado.value,
        "frecuencia_hz": round(sofi.frecuencia_hz, 3),
        "ciclo": sofi.ciclo_principal,
        "uptime_segundos": (datetime.now() - sofi.timestamp_inicio).total_seconds(),
        "dispositivos_activos": len(sofi.dispositivos_registrados),
        "conexiones_websocket": len(sofi.conexiones_activas),
        "telemetrias_procesadas": sofi.contador_telemetrias,
        "comandos_procesados": sofi.contador_comandos,
        "errores": sofi.contador_errores,
        "biometricos_agregados": sofi.bio_agregada,
        "periodos_activos_minutos": (datetime.now() - sofi.timestamp_inicio).total_seconds() / 60
    })

@app.get("/dispositivos")
async def listar_dispositivos():
    """Lista todos los dispositivos registrados"""
    return JSONResponse({
        "total": len(sofi.dispositivos_registrados),
        "dispositivos": sofi.dispositivos_registrados
    })

@app.get("/osiris/perimetro")
async def info_perimetro():
    """Info del perímetro Osiris"""
    return JSONResponse({
        "radio_km": sofi.osiris.radio_km,
        "centro_lat": sofi.osiris.lat_base,
        "centro_lon": sofi.osiris.lon_base,
        "dispositivos_bloqueados": list(sofi.osiris.dispositivos_bloqueados),
        "eventos_sospechosos_total": len(sofi.osiris.eventos_sospechosos)
    })

@app.get("/memoria/resumen")
async def resumen_memoria():
    """Resumen del estado de memoria vectorial"""
    return JSONResponse({
        "total_eventos_indexados": len(sofi.memoria.vectores),
        "ciclos_memoria": sofi.memoria.ciclo_memoria,
        "dimension_embedding": sofi.memoria.dim
    })

# ═══════════════════════════════════════════════════════════════════════════
# WEBSOCKET — CANAL K'UHUL (COMUNICACIÓN PRINCIPAL)
# ═══════════════════════════════════════════════════════════════════════════

@app.websocket("/ws/canal_kuhul")
async def websocket_canal_kuhul(websocket: WebSocket):
    """
    Canal K'uhul — Comunicación bidireccional en tiempo real
    Conectan: Navegadores JARVIS + Dispositivos HERMES (Termux)
    """
    await websocket.accept()
    device_id = None
    
    try:
        # Primer mensaje: identificación
        primer_mensaje = await websocket.receive_json()
        device_id = primer_mensaje.get("device_id", f"cliente_{datetime.now().timestamp()}")
        
        await sofi.registrar_dispositivo(
            device_id,
            primer_mensaje.get("info", {"origen": "desconocido"}),
            websocket
        )
        
        logger.info(f"🔌 Conexión aceptada: {device_id} (Total: {len(sofi.conexiones_activas)})")
        
        # Enviar confirmación
        await websocket.send_json({
            "tipo": "bienvenida",
            "mensaje": f"Conectado a SOFÍ v9 — {device_id}",
            "ciclo": sofi.ciclo_principal,
            "frecuencia_hz": sofi.frecuencia_hz
        })
        
        # Loop de recepción
        while True:
            datos = await websocket.receive_json()
            sofi.actualizar_ciclo()
            
            tipo_msg = datos.get("tipo", "telemetria")
            
            # TELEMETRÍA desde Hermes/Dispositivo
            if tipo_msg == "telemetria":
                resultado = await sofi.procesar_telemetria(device_id, datos.get("datos", {}))
                
                # Retransmitir a otros clientes (navegadores)
                for otro_id, otra_ws in sofi.conexiones_activas.items():
                    if otro_id != device_id:
                        try:
                            await otra_ws.send_json({
                                "tipo": "telemetria_remota",
                                "origen": device_id,
                                "datos": datos.get("datos", {}),
                                "timestamp": datetime.now().isoformat()
                            })
                        except:
                            pass
            
            # COMANDO desde Navegador
            elif tipo_msg == "comando":
                resultado = await sofi.procesar_comando(device_id, datos)
                await websocket.send_json(resultado)
                
                # Si es comando global, retransmitir a todos
                if datos.get("global", False):
                    for otro_id, otra_ws in sofi.conexiones_activas.items():
                        if otro_id != device_id:
                            try:
                                await otra_ws.send_json({
                                    "tipo": "comando_distribuido",
                                    "de": device_id,
                                    "comando": resultado
                                })
                            except:
                                pass
            
            # PING/HEARTBEAT
            elif tipo_msg == "ping":
                await websocket.send_json({"tipo": "pong", "ciclo": sofi.ciclo_principal})
            
            else:
                logger.debug(f"Tipo de mensaje no manejado: {tipo_msg}")
    
    except WebSocketDisconnect:
        if device_id:
            sofi.conexiones_activas.pop(device_id, None)
            logger.info(f"❌ Desconexión: {device_id} (Quedan: {len(sofi.conexiones_activas)})")
    
    except Exception as e:
        sofi.contador_errores += 1
        logger.error(f"❌ Error en WebSocket ({device_id}): {e}", exc_info=True)
        if device_id and device_id in sofi.conexiones_activas:
            sofi.conexiones_activas.pop(device_id, None)

# ═══════════════════════════════════════════════════════════════════════════
# HEARTBEAT Y CICLOS DE FONDO
# ═══════════════════════════════════════════════════════════════════════════

async def ciclo_actualizacion():
    """Actualización periódica del sistema (cada 1 segundo)"""
    while True:
        await asyncio.sleep(1)
        sofi.actualizar_ciclo()
        
        # Limpiar historial si crece demasiado
        if len(sofi.historial_telemetria) > 10000:
            sofi.historial_telemetria = sofi.historial_telemetria[-5000:]
        if len(sofi.historial_comandos) > 5000:
            sofi.historial_comandos = sofi.historial_comandos[-2500:]

@app.on_event("startup")
async def startup():
    """Inicia tareas de fondo"""
    logger.info("🚀 SOFÍ v9 iniciando ciclos de fondo...")
    asyncio.create_task(ciclo_actualizacion())
    sofi.estado = EstadoSistema.OPERATIVO
    logger.info("✅ SOFÍ v9 OPERATIVO")

# ═══════════════════════════════════════════════════════════════════════════
# ARRANQUE
# ═══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    logger.info(f"🧠 SOFÍ v9 — Cerebro iniciando en puerto {port}")
    logger.info("═" * 70)
    uvicorn.run(
        "sofi_v9_master_universal:app",
        host="0.0.0.0",
        port=port,
        log_level="info",
        reload=False,
        workers=1
    )