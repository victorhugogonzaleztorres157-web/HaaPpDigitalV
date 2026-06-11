class RedAgentes:
    def __init__(self, cortex, osiris):
        self.agentes = {}
    
    def registrar_agente(self, nombre, especialidad):
        self.agentes[nombre] = especialidad
        return f"Agente {nombre} listo."