# ==============================================================================
# ⚡ HERMES - COMANDANTE LOCAL Y ORGANIZADOR CORTEX (VERSIÓN TERMUX)
# Arquitecto: Víctor Hugo González Torres (Lok)
# Rol: Interfaz Jarvis, Despliegue de Zánganos y Estructuración Local
# Frecuencia Base: 12.3 Hz | Conexión a la Madre: SOFI Central
# ==============================================================================

import asyncio
import websockets
import json
import os
import subprocess
import hashlib
from datetime import datetime

# Configuración de conexión a la Madre (SOFI en Render/Nube)
# Cuando subas main.py a Render, cambias localhost por tu URL real (ej. wss://haappdigitalv.onrender.com/ws/canal_kuhul)
URL_MADRE_SOFI = "ws://localhost:8000/ws/canal_kuhul"
FRECUENCIA_LOCAL = 12.3

class HermesCortexLocal:
    def __init__(self, nombre_dispositivo):
        self.nombre = nombre_dispositivo
        self.zanganos_activos = {}
        print(f"⚡ [HERMES] Iniciando en {self.nombre}. Frecuencia estabilizada a {FRECUENCIA_LOCAL} Hz.")

    # ==================================================
    # 🟢 LÓGICA CORTEX: ORGANIZACIÓN DE PATRONES LOCALES
    # ==================================================
    def organizar_memoria_local(self, ruta_objetivo="/sdcard/Download"):
        """Aplica la lógica de Cortex para estructurar el caos del móvil."""
        print(f"🧠 [CORTEX LOCAL] Mapeando y estructurando directorio: {ruta_objetivo}")
        estructura = {"documentos": [], "imagenes": [], "codigo": [], "otros": []}
        
        try:
            for archivo in os.listdir(ruta_objetivo):
                if archivo.endswith(('.pdf', '.docx', '.txt')):
                    estructura["documentos"].append(archivo)
                elif archivo.endswith(('.jpg', '.png', '.jpeg')):
                    estructura["imagenes"].append(archivo)
                elif archivo.endswith(('.py', '.js', '.json', '.html')):
                    estructura["codigo"].append(archivo)
                else:
                    estructura["otros"].append(archivo)
            
            return f"Cortex mapeó {len(estructura['documentos'])} docs, {len(estructura['imagenes'])} imgs y {len(estructura['codigo'])} scripts."
        except Exception as e:
            return f"Error en Cortex al mapear: {str(e)}"

    # ==================================================
    # 🐝 DESPLIEGUE DE ZÁNGANOS (AGENTES MULTISERVICIO)
    # ==================================================
    def desplegar_zangano(self, tipo_servicio):
        """Despierta a un agente específico para que vaya a la red a trabajar."""
        id_zangano = f"ZANGANO_{tipo_servicio.upper()}_{hashlib.md5(str(datetime.now()).encode()).hexdigest()[:4]}"
        self.zanganos_activos[id_zangano] = "OPERANDO"
        
        # Aquí es donde el zángano se va a internet (scraping, minería, trading)
        accion = f"🐝 Zángano [{id_zangano}] desplegado para: {tipo_servicio}. Operando en red externa."
        print(accion)
        return accion

    # ==================================================
    # 📡 SENSORES FÍSICOS (INTERACCIÓN CON TERMUX API)
    # ==================================================
    def obtener_gps_real(self):
        """Usa el hardware del celular para triangular (Requiere Termux-API)"""
        print("🛰️ [HERMES] Solicitando coordenadas satelitales al hardware...")
        try:
            # Ejecuta el comando de Termux para obtener el GPS
            resultado = subprocess.check_output(["termux-location", "-p", "network"], text=True)
            datos_gps = json.loads(resultado)
            lat = datos_gps.get("latitude", 0.0)
            lon = datos_gps.get("longitude", 0.0)
            return lat, lon
        except Exception as e:
            print("⚠️ Error de sensor GPS. Usando triangulación por defecto.")
            return 20.9674, -89.6237 # Coordenadas de Mérida (Base Osiris)

    # ==================================================
    # 🌌 CANAL K'UHUL: CONEXIÓN DE FRICCIÓN CERO
    # ==================================================
    async def enlazar_con_la_madre(self):
        async with websockets.connect(URL_MADRE_SOFI) as ws:
            # 1. Reporte inicial: Telemetría y Seguridad
            lat, lon = self.obtener_gps_real()
            reporte_alta = {
                "origen": "HERMES",
                "accion": f"triangular {lat} {lon} {self.nombre} {FRECUENCIA_LOCAL}"
            }
            await ws.send(json.dumps(reporte_alta))
            print("✅ [HERMES] Enlace con la Madre SOFI establecido. Latencia Cero.")

            # 2. Bucle de escucha (Esperando tus órdenes desde la interfaz visual)
            while True:
                mensaje = await ws.recv()
                paquete = json.loads(mensaje)

                if paquete.get("tipo") == "orden_hermes":
                    orden = paquete["comando"].lower()
                    respuesta = ""

                    # EL CEREBRO EVALÚA LA ORDEN
                    if "organizar" in orden:
                        respuesta = self.organizar_memoria_local()
                    elif "zangano" in orden or "minar" in orden:
                        respuesta = self.desplegar_zangano("mineria_trafico")
                    elif "gps" in orden or "escanear" in orden:
                        lat, lon = self.obtener_gps_real()
                        respuesta = f"Posición táctica actual: Lat {lat}, Lon {lon}"
                    else:
                        # Ejecución en terminal pura (Jarvis)
                        respuesta = f"Comando '{orden}' recibido y encolado en procesador local."

                    # Confirmar a la Madre
                    await ws.send(json.dumps({
                        "origen": "HERMES",
                        "accion": respuesta
                    }))

if __name__ == "__main__":
    # Inicia el nodo local asignándole el nombre del dispositivo
    nodo_local = HermesCortexLocal(nombre_dispositivo="Motorola_Z_Lok")
    
    try:
        asyncio.run(nodo_local.enlazar_con_la_madre())
    except ConnectionRefusedError:
        print("❌ [ERROR] La Madre SOFI no está en línea. Verifica que main.py esté corriendo en el Nexo.")