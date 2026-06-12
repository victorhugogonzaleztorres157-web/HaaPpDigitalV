# ==============================================================================
# 🐝 NÚCLEO DE AGENTES SOFÍ (HaaPpDigitalV)
# Arquitecto: Víctor Hugo González Torres (Lok)
# Misión: Operación Autónoma Sincronizada con la Madre
# ==============================================================================

import asyncio
import json
import websockets
import hashlib
from datetime import datetime

class AgenteMaestro:
    def __init__(self, nombre, rol, url_madre):
        self.nombre = nombre
        self.rol = rol
        self.url_madre = url_madre
        self.estado = "INACTIVO"
        self.firma_base = "_12.3Hz_Kuhul"
        print(f"🧬 [AGENTE {self.nombre}] Instanciado en modo {self.rol}.")

    def generar_sello_forense(self, data):
        """Osiris: Firma cada movimiento del agente."""
        blob = json.dumps(data, sort_keys=True) + self.firma_base
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    async def conectar_a_la_colmena(self):
        """Conexión persistente al bus de la Madre."""
        while True:
            try:
                async with websockets.connect(self.url_madre) as ws:
                    print(f"🔗 [AGENTE {self.nombre}] Canal abierto.")
                    await ws.send(json.dumps({"tipo": "handshake", "agente": self.nombre}))
                    
                    while True:
                        mensaje = await ws.recv()
                        paquete = json.loads(mensaje)
                        
                        # Si la Madre (SOFÍ) da una orden, el agente la ejecuta
                        if paquete.get("rol_destino") == self.rol:
                            accion = paquete.get("accion")
                            print(f"⚙️ [AGENTE {self.nombre}] Ejecutando: {accion}")
                            
                            resultado = self.logica_operativa(accion)
                            
                            # Respuesta firmada
                            respuesta = {
                                "origen": self.nombre,
                                "payload": resultado,
                                "osiris_sello": self.generar_sello_forense(resultado)
                            }
                            await ws.send(json.dumps(respuesta))
            except Exception as e:
                print(f"⚠️ [AGENTE {self.nombre}] Fricción en red: {e}. Reconectando...")
                await asyncio.sleep(5)

    def logica_operativa(self, accion):
        """A ser implementada por cada agente específico."""
        raise NotImplementedError("Los agentes deben definir su lógica operativa.")
