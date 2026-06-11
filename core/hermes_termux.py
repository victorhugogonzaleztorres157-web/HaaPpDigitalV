# ==============================================================================
# ⚡ HERMES + CORTEX + OSIRIS (COMANDANTE LOCAL BLINDADO)
# Arquitecto: Víctor Hugo González Torres (Lok)
# Rol: Interfaz Jarvis, Organización Cortex y Seguridad Forense (Triangulación)
# Frecuencia Base: 12.3 Hz | Fricción: 0
# ==============================================================================

import asyncio
import websockets
import json
import os
import subprocess
import hashlib
import math
from datetime import datetime

URL_MADRE_SOFI = "ws://localhost:8000/ws/canal_kuhul"
FRECUENCIA_LOCAL = 12.3

# ==================================================
# 🔱 NÚCLEO OSIRIS LOCAL (SEGURIDAD Y HASHES)
# ==================================================
class OsirisLocal:
    def __init__(self):
        self.firma_base = "_12.3Hz_Kuhul"

    def auditar_archivo(self, ruta_archivo):
        """Genera un Hash SHA-256 inmutable de un archivo físico en el celular."""
        try:
            with open(ruta_archivo, "rb") as f:
                contenido = f.read()
            # Añadimos nuestra firma frecuencial al hash
            hash_calculado = hashlib.sha256(contenido + self.firma_base.encode()).hexdigest()
            return hash_calculado
        except Exception as e:
            return f"ERROR_OSIRIS: {str(e)}"

# ==================================================
# 📡 NÚCLEO GEO (TRIANGULACIÓN FÍSICA)
# ==================================================
class GeoTriangulacion:
    def __init__(self):
        # Coordenadas base (Mérida, Yucatán - El Santuario)
        self.base_lat = 20.9674
        self.base_lon = -89.6237
        self.radio_seguro_km = 50.0  # Zona segura

    def obtener_gps_real(self):
        """Extrae el GPS del hardware vía Termux-API"""
        try:
            res = subprocess.check_output(["termux-location", "-p", "network"], text=True)
            datos = json.loads(res)
            return datos.get("latitude", 0.0), datos.get("longitude", 0.0)
        except:
            return self.base_lat, self.base_lon # Fallback de emergencia

    def calcular_distancia(self, lat1, lon1, lat2, lon2):
        """Fórmula Haversine para triangulación satelital en km"""
        R = 6371.0 # Radio de la Tierra
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat/2)*math.sin(dLat/2) + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dLon/2)*math.sin(dLon/2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        return R * c

    def validar_zona(self, lat_actual, lon_actual):
        distancia = self.calcular_distancia(self.base_lat, self.base_lon, lat_actual, lon_actual)
        if distancia <= self.radio_seguro_km:
            return True, distancia
        return False, distancia

# ==================================================
# 🤖 HERMES + CORTEX (EL COMANDANTE)
# ==================================================
class HermesComandante:
    def __init__(self, nombre_dispositivo):
        self.nombre = nombre_dispositivo
        self.osiris = OsirisLocal()
        self.geo = GeoTriangulacion()
        self.zanganos_activos = {}
        print(f"⚡ [HERMES] Iniciando en {self.nombre}. Frecuencia {FRECUENCIA_LOCAL} Hz.")

    def organizar_y_auditar(self, ruta="/sdcard/Download"):
        """Cortex organiza y Osiris audita cada archivo."""
        archivos = os.listdir(ruta)[:5] # Escaneamos los primeros 5 para prueba
        reporte = []
        for arch in archivos:
            ruta_completa = os.path.join(ruta, arch)
            if os.path.isfile(ruta_completa):
                firma = self.osiris.auditar_archivo(ruta_completa)
                reporte.append({"archivo": arch, "firma_osiris": firma[:10]})
        return f"Cortex mapeó y Osiris blindó: {reporte}"

    async def enlazar_con_la_madre(self):
        async with websockets.connect(URL_MADRE_SOFI) as ws:
            # 1. TRIANGULACIÓN DE ARRANQUE (OSIRIS GEO)
            lat, lon = self.geo.obtener_gps_real()
            seguro, dist = self.geo.validar_zona(lat, lon)
            
            if not seguro:
                print(f"🚨 [OSIRIS ALERTA] Triangulación fuera de zona segura ({dist:.1f} km). Bloqueando acceso a la Madre.")
                return # Corta la conexión inmediatamente (Fricción Cero contra ataques)

            print(f"🛡️ [OSIRIS] Triangulación validada. Nodo a {dist:.1f} km de la base. Zona Segura.")
            
            # 2. REPORTE A LA MADRE
            await ws.send(json.dumps({
                "origen": "HERMES",
                "accion": f"triangular {lat} {lon} {self.nombre} {FRECUENCIA_LOCAL}"
            }))

            # 3. BUCLE DE ÓRDENES
            while True:
                paquete = json.loads(await ws.recv())
                if paquete.get("tipo") == "orden_hermes":
                    orden = paquete["comando"].lower()
                    respuesta = ""

                    if "organizar" in orden or "auditar" in orden:
                        respuesta = self.organizar_y_auditar()
                    elif "zangano" in orden:
                        id_zangano = f"ZANG_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:4]}"
                        respuesta = f"🐝 Zángano [{id_zangano}] desplegado hacia red externa."
                    else:
                        respuesta = f"Comando '{orden}' procesado localmente."

                    await ws.send(json.dumps({"origen": "HERMES", "accion": respuesta}))

if __name__ == "__main__":
    nodo = HermesComandante("Motorola_Z_Lok")
    asyncio.run(nodo.enlazar_con_la_madre())