import hashlib
from datetime import datetime

class CortexOrganizado:
    def __init__(self):
        self.estructura = {"operativo": {"datos": {}}}
    
    def guardar(self, categoria, contenido):
        reg = {"id": hashlib.sha256(str(contenido).encode()).hexdigest()[:12], "contenido": contenido}
        self.estructura[categoria]["datos"][reg["id"]] = reg
        return reg