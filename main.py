# ==============================================================================
# 🌌 SISTEMA UNIFICADO SOFI - REPOSITORIO: HaaPbDigtalV
# Arquitecto: Víctor Hugo González Torres (Lok)
# Módulos: Cortex (Memoria) | Hermes (Ejecución) | Osiris (Seguridad/Geo)
# Frecuencia Base: 12.3 Hz | Fricción: 0 | Latencia: 0
# ==============================================================================

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
import hashlib
import json
import time
from datetime import datetime
import os
from geopy.distance import geodesic

app = FastAPI(title="HaaPbDigtalV - Nexo Central")

# ==================================================
# 🔱 NÚCLEO 1: OSIRIS (SEGURIDAD, HASH Y COHERENCIA)
# ==================================================
class OsirisCore:
    def __init__(self, ruta_respaldo="./backups_osiris/"):
        self.ruta_respaldo = ruta_respaldo
        self.integridad_registros = {}
        os.makedirs(self.ruta_respaldo, exist_ok=True)
        print("🔱 [OSIRIS] Bóveda de seguridad inicializada.")

    def generar_firma(self, datos):
        """Crea huella digital inmutable anclada a la frecuencia K'uhul"""
        cadena = json.dumps(datos, sort_keys=True) + "_12.3Hz"
        return hashlib.sha256(cadena.encode()).hexdigest()[:16]

    def verificar_integridad(self, datos, firma):
        return self.generar_firma(datos) == firma

    def guardar_respaldo(self, nombre, contenido):
        firma = self.generar_firma(contenido)
        registro = {
            "fecha": datetime.now().isoformat(),
            "datos": contenido,
            "firma": firma,
            "estado": "ACTIVO - PROTEGIDO"
        }
        ruta_archivo = f"{self.ruta_respaldo}{nombre}_{firma[:6]}.json"
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(registro, f, indent=2)
        self.integridad_registros[nombre] = firma
        return f"✅ OSIRIS: Respaldo blindado | Firma SHA-256: {firma[:8]}"

    def validar_coherencia(self, valor_frecuencia):
        tolerancia = 0.03
        return abs(valor_frecuencia - 12.3) <= tolerancia

# ==================================================
# 📡 NÚCLEO 2: TELEGEO (TRIANGULACIÓN Y GLOBO 3D)
# ==================================================
class GeoTeletransporte:
    def __init__(self, osiris_core):
        self.osiris = osiris_core
        self.ubicaciones = []
        self.rutas = []
        self.ubicacion_actual = None

    def registrar_nodo(self, lat, lon, nombre, ip_origen, frecuencia_reportada):
        """Registra un punto solo si vibra a 12.3 Hz. Si no, lo marca como amenaza."""
        es_seguro = self.osiris.validar_coherencia(frecuencia_reportada)
        color = "#00ffcc" if es_seguro else "#ff0000" # Verde neón (Seguro) / Rojo (Amenaza)
        
        nodo = {
            "lat": float(lat), "lng": float(lon), 
            "name": f"{nombre} [{'SEGURO' if es_seguro else 'AMENAZA'}]",
            "color": color,
            "ip": ip_origen
        }
        self.ubicaciones.append(nodo)
        self.ubicacion_actual = (float(lat), float(lon))
        return f"📍 Nodo {nombre} mapeado. Estado de Seguridad: {es_seguro}"

    def crear_ruta_cuantica(self, lat1, lon1, lat2, lon2):
        self.rutas.append({
            "startLat": float(lat1), "startLng": float(lon1),
            "endLat": float(lat2), "endLng": float(lon2)
        })
        return "🛤️ Canal K'uhul trazado entre nodos."

# ==================================================
# 🧠 NÚCLEO 3 Y 4: CORTEX (MEMORIA) Y HERMES (EJECUTOR)
# ==================================================
class CortexCore:
    def __init__(self):
        self.memoria = {}
    
    def guardar(self, id_unico, contenido):
        self.memoria[id_unico] = {"datos": contenido, "fecha": time.time()}
        return f"🧠 CORTEX: Recuerdo guardado [{id_unico}]"

