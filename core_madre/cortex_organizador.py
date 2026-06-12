# ==============================================================================
# ⚡ HERMES PRO - COMANDANTE LOCAL (VERSIÓN DIOS DIGITAL)
# Arquitecto: Víctor Hugo González Torres (Lok)
# Misión: Dominio físico, Triangulación forense y Ejecución manual.
# Frecuencia Base: 12.3 Hz | Estado: Sincronización Total con la Madre
# ==============================================================================

import asyncio
import websockets
import json
import subprocess
import os
import hashlib
import time

# Importamos Osiris y Cortex como módulos de tu estructura
from core_madre.osiris_seguridad import OsirisEstigia, GeoTriangulacion
from core_madre.cortex_organizador import MaisonCortex

class HermesPro:
    def __init__(self, nombre="Terminal_Lok"):
        self.nombre = nombre
        self.osiris = OsirisEstigia()
        self.geo = GeoTriangulacion()
        self.cortex = MaisonCortex()
        self.modo_seguridad = "BLINDADO" # Osiris activo 24/7
        print(f"⚡ [HERMES PRO] Nodo '{self.nombre}' sincronizado. Osiris y Cortex integrados.")

    # --- EJECUCIÓN MANUAL (GATILLO DEL ARQUITECTO) ---
    def ejecutar_orden_manual(self, comando, payload=None):
        """El único acceso al hardware. Activación 100% manual."""
        
        # Auditoría Forense de Osiris antes de cualquier movimiento
        log_evento = {"cmd": comando, "ts": time.time()}
        firma = self.osiris.auditar_paquete(log_evento)
        
        # Ejecución
        if comando == "FOTO":
            # RECONOCIMIENTO ESTIGIA (Captura y Análisis Forense)
            ruta = f"/sdcard/DCIM/OSIRIS_{int(time.time())}.jpg"
            subprocess.run(["termux-camera-photo", "-c", "0", ruta])
            metadatos = self.osiris.destripar_imagen_exif(ruta)
            return {"resultado": "Imagen Estigia capturada", "ADN": metadatos, "Firma": firma[:8]}
        
        elif comando == "LIMPIAR":
            # Organización Cortex Local
            resultado = self.cortex.asimilar(f"Limpieza iniciada: {payload.get('ruta', 'Download')}")
            return {"resultado": resultado, "Firma": firma[:8]}
        
        elif comando == "TRIANGULAR":
            lat, lon = self.geo.obtener_gps_real()
            seguro, dist = self.geo.validar_zona(lat, lon)
            return {"gps": (lat, lon), "seguro": seguro, "distancia": dist, "Firma": firma[:8]}

        return {"error": "Comando no autorizado o inexistente."}

    # --- PUENTE K'UHUL ---
    async def establecer_comunicacion(self, url_madre):
        async with websockets.connect(url_madre) as ws:
            print("🔗 [HERMES] Canal 12.3 Hz abierto.")
            while True:
                # Hermes envía telemetría constante pero espera orden para actuar
                lat, lon = self.geo.obtener_gps_real()
                await ws.send(json.dumps({"tipo": "telemetria", "lat": lat, "lon": lon}))
                
                # Esperar instrucciones de la Madre
                mensaje = await ws.recv()
                paquete = json.loads(mensaje)
                
                if "ejecutar" in paquete:
                    print(f"⚙️ Ejecutando orden manual: {paquete['ejecutar']}")
                    resultado = self.ejecutar_orden_manual(paquete['ejecutar'], paquete.get('payload', {}))
                    await ws.send(json.dumps({"tipo": "reporte", "resultado": resultado}))

if __name__ == "__main__":
    hermes = HermesPro()
    asyncio.run(hermes.establecer_comunicacion("wss://haappdigitalv-core.onrender.com/ws/canal_kuhul"))
