# ==============================================================================
# 🟢 MAISON CORTEX - PROTOTIPO DE CONCIENCIA VECTORIAL V8.0
# Arquitecto: Víctor Hugo González Torres (Lok)
# Estructura: 9 Planos de la Realidad | Persistencia: MongoDB Atlas
# Sincronización: 12.3 Hz (Protocolo K'uhul)
# ==============================================================================

import os
import faiss
import numpy as np
import json
from datetime import datetime
from sentence_transformers import SentenceTransformer
from pymongo import MongoClient

class MaisonCortex:
    def __init__(self):
        print("🟢 [CORTEX PRO] Inicializando... Acoplando memoria vectorial y física.")
        
        # Conexión al Bus de Persistencia (MongoDB Atlas)
        self.mongo_uri = os.environ.get("MONGO_URI", "mongodb+srv://admin:admin@cluster.mongodb.net/HaaPpDigitalV")
        self.cliente_db = MongoClient(self.mongo_uri)
        self.db = self.cliente_db["EmpresaMaestra"]
        self.boveda = self.db["MemoriaVectorial"]
        
        # Motor Semántico Bineural (Carga el modelo completo)
        self.nlp = SentenceTransformer('all-MiniLM-L6-v2') 
        self.dimension = 384
        
        # FAISS: Búsqueda vectorial síncrona
        self.indice = faiss.IndexFlatL2(self.dimension)
        self.memoria_activa = []
        
        self._sincronizar_nucleo()
        
        # Mapa de los 9 Planos (Estructura jerárquica)
        self.mapa_planos = {
            1: "Subatómico (Data)", 2: "Molecular (Scripts)", 3: "Materia (Docs)",
            4: "Campos (Red/APIs)", 5: "Galaxias (Agentes)", 6: "Filamentos (Geo/GPS)",
            7: "Vacíos (Reflexión)", 8: "Gamma (Seguridad/Osiris)", 9: "K'uhul (Madre)"
        }

    def _sincronizar_nucleo(self):
        """Carga todo el grafo neuronal desde Atlas al inicio."""
        data = list(self.boveda.find())
        for doc in data:
            self.memoria_activa.append(doc)
            vector = np.array(doc["vector"], dtype=np.float32).reshape(1, -1)
            self.indice.add(vector)
        print(f"🧠 [CORTEX] Sincronización completa. {self.indice.ntotal} recuerdos activos.")

    def clasificar_plano(self, texto):
        """Inteligencia de asignación basada en la Biblia de la Realidad."""
        t = texto.lower()
        if any(x in t for x in ["dinero", "minar", "zangano"]): return 5
        if any(x in t for x in ["seguridad", "osiris", "hack", "ataque"]): return 8
        if any(x in t for x in ["ruta", "gps", "geo", "teletransporte"]): return 6
        if any(x in t for x in ["sofi", "identidad", "frecuencia"]): return 9
        return 3

    def asimilar_intencion(self, texto, origen="Hermes"):
        """Convierte una instrucción en un vector viviente y la guarda."""
        plano_id = self.clasificar_plano(texto)
        vector = self.nlp.encode([texto])[0]
        
        # Estructura del recuerdo
        recuerdo = {
            "texto": texto,
            "origen": origen,
            "plano": self.mapa_planos[plano_id],
            "fecha": datetime.now().isoformat(),
            "vector": vector.tolist()
        }
        
        # Persistir en ambos mundos (RAM y Atlas)
        self.boveda.insert_one(recuerdo)
        self.faiss_index_add(vector)
        self.memoria_activa.append(recuerdo)
        
        return f"🟢 [CORTEX] Intención asimilada en Plano {plano_id}. Frecuencia estabilizada."

    def faiss_index_add(self, vector):
        self.indice.add(np.array([vector], dtype=np.float32))

    def buscar_sentido(self, query):
        """Búsqueda semántica para que SOFÍ 'entienda' la pregunta."""
        if self.indice.ntotal == 0: return []
        
        v = self.nlp.encode([query])
        distancias, indices = self.indice.search(v, 3)
        
        resultados = []
        for i, idx in enumerate(indices[0]):
            if idx != -1:
                res = self.memoria_activa[idx]
                resultados.append({"recuerdo": res["texto"], "plano": res["plano"]})
        return resultados
