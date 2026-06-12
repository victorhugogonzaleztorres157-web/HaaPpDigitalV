# ==============================================================================
# ⚡ HERMES · COMANDANTE LOCAL Y EJECUTOR BINEURAL (VERSIÓN PRO)
# Arquitecto: Víctor Hugo González Torres (Lok)
# Misión: Dominio físico, Triangulación Osiris y Enlace de Frecuencia 12.3 Hz
# Integración: Hermes (Ejecución) + Cortex (Memoria Local) + Osiris (Seguridad)
# ==============================================================================

import asyncio
import websockets
import json
import os
import subprocess
import time
from datetime import datetime
# Importamos la seguridad forense y geo de Osiris que ya definimos
from osiris_seguridad import OsirisEstigia, GeoTriangulacion
from cortex_organizador import MaisonCortex

class HermesPro:
    def __init__(self, nombre_dispositivo="Hermes_Alpha_Node"):
        self.nombre = nombre_dispositivo
        self.osiris = OsirisEstigia()
        self.geo = GeoTriangulacion()
        self.cortex = MaisonCortex()
        self.estado_sistema = "SYNCHRONIZED_12.3HZ"
        print(f"⚡ [HERMES PRO] Nodo {self.nombre} activo. Integración total cargada.")

    # --- COMANDOS DE HARDWARE (EL BRAZO FÍSICO) ---
    def procesar_orden(self, comando, payload):
        """Procesa órdenes de la Madre SOFÍ o de tu Interfaz Cortex."""
        cmd = comando.lower()
        
        # Modo Estigia Visual (Cámara/Sensores)
        if "foto" in cmd:
            ruta = f"/sdcard/DCIM/OSIRIS_{int(time.time())}.jpg"
            subprocess.run(["termux-camera-photo", "-c", "0", ruta])
            metadatos = self.osiris.destripar_imagen_exif(ruta)
            return {"resultado": "Captura estigia realizada", "adn_imagen": metadatos}
        
        # Cortex Local (Organización)
        elif "organizar" in cmd:
            resultado = self.cortex.asimilar(f"Organización iniciada en: {payload.get('ruta', '/sdcard/Download')}")
            return {"resultado": resultado}
        
        # Geolocalización táctica
        elif "gps" in cmd:
            lat, lon = self.geo.obtener_gps_real()
            return {"lat": lat, "lon": lon, "status": "Triangulación actualizada"}

        # Estado del hardware
        elif "bateria" in cmd:
            return {"status": self.cortex.asimilar("Reporte de batería solicitado")}
        
        return {"error": "Acción no reconocida en el plano físico."}

    # --- ENLACE CUÁNTICO (BUS DE COHERENCIA) ---
    async def correr_nodo(self, url_madre):
        while True:
            try:
                async with websockets.connect(url_madre) as ws:
                    print(f"🔗 [HERMES] Conectado a {url_madre}")
                    
                    while True:
                        # Obtenemos telemetría local
                        lat, lon = self.geo.obtener_gps_real()
                        
                        # Esperar instrucción de la Madre
                        paquete = json.loads(await ws.recv())
                        
                        # Ejecutar orden y auditar con Osiris antes de responder
                        if "comando" in paquete:
                            resultado_fisico = self.procesar_orden(paquete["comando"], paquete.get("payload", {}))
                            
                            # Firma forense de Osiris antes de enviar
                            firma = self.osiris.auditar_paquete(resultado_fisico)
                            
                            respuesta_final = {
                                "origen": self.nombre,
                                "lat": lat,
                                "lon": lon,
                                "ejecucion": resultado_fisico,
                                "firma_jhop": firma
                            }
                            await ws.send(json.dumps(respuesta_final))
            except Exception as e:
                print(f"⚠️ [HERMES] Pérdida de coherencia ({e}). Reintento en 5s...")
                await asyncio.sleep(5)

if __name__ == "__main__":
    hermes = HermesPro(nombre_dispositivo="HaaPp_Terminal_01")
    asyncio.run(hermes.correr_nodo("wss://haappdigitalv-core.onrender.com/ws/canal_kuhul"))
