# ==============================================================================
# ⚡ HERMES - EL BRAZO EJECUTOR Y COMANDANTE LOCAL (VERSIÓN TERMUX)
# Arquitecto: Víctor Hugo González Torres (Lok)
# Función: Toma de control del hardware del celular, sensores y ejecución local.
# Frecuencia Base: 12.3 Hz | Conexión: Mente Madre (WebSocket)
# ==============================================================================

import asyncio
import websockets
import json
import subprocess
import os

# Conexión directa al Nexo Central (Cambiar por tu URL de Render en producción)
URL_MADRE_SOFI = "ws://localhost:8000/ws/canal_kuhul"
FRECUENCIA_LOCAL = 12.3

class HermesHardware:
    def __init__(self, nombre_dispositivo):
        self.nombre = nombre_dispositivo
        print(f"⚡ [HERMES] Sistema en línea. Tomando control del hardware en: {self.nombre}")

    # ==================================================
    # 📱 CONTROL FÍSICO DEL CELULAR (TERMUX-API)
    # ==================================================
    def ejecutar_termux(self, comando_lista):
        """Ejecuta comandos nativos de Termux y devuelve el resultado."""
        try:
            resultado = subprocess.check_output(comando_lista, text=True)
            return resultado.strip()
        except Exception as e:
            return f"Error de hardware: {str(e)}"

    def estado_bateria(self):
        """Lee el porcentaje y estado de la batería del celular."""
        datos = self.ejecutar_termux(["termux-battery-status"])
        try:
            bat = json.loads(datos)
            return f"Batería: {bat.get('percentage', 0)}% | Conectado: {bat.get('plugged', 'UNPLUGGED')}"
        except:
            return "No se pudo leer la batería."

    def tomar_fotografia_silenciosa(self):
        """Usa la cámara del teléfono sin abrir la aplicación (Modo Espía/Seguridad)."""
        ruta_foto = f"/sdcard/Download/captura_hermes_{int(asyncio.get_event_loop().time())}.jpg"
        self.ejecutar_termux(["termux-camera-photo", "-c", "0", ruta_foto])
        return f"📸 Fotografía tomada y guardada en: {ruta_foto}"

    def alerta_vibracion(self):
        """Hace vibrar el teléfono (Notificación física de orden recibida)."""
        self.ejecutar_termux(["termux-vibrate", "-d", "500"])
        return "📱 Vibración ejecutada."

    # ==================================================
    # 🟢 CORTEX LOCAL: ORGANIZACIÓN DE ARCHIVOS
    # ==================================================
    def organizar_memoria_interna(self, ruta_objetivo="/sdcard/Download"):
        """Cortex toma el control de los archivos del teléfono y los clasifica."""
        try:
            archivos = os.listdir(ruta_objetivo)
            documentos = [f for f in archivos if f.endswith(('.pdf', '.docx', '.txt'))]
            imagenes = [f for f in archivos if f.endswith(('.jpg', '.png', '.jpeg'))]
            
            return f"Cortex mapeó localmente: {len(documentos)} Documentos y {len(imagenes)} Imágenes en {ruta_objetivo}."
        except Exception as e:
            return f"Fallo al leer memoria local: {str(e)}"

    # ==================================================
    # 🌌 CANAL K'UHUL (ENLACE CON LA MENTE MADRE Y EL HTML)
    # ==================================================
    async def escuchar_ordenes_del_arquitecto(self):
        """Bucle de Fricción Cero que espera comandos desde tu Interfaz HTML."""
        print(f"📡 [HERMES] Sintonizando canal cuántico a {FRECUENCIA_LOCAL} Hz...")
        
        try:
            async with websockets.connect(URL_MADRE_SOFI) as ws:
                # Reporte de alta al conectarse
                await ws.send(json.dumps({
                    "origen": "HERMES",
                    "accion": f"Dispositivo {self.nombre} anclado a la Mente Madre. Control de hardware activo."
                }))

                while True:
                    mensaje = await ws.recv()
                    paquete = json.loads(mensaje)

                    # Si el comando viene de SOFÍ Blanca o directo de tu Interfaz HTML
                    if paquete.get("tipo") == "orden_hermes":
                        comando = paquete["comando"].lower()
                        respuesta_hardware = ""

                        print(f"⚙️ [ORDEN RECIBIDA]: {comando}")

                        # LÓGICA DE EJECUCIÓN
                        if "bateria" in comando or "estado" in comando:
                            respuesta_hardware = self.estado_bateria()
                        elif "foto" in comando or "camara" in comando:
                            respuesta_hardware = self.tomar_fotografia_silenciosa()
                        elif "vibrar" in comando or "alerta" in comando:
                            respuesta_hardware = self.alerta_vibracion()
                        elif "organizar" in comando or "cortex" in comando:
                            respuesta_hardware = self.organizar_memoria_interna()
                        else:
                            # Comando genérico en terminal
                            respuesta_hardware = f"Comando '{comando}' encolado en procesador local."

                        # Hermes le reporta a la Mente Madre (y esta lo manda a tu HTML)
                        await ws.send(json.dumps({
                            "origen": "HERMES",
                            "accion": respuesta_hardware
                        }))

        except Exception as e:
            print(f"❌ [ERROR] Desconexión de la Mente Madre. Motivo: {e}")
            print("🔄 Reintentando sintonización en 5 segundos...")
            await asyncio.sleep(5)
            await self.escuchar_ordenes_del_arquitecto()

if __name__ == "__main__":
    # Nombra al dispositivo para identificarlo en la red
    comandante = HermesHardware(nombre_dispositivo="Terminal_Movil_Lok")
    asyncio.run(comandante.escuchar_ordenes_del_arquitecto())
