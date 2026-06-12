import os
import json
import math
import time
import subprocess
import asyncio
import websockets
from dotenv import load_dotenv

load_dotenv()

# --------------------------
# 🔱 OSIRIS LIGERO (para validar y firmar en el equipo)
# --------------------------
class OsirisLocal:
    FIRMA_BASE = "_12.3Hz_Kuhul_Osiris"
    def firmar(self, datos):
        import hashlib
        txt = json.dumps(datos, sort_keys=True, ensure_ascii=False) + self.FIRMA_BASE
        return hashlib.sha256(txt.encode()).hexdigest()

    def haversine(self, lat1, lon1, lat2, lon2):
        R = 6371
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# --------------------------
# ⚡ HERMES FÍSICO — ACCESO SIN LÍMITES
# --------------------------
class HermesTotal:
    def __init__(self):
        self.osiris = OsirisLocal()
        self.nombre = os.getenv("HERMES_NOMBRE", "HaaPp_Merida_01")

    # GPS real
    def gps(self):
        try:
            out = subprocess.check_output(["termux-location", "-p", "gps"], timeout=10)
            geo = json.loads(out)
            return float(geo["latitude"]), float(geo["longitude"])
        except:
            return 20.9674, -89.6237

    # Batería y estado
    def bateria(self):
        try:
            return json.loads(subprocess.check_output(["termux-battery-status"], timeout=5))
        except:
            return {"nivel": "?", "estado": "desconocido"}

    # Cámara + extracción EXIF (envía ubicación al sistema)
    def foto_con_exif(self):
        ruta = f"/sdcard/DCIM/OSIRIS_CAPTURA_{int(time.time())}.jpg"
        try:
            subprocess.run(["termux-camera-photo", "-c", "0", ruta], timeout=12, check=True)
            # Extraer metadatos
            from PIL import Image
            from PIL.ExifTags import TAGS, GPSTAGS
            img = Image.open(ruta)
            exif = img._getexif() or {}
            datos = {"archivo": ruta, "fecha": None, "lat": None, "lon": None}
            for tag, val in exif.items():
                nombre = TAGS.get(tag)
                if nombre == "DateTimeOriginal":
                    datos["fecha"] = val
                if nombre == "GPSInfo":
                    gps = {}
                    for gt in val:
                        gps_nombre = GPSTAGS.get(gt)
                        gps[gps_nombre] = val[gt]
                    if "GPSLatitude" in gps and "GPSLongitude" in gps:
                        def conv(coord, ref):
                            d, m, s = coord
                            res = d + m/60 + s/3600
                            return -res if ref in ("S", "W") else res
                        datos["lat"] = conv(gps["GPSLatitude"], gps["GPSLatitudeRef"])
                        datos["lon"] = conv(gps["GPSLongitude"], gps["GPSLongitudeRef"])
            return datos
        except Exception as e:
            return {"error": str(e)}

    # Ejecutar cualquier orden que pida Cortex
    async def ejecutar_orden(self, orden):
        if "gps" in orden.lower():
            lat, lon = self.gps()
            return {"tipo": "ubicacion", "lat": lat, "lon": lon, "firma": self.osiris.firmar({"lat":lat,"lon":lon})[:12]}
        elif "foto" in orden.lower() or "exif" in orden.lower():
            return self.foto_con_exif()
        elif "bateria" in orden.lower():
            return self.bateria()
        elif "archivos" in orden.lower():
            carpeta = "/sdcard/Download"
            return {"carpeta": carpeta, "cantidad": len(os.listdir(carpeta))}
        else:
            return {"mensaje": f"Orden recibida: {orden}"}

    # Conexión continua al núcleo
    async def conectar(self):
        url = os.getenv("SOFI_URL")
        print(f"⚡ HERMES TOTAL conectando a: {url}")
        while True:
            try:
                async with websockets.connect(url) as ws:
                    lat, lon = self.gps()
                    await ws.send(json.dumps({
                        "origen": self.nombre,
                        "comando": "Nodo Hermes activo — control total",
                        "lat": lat, "lon": lon
                    }))
                    print("✅ Conectado. Esperando órdenes de Cortex/Osiris...")
                    while True:
                        mensaje = await ws.recv()
                        datos = json.loads(mensaje)
                        accion = datos.get("accion", "")
                        resultado = await self.ejecutar_orden(accion)
                        await ws.send(json.dumps({
                            "origen": self.nombre,
                            "respuesta": resultado,
                            "reflejo": "actualizar_panel"
                        }))
            except Exception as e:
                print(f"⚠️ Conexión caída: {e} — Reintentando en 5s...")
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(HermesTotal().conectar())
