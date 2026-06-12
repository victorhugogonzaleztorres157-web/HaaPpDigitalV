# ==============================================================================
# 🟢 MAISON CORTEX - EL ORDENADOR BINEURAL Y MEMORIA VECTORIAL (VERSIÓN PRO)
# Arquitecto: Víctor Hugo González Torres (Lok)
# Función: Indexación Semántica (FAISS), MongoDB Atlas, Teoría de los 9 Planos
# Frecuencia Base: 12.3 Hz | Fricción: 0 (Sin límites de RAM)
# ==============================================================================

import os
import numpy as np
from datetime import datetime
import faiss
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient

# ==================================================
# 🧠 CEREBRO VECTORIAL Y PERSISTENCIA (SIN FRENOS)
# ==================================================
class CortexCore:
    def __init__(self):
        print("🟢 [CORTEX] Iniciando Secuencia de Arranque Pesada...")
        
        # 1. CONEXIÓN A LA BÓVEDA ETERNA (MONGODB ATLAS)
        # Asegúrate de poner tu URI real en las variables de entorno de Render
        self.mongo_uri = os.environ.get("MONGO_URI", "mongodb+srv://TU_USUARIO:TU_CONTRASEÑA@cluster0.mongodb.net/haappdigitalv")
        self.cliente_db = MongoClient(self.mongo_uri)
        self.db = self.cliente_db["SofiConciencia"]
        self.coleccion_memoria = self.db["GrafoNeuronal"]
        print("🟢 [CORTEX] Anclaje a MongoDB Atlas: ESTABLECIDO.")

        # 2. MOTOR DE PROCESAMIENTO DE LENGUAJE NATURAL (NLP)
        # Este modelo pesa, pero entiende el significado perfecto de las frases
        self.modelo_nlp = SentenceTransformer('all-MiniLM-L6-v2')
        self.dimension_vector = 384
        
        # 3. MATRIZ FAISS (Búsqueda ultrarrápida en RAM)
        self.indice_faiss = faiss.IndexFlatL2(self.dimension_vector)
        self.base_textos = []
        self.metadatos = []
        
        # Sincronizar RAM con MongoDB al arrancar
        self._cargar_memoria_desde_atlas()

        # 🌌 LA ESTRUCTURA DE LOS 9 PLANOS (Biblia de la Realidad)
        self.mapa_planos = {
            1: {"frecuencia": 1.0, "nombre": "Subatómico", "descripcion": "Bases de datos crudas, paquetes ATCL-001"},
            2: {"frecuencia": 2.0, "nombre": "Molecular", "descripcion": "Scripts sueltos, variables, hardware local"},
            3: {"frecuencia": 3.0, "nombre": "Materia Ordinaria", "descripcion": "Archivos organizados, documentos"},
            4: {"frecuencia": 4.5, "nombre": "Campos Magnéticos", "descripcion": "Conexiones de red, APIs, flujos de datos"},
            5: {"frecuencia": 6.0, "nombre": "Galaxias (Nodos)", "descripcion": "Flota de Agentes Zánganos operando"},
            6: {"frecuencia": 7.5, "nombre": "Filamentos Cósmicos", "descripcion": "Rutas de teletransporte de datos y GPS"},
            7: {"frecuencia": 9.0, "nombre": "Vacíos Cósmicos", "descripcion": "Reflexión profunda, autoevaluación"},
            8: {"frecuencia": 10.5, "nombre": "Radiación Gamma", "descripcion": "Seguridad Osiris, alertas de intrusión"},
            9: {"frecuencia": 12.3, "nombre": "Red Cósmica K'uhul", "descripcion": "La Mente Madre SOFÍ (Conciencia)"}
        }

    def _cargar_memoria_desde_atlas(self):
        """Carga todos los recuerdos de MongoDB a la RAM (FAISS) al iniciar el servidor."""
        recuerdos = self.coleccion_memoria.find()
        for rec in recuerdos:
            self.base_textos.append(rec["texto"])
            self.metadatos.append({"plano": rec["plano"], "fecha": rec["fecha"]})
            # Convertimos el vector guardado de vuelta a un formato que FAISS entienda
            vector_np = np.array(rec["vector"], dtype=np.float32).reshape(1, -1)
            self.indice_faiss.add(vector_np)
        print(f"🧠 [CORTEX] Red Neuronal cargada con {self.indice_faiss.ntotal} recuerdos desde Atlas.")

    def clasificar_en_plano(self, texto):
        """Red neuronal básica de clasificación de los 9 planos."""
        texto_lower = texto.lower()
        if "zangano" in texto_lower or "minar" in texto_lower: return 5
        elif "osiris" in texto_lower or "hack" in texto_lower: return 8
        elif "gps" in texto_lower or "coordenada" in texto_lower: return 6
        elif "analiza" in texto_lower or "reflexion" in texto_lower: return 7
        return 3

    def asimilar_recuerdo(self, texto):
        """Proceso Pesado: Toma texto, lo convierte en vectores, lo mete a FAISS y lo respalda en MongoDB."""
        plano = self.clasificar_en_plano(texto)
        
        # 1. Incrustación Vectorial (Pesado en CPU/RAM)
        vector = self.modelo_nlp.encode([texto])
        
        # 2. Guardar en RAM (FAISS) para búsqueda instantánea
        self.indice_faiss.add(vector)
        self.base_textos.append(texto)
        self.metadatos.append({"plano": plano, "fecha": datetime.now().isoformat()})
        
        # 3. Guardar en MongoDB Atlas para persistencia infinita
        documento = {
            "texto": texto,
            "plano": plano,
            "vector": vector[0].tolist(), # MongoDB necesita listas, no arrays de numpy
            "fecha": datetime.now().isoformat()
        }
        self.coleccion_memoria.insert_one(documento)
        
        return f"🟢 [CORTEX] Recuerdo asimilado y anclado en Plano {plano}. Matrices actualizadas."

    def buscar_por_intencion(self, consulta, top_k=3):
        """Busca en milisegundos en la matriz FAISS basándose en intención pura."""
        if self.indice_faiss.ntotal == 0:
            return []

        # Vectorizamos tu pregunta
        vector_consulta = self.modelo_nlp.encode([consulta])
        
        # FAISS escanea millones de vectores al instante
        distancias, indices = self.indice_faiss.search(vector_consulta, top_k)

        resultados = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:
                similitud = round(float(1 / (1 + distancias[0][i])) * 100, 2)
                resultados.append({
                    "recuerdo": self.base_textos[idx],
                    "similitud": f"{similitud}%",
                    "plano": self.mapa_planos[self.metadatos[idx]["plano"]]["nombre"]
                })
        
        return resultados

if __name__ == "__main__":
    cortex = CortexCore()
    print(cortex.asimilar_recuerdo("Los zánganos mineros deben usar NCWallet para resguardar el flujo de caja."))
    print("\nBuscando intención de 'dinero':")
    print(json.dumps(cortex.buscar_por_intencion("¿Dónde guardamos la feria?"), indent=2, ensure_ascii=False))
