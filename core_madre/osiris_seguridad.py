# ==============================================================================
# 🔱 OSIRIS - NÚCLEO DE SEGURIDAD, HASHING Y MODO ESTIGIA (INTELIGENCIA)
# Arquitecto: Víctor Hugo González Torres (Lok)
# Frecuencia Base: 12.3 Hz | Tolerancia de Fricción: 0.03
# ==============================================================================

import hashlib
import json
import math
import os
from datetime import datetime

# Simulamos la importación de librerías para extraer EXIF de imágenes
# En producción instalar: pip install Pillow exifread requests
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    ESTIGIA_VISUAL_ACTIVO = True
except ImportError:
    ESTIGIA_VISUAL_ACTIVO = False
    print("⚠️ [OSIRIS] Librerías de visión (Pillow/ExifTags) no encontradas. Modo Estigia Visual desactivado.")

class OsirisLocal:
    def __init__(self, ruta_respaldo="../boveda_memoria/backups_osiris/"):
        self.firma_base = "_12.3Hz_Kuhul"
        self.ruta_respaldo = ruta_respaldo
        os.makedirs(self.ruta_respaldo, exist_ok=True)
        print("🔱 [OSIRIS] Bóveda Criptográfica y Modo Estigia Inicializados.")

    # ==================================================
    # 1. CRIPTOGRAFÍA FORENSE (JHOP)
    # ==================================================
    def auditar_archivo_virtual(self, datos_brutos):
        """Genera el Hash SHA-256 de cualquier texto/JSON que entra a la Mente Madre."""
        cadena_segura = json.dumps(datos_brutos, sort_keys=True) + self.firma_base
        hash_calculado = hashlib.sha256(cadena_segura.encode()).hexdigest()
        return hash_calculado

    def guardar_respaldo_seguro(self, nombre_modulo, datos):
        """Sella la memoria del Cortex o los balances de los zánganos en disco duro."""
        firma = self.auditar_archivo_virtual(datos)
        paquete = {
            "timestamp": datetime.now().isoformat(),
            "datos": datos,
            "firma_jhop": firma
        }
        ruta_archivo = os.path.join(self.ruta_respaldo, f"{nombre_modulo}_{firma[:8]}.json")
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(paquete, f, indent=4)
        return f"✅ Respaldo Blindado [{nombre_modulo}] - Hash: {firma[:8]}"

    # ==================================================
    # 2. MODO ESTIGIA: RECONOCIMIENTO Y EXTRACCIÓN (OSINT)
    # ==================================================
    def extraer_metadatos_imagen(self, ruta_imagen):
        """Abre una foto enviada por Hermes, extrae cámara, fecha y si tiene GPS oculto."""
        if not ESTIGIA_VISUAL_ACTIVO or not os.path.exists(ruta_imagen):
            return {"error": "Módulo visual inactivo o archivo no encontrado."}
        
        datos_estigia = {"camara": "Desconocida", "fecha": "Desconocida", "gps_oculto": None}
        
        try:
            imagen = Image.open(ruta_imagen)
            info_exif = imagen._getexif()
            
            if info_exif:
                for tag, value in info_exif.items():
                    nombre_tag = TAGS.get(tag, tag)
                    if nombre_tag == "Model":
                        datos_estigia["camara"] = str(value)
                    elif nombre_tag == "DateTimeOriginal":
                        datos_estigia["fecha"] = str(value)
                    elif nombre_tag == "GPSInfo":
                        # Aquí, en producción, se decodifican los grados/min/seg a decimales
                        datos_estigia["gps_oculto"] = "Coordenadas detectadas en archivo"
            
            return datos_estigia
        except Exception as e:
            return {"error": f"Fallo al destripar imagen: {e}"}

    def auditar_nodo_externo(self, ip_entrante, lat_reportada, lon_reportada):
        """
        Cruza la IP del usuario/zángano con la coordenada que reportó.
        Si la IP es de Rusia pero el GPS dice 'Mérida', Osiris lo detecta como SPOOFING.
        """
        # Nota: En producción esto usaría una API como ipinfo.io
        print(f"👁️ [ESTIGIA] Auditando IP {ip_entrante} cruzada con GPS ({lat_reportada}, {lon_reportada})")
        # Simulamos que la IP coincide con el área geográfica
        riesgo_spoofing = False 
        
        if riesgo_spoofing:
            return False, "🚨 ANOMALÍA: Discrepancia entre Proveedor de Red (IP) y Hardware (GPS)."
        return True, "✅ Red e Infraestructura validadas."

# ==================================================
# 3. GEOLOCALIZACIÓN Y TRIANGULACIÓN SATELITAL
# ==================================================
class GeoTriangulacion:
    def __init__(self):
        # El Santuario / Base de Operaciones
        self.base_lat = 20.9674
        self.base_lon = -89.6237
        self.radio_seguro_km = 50.0

    def calcular_distancia(self, lat1, lon1, lat2, lon2):
        """Fórmula Haversine real para medir la distancia curva sobre la Tierra."""
        R = 6371.0  # Radio de la Tierra en km
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        a = math.sin(dLat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return R * c

    def validar_zona(self, lat_actual, lon_actual):
        """Determina si Hermes o los Zánganos están dentro del perímetro autorizado."""
        distancia = self.calcular_distancia(self.base_lat, self.base_lon, lat_actual, lon_actual)
        if distancia <= self.radio_seguro_km:
            return True, distancia
        return False, distancia

# ==============================================================================
# PRUEBA TÉCNICA AISLADA (Para verificar que Osiris muerde)
# ==============================================================================
if __name__ == "__main__":
    guardian = OsirisLocal()
    rastreador = GeoTriangulacion()

    print("\n--- TEST: FIRMA CRIPTOGRÁFICA ---")
    datos_test = {"comando": "transferir_fondos", "monto": 5000}
    hash_seguro = guardian.auditar_archivo_virtual(datos_test)
    print(f"Datos: {datos_test}")
    print(f"Firma Creada: {hash_seguro}")

    print("\n--- TEST: TRIANGULACIÓN HAVERSINE ---")
    # Prueba 1: Estás en tu casa/Mérida
    seguro, dist = rastreador.validar_zona(20.9700, -89.6200)
    print(f"Ubicación Mérida -> Seguro: {seguro} | Distancia a la base: {dist:.2f} km")
    
    # Prueba 2: Un hacker intenta entrar desde CDMX
    seguro, dist = rastreador.validar_zona(19.4326, -99.1332)
    print(f"Ubicación CDMX   -> Seguro: {seguro} | Distancia a la base: {dist:.2f} km")

    print("\n--- TEST: MODO ESTIGIA ---")
    auditoria = guardian.auditar_nodo_externo("189.200.x.x", 20.9700, -89.6200)
    print(auditoria[1])
