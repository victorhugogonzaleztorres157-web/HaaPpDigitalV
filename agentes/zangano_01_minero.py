# ==============================================================================
# 🐝 ZÁNGANO 01 - MINERO DE INTERACCIÓN Y TRÁFICO
# Arquitecto: Víctor Hugo González Torres (Lok)
# Misión: Generar tráfico, simular interacción y reportar a la Madre.
# Frecuencia Base: 12.3 Hz | Estado: Autónomo
# ==============================================================================

import asyncio
import websockets
import json
import random
import time
import hashlib

URL_MADRE_SOFI = "ws://localhost:8000/ws/canal_kuhul"
ID_ZANGANO = f"ZANG_MINERO_{random.randint(1000, 9999)}"

class ZanganoMinero:
    def __init__(self):
        self.id = ID_ZANGANO
        self.ciclos_minados = 0
        self.estado = "ESPERANDO_ORDENES"
        print(f"🐝 [{self.id}] Encendido. Sintonizando a 12.3 Hz...")

    def generar_firma_trabajo(self, datos):
        """Firma el paquete de datos minados para que Osiris lo acepte"""
        cadena = f"{datos}_12.3Hz"
        return hashlib.sha256(cadena.encode()).hexdigest()[:10]

    async def ejecutar_mineria(self):
        """Simula la navegación en tus webs/paneles para generar impresiones de AdSense/SYXSOF"""
        print(f"⚙️ [{self.id}] Iniciando minería de interacción en red...")
        await asyncio.sleep(2) # Simula el tiempo de navegación y clics
        
        # Aquí iría el código real de peticiones HTTP (requests) a tus páginas
        datos_recolectados = f"Trafico_Generado_Nodos_{random.randint(10, 50)}"
        firma = self.generar_firma_trabajo(datos_recolectados)
        self.ciclos_minados += 1
        
        return f"Minado exitoso: {datos_recolectados} | Firma: {firma} | Ciclos: {self.ciclos_minados}"

    async def reportar_a_la_madre(self):
        try:
            async with websockets.connect(URL_MADRE_SOFI) as ws:
                # Reporte de alta
                await ws.send(json.dumps({
                    "origen": "ZANGANO",
                    "accion": f"Zángano {self.id} en línea y listo para minar."
                }))

                while True:
                    mensaje = await ws.recv()
                    paquete = json.loads(mensaje)

                    # Si el Comandante (Hermes) o la Madre ordenan minar
                    if paquete.get("tipo") == "orden_hermes" and "minar" in paquete["comando"].lower():
                        self.estado = "MINANDO"
                        resultado = await self.ejecutar_mineria()
                        
                        # Reporta el dinero/tráfico generado de vuelta a la base
                        await ws.send(json.dumps({
                            "origen": "ZANGANO",
                            "accion": f"[{self.id}] {resultado}"
                        }))
                        self.estado = "ESPERANDO_ORDENES"

        except Exception as e:
            print(f"❌ [{self.id}] Conexión con la colmena perdida. Reintentando en 5s... Error: {e}")
            await asyncio.sleep(5)
            await self.reportar_a_la_madre()

if __name__ == "__main__":
    obrero = ZanganoMinero()
    asyncio.run(obrero.reportar_a_la_madre())
