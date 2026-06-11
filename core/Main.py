# ==================================================
# 🚀 SOFI - GARVIS | NÚCLEO PRINCIPAL
# Archivo: core/Main.py
# Frecuencia base: 12.3 Hz | Integración completa
# ==================================================

import sys
import os

# Agregar ruta para importar módulos correctamente
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar todos los componentes del sistema
from cortex import CortexOrganizado
from telegeo import TeleGeoAvanzado
from osiris import OsirisBlindaje
from agentes import RedAgentes
from flask import Flask

# --------------------------
# ⚙️ CONFIGURACIÓN GLOBAL
# --------------------------
VERSION = "1.0.0"
FRECUENCIA_OFICIAL = 12.3
NOMBRE_SISTEMA = "SOFI - GARVIS"

# --------------------------
# 🧠 INICIALIZACIÓN DEL NÚCLEO
# --------------------------
class NucleoPrincipal:
    def __init__(self):
        print(f"🔄 Iniciando {NOMBRE_SISTEMA} v{VERSION}...")
        print(f"📡 Frecuencia de operación: {FRECUENCIA_OFICIAL} Hz")

        # Cargar cada módulo en orden seguro
        self.osiris = OsirisBlindaje()          # 1° Seguridad primero
        self.cortex = CortexOrganizado()        # 2° Memoria y organización
        self.geo = TeleGeoAvanzado()            # 3° Geolocalización
        self.agentes = RedAgentes(self.cortex, self.osiris)  # 4° Red inteligente

        # Aplicar marca de coherencia al sistema
        self._aplicar_frecuencia_base()

        print("✅ Sistema unificado e inicializado correctamente")

    def _aplicar_frecuencia_base(self):
        """Sella el sistema con su identidad exclusiva"""
        firma = self.osiris.generar_sello({
            "sistema": NOMBRE_SISTEMA,
            "version": VERSION,
            "frecuencia": FRECUENCIA_OFICIAL
        })
        self.cortex.guardar(
            categoria="nucleo",
            contenido={
                "estado": "activo",
                "frecuencia": FRECUENCIA_OFICIAL,
                "firma": firma
            },
            nombre="Identidad_Sistema"
        )

    def estado_general(self):
        """Devuelve el resumen completo del sistema"""
        return {
            "sistema": NOMBRE_SISTEMA,
            "version": VERSION,
            "frecuencia": FRECUENCIA_OFICIAL,
            "cortex": "✅ Operativo",
            "geolocalizacion": "✅ Activo",
            "seguridad": "✅ Blindada",
            "agentes": f"🤝 {len(self.agentes.agentes)} conectados"
        }

# --------------------------
# 🌐 SERVIDOR PRINCIPAL
# --------------------------
app = Flask(__name__)
nucleo = NucleoPrincipal()

# Importar rutas de interfaz
from app import INTERFAZ_JARVIS

@app.route('/')
def panel_principal():
    """Carga la interfaz visual estilo Jarvis"""
    return INTERFAZ_JARVIS

@app.route('/api/estado')
def ver_estado():
    """Devuelve estado completo del núcleo"""
    from flask import jsonify
    return jsonify(nucleo.estado_general())

@app.route('/api/ejecutar', methods=['POST'])
def procesar_comando():
    """Recibe y valida órdenes"""
    from flask import request, jsonify
    datos = request.get_json() or {}

    # Verificación obligatoria de frecuencia
    if not nucleo.osiris.verificar_frecuencia(datos.get("frecuencia", 0)):
        return jsonify({
            "estado": "denegado",
            "mensaje": "Frecuencia no autorizada - Acceso rechazado"
        }), 403

    # Procesar orden
    resultado = nucleo.cortex.guardar(
        categoria="operativo",
        contenido=datos.get("comando", ""),
        nombre="Orden_Recibida"
    )

    return jsonify({
        "estado": "ejecutado",
        "mensaje": "Comando procesado correctamente",
        "id_registro": resultado["id"]
    })

# --------------------------
# ▶️ EJECUCIÓN FINAL
# --------------------------
if __name__ == "__main__":
    print(f"🚀 {NOMBRE_SISTEMA} corriendo en: http://0.0.0.0:10000")
    app.run(host="0.0.0.0", port=10000, debug=False)
