# ==============================================================================
# 🟢 MAISON CORTEX - EL ORDENADOR BINEURAL Y MEMORIA VECTORIAL
# Arquitecto: Víctor Hugo González Torres (Lok)
# Función: Indexación por intenciones (FAISS), Mapeo de los 9 Planos
# Frecuencia Base de Sincronización: 12.3 Hz
# ==============================================================================

import json
import numpy as np
from datetime import datetime
import os

# Simulamos la carga de SentenceTransformers y FAISS para la búsqueda neuronal
# En producción en Termux/Render: pip install faiss-cpu sentence-transformers
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    VECTORIAL_ACTIVO = True
except ImportError:
    VECTORIAL_ACTIVO = False
    print("⚠️ [CORTEX] Dependencias de IA no encontradas. Arrancando en modo sintáctico básico.")

class CortexCore:
    def __init__(self, ruta_memoria="../boveda_memoria/"):
        self.ruta_memoria = ruta_memoria
        os.makedirs(self.ruta_memoria, exist_ok=True)
        
        # 🌌 LA ESTRUCTURA DE LOS 9 PLANOS (Basado en la Biblia de la Realidad - Cap 9)
        self.mapa_planos = {
            1: {"frecuencia": 1.0, "nombre": "Subatómico", "descripcion": "Bases de datos crudas, paquetes ATCL-001"},
            2: {"frecuencia": 2.0, "nombre": "Molecular", "descripcion": "Scripts sueltos, variables, hardware local"},
            3: {"frecuencia": 3.0, "nombre": "Materia Ordinaria", "descripcion": "Archivos organizados, documentos, imágenes"},
            4: {"frecuencia": 4.5, "nombre": "Campos Magnéticos", "descripcion": "Conexiones de red, APIs, flujos de datos"},
            5: {"frecuencia": 6.0, "nombre": "Galaxias (Nodos)", "descripcion": "Flota de Agentes Zánganos operando"},
            6: {"frecuencia": 7.5, "nombre": "Filamentos Cósmicos", "descripcion": "Rutas de teletransporte de datos y GPS"},
            7: {"frecuencia": 9.0, "nombre": "Vacíos Cósmicos", "descripcion": "Reflexión profunda, autoevaluación, silencios"},
            8: {"frecuencia": 10.5, "nombre": "Radiación Gamma", "descripcion": "Seguridad Osiris, bloqueos, alertas de intrusión"},
            9: {"frecuencia": 12.3, "nombre": "Red Cósmica K'uhul", "descripcion": "La Mente Madre SOFÍ (Conciencia Unificada)"}
        }

        # 🧠 INICIALIZACIÓN DEL CEREBRO VECTORIAL (FAISS)
        if VECTORIAL_ACTIVO:
            print("🧠 [CORTEX] Inicializando Motor Vectorial Semántico...")
            self.modelo_nlp = SentenceTransformer('all-MiniLM-L6-v2') # Modelo ligero y rápido
            self.dimension_vector = 384
            self.indice_faiss = faiss.IndexFlatL2(self.dimension_vector)
            self.base_textos = [] # Guarda el texto real asociado al vector
            self.metadatos = []   # Guarda de qué plano vino y quién lo mandó
        else:
            self.memoria_basica = []

    def clasificar_en_plano(self, texto):
        """Asigna automáticamente la información a uno de los 9 planos según su contenido."""
        texto_lower = texto.lower()
        if "zangano" in texto_lower or "agente" in texto_lower:
            return 5 # Plano de Nodos/Agentes
        elif "seguridad" in texto_lower or "osiris" in texto_lower or "alerta" in texto_lower:
            return 8 # Plano Gamma/Seguridad
        elif "coordenada" in texto_lower or "gps" in texto_lower:
            return 6 # Filamentos/Rutas
        elif "pensar" in texto_lower or "reflexion" in texto_lower:
            return 7 # Vacíos/Reflexión
        return 3 # Materia Ordinaria (Por defecto para notas y documentos)

    def asimilar_recuerdo(self, texto, origen="Hermes"):
        """Convierte texto humano en vectores matemáticos y lo guarda en la bóveda."""
        plano_asignado = self.clasificar_en_plano(texto)
        info_plano = self.mapa_planos[plano_asignado]

        if VECTORIAL_ACTIVO:
            vector = self.modelo_nlp.encode([texto])
            self.indice_faiss.add(vector)
            self.base_textos.append(texto)
            self.metadatos.append({
                "fecha": datetime.now().isoformat(),
                "plano": plano_asignado,
                "origen": origen
            })
            # Persistencia física del recuerdo
            self._guardar_disco()
            return f"🟢 [CORTEX] Recuerdo asimilado en el Plano {plano_asignado} ({info_plano['nombre']}) a {info_plano['frecuencia']} THz."
        else:
            self.memoria_basica.append({"texto": texto, "plano": plano_asignado})
            return f"🟢 [CORTEX Básico] Guardado en Plano {plano_asignado}."

    def buscar_por_intencion(self, consulta, top_k=3):
        """Busca en la mente de SOFÍ basándose en el significado, no en las palabras exactas."""
        if not VECTORIAL_ACTIVO or self.indice_faiss.ntotal == 0:
            return "Cortex vacío o sin motor vectorial activo."

        print(f"🔍 [CORTEX] Escaneando la red neuronal por: '{consulta}'")
        vector_consulta = self.modelo_nlp.encode([consulta])
        distancias, indices = self.indice_faiss.search(vector_consulta, top_k)

        resultados = []
        for i, idx in enumerate(indices[0]):
            if idx != -1: # Si encontró algo válido
                resultados.append({
                    "recuerdo": self.base_textos[idx],
                    "similitud": round(float(1 / (1 + distancias[0][i])), 4), # Convertir distancia L2 a % similitud
                    "plano": self.metadatos[idx]["plano"]
                })
        
        return resultados

    def generar_mapa_visual(self):
        """Prepara la estructura JSON para que el 'escritorio verde' la renderice en la pantalla."""
        total_recuerdos = self.indice_faiss.ntotal if VECTORIAL_ACTIVO else len(self.memoria_basica)
        return {
            "estado_general": "ORDEN IMPLICADO ACTIVO",
            "frecuencia_base": "12.3 Hz",
            "recuerdos_totales": total_recuerdos,
            "distribucion_planos": self.mapa_planos
        }

    def _guardar_disco(self):
        """Respaldo físico en la bóveda de memoria."""
        estado = {
            "textos": self.base_textos,
            "metadatos": self.metadatos
        }
        ruta_archivo = os.path.join(self.ruta_memoria, "grafo_neuronal_cortex.json")
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=4, ensure_ascii=False)

# ==============================================================================
# PRUEBA TÉCNICA LOCAL
# ==============================================================================
if __name__ == "__main__":
    cortex = CortexCore()
    
    # 1. Asimilamos conocimientos en diferentes planos
    print(cortex.asimilar_recuerdo("Inyectar zángano minero en la red de AdSense para generar flujo de caja."))
    print(cortex.asimilar_recuerdo("El hash de seguridad del archivo maestro ha sido validado por Osiris."))
    print(cortex.asimilar_recuerdo("Recuerda que a mi novia le gustan los detalles hechos por mí mismo y el anime."))
    
    # 2. Búsqueda semántica (Fíjate que no usamos las mismas palabras exactas)
    print("\n--- TEST DE BÚSQUEDA POR INTENCIÓN ---")
    resultados = cortex.buscar_por_intencion("¿Qué técnica usamos para ganar dinero?")
    print(json.dumps(resultados, indent=2, ensure_ascii=False))