class HermesInterface:
    def __init__(self, cortex, geo, osiris):
        self.cortex = cortex
        self.geo = geo
        self.osiris = osiris

    def procesar_comando(self, texto):
        partes = texto.lower().split()
        accion = partes[0] if partes else ""

        if accion == "guardar":
            return self.cortex.guardar(partes[1], " ".join(partes[2:]))
        elif accion == "respaldo":
            return self.osiris.guardar_respaldo("DatosSofi", self.cortex.memoria)
        elif accion == "triangular":
            return self.geo.registrar_nodo(partes[1], partes[2], partes[3], "192.168.1.x", float(partes[4]))
        return "❓ HERMES: Comando físico no reconocido."

# ==================================================
# 🚀 INICIALIZACIÓN DEL SISTEMA
# ==================================================
osiris = OsirisCore()
cortex = CortexCore()
telegeo = GeoTeletransporte(osiris)
sofi = HermesInterface(cortex, telegeo, osiris)

# ==================================================
# 🌐 ENDPOINTS DE LA INTERFAZ VISUAL (GLOBO)
# ==================================================
INTERFAZ_GLOBO = """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>🌍 SOFI - Monitor Geo-Táctico</title>
  <script src="https://unpkg.com/globe.gl"></script>
  <style>
    body { margin:0; background:#050814; font-family: monospace; color: #0fa;}
    #globe { width:100vw; height:100vh; }
    #overlay { position: absolute; top: 10px; left: 10px; z-index: 10; background: rgba(0,0,0,0.7); padding: 15px; border: 1px solid #0fa; border-radius: 8px;}
  </style>
</head>
<body>
  <div id="overlay">
    <h2>🛰️ HaaPbDigtalV - Monitor K'uhul</h2>
    <p>Frecuencia Base: 12.3 Hz</p>
    <p>Nodos Activos: <span id="contador">0</span></p>
  </div>
  <div id="globe"></div>
  <script>
    const world = Globe()
      .globeImageUrl('//unpkg.com/three-globe/example/img/earth-night.jpg')
      .backgroundColor('#050814')
      .arcColor(() => '#00ffcc') // Verde cian para datos seguros
      .arcStroke(0.8)
      .arcDashLength(0.5)
      .arcDashGap(0.2)
      .arcDashAnimateTime(1500)
      .pointColor('color') // Toma el color dinámico del JSON (Verde o Rojo)
      .pointAltitude(0.1)
      .pointRadius(0.4)
      (document.getElementById('globe'));

    // Bucle de Fricción Cero para actualizar el mapa
    setInterval(() => {
        fetch('/api/ubicaciones').then(r=>r.json()).then(d=>{
          world.pointsData(d.puntos);
          world.arcsData(d.rutas);
          document.getElementById('contador').innerText = d.puntos.length;
        });
    }, 2000);
  </script>
</body>
</html>
"""

@app.get("/")
def ver_globo():
    return HTMLResponse(content=INTERFAZ_GLOBO)

@app.get("/api/ubicaciones")
def datos_geo():
    return {"puntos": telegeo.ubicaciones, "rutas": telegeo.rutas}

@app.post("/api/comando")
def ejecutar_comando(comando: str):
    resultado = sofi.procesar_comando(comando)
    return {"status": "Ejecutado", "resultado": resultado}

# Prueba interna de arranque
if __name__ == "__main__":
    import uvicorn
    print("Iniciando simulación de nodos iniciales...")
    sofi.procesar_comando("triangular 20.9674 -89.6237 Merida_Central 12.3") # Seguro (Verde)
    sofi.procesar_comando("triangular 40.7128 -74.0060 Intento_Hack 10.5")   # Amenaza (Rojo)
    sofi.procesar_comando("respaldo")
    uvicorn.run(app, host="0.0.0.0", port=8000)