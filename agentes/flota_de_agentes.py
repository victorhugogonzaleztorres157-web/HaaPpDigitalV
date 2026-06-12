# ==============================================================================
# 🧬 FLOTA DE AGENTES (OFENSIVA Y DEFENSIVA) - HaaPpDigitalV
# Arquitecto: Víctor Hugo González Torres (Lok)
# Lógica: Inmunidad Activa (Red vs Blue Team)
# ==============================================================================

from base_agente import AgenteMaestro
import random

class AgenteOfensivo(AgenteMaestro):
    """
    EL LADRÓN: Busca vulnerabilidades 24/7.
    Su tarea no es dañar, es informar a la Madre sobre qué puerta está abierta.
    """
    def logica_operativa(self, accion):
        vulnerabilidades = ["SQL_INJECTION_PROBE", "BRUTE_FORCE_PORT_80", "HEADER_OVERFLOW"]
        ataque = random.choice(vulnerabilidades)
        return {"evento": "PROBING", "objetivo": accion, "metodo": ataque, "nivel": "ESTIMULACIÓN_SEGURIDAD"}

class AgenteDefensivo(AgenteMaestro):
    """
    EL POLICÍA: Escucha los ataques, analiza logs y parcha.
    """
    def logica_operativa(self, accion):
        if "ATAQUE_DETECTADO" in accion:
            # Aquí SOFÍ le ordena bloquear IP o cambiar protocolo
            return {"status": "BLINDAJE_REFORZADO", "acción": "FIREWALL_RULE_UPDATED"}
        return {"status": "MONITOREO_ACTIVO"}

# ==================================================
# INICIALIZACIÓN DE LA FLOTA EN EL CORE
# ==================================================
# En tu main.py o en un gestor, disparas estas estancias:
# ladron = AgenteOfensivo("Rojo_01", "OFENSIVA", "wss://...")
# policia = AgenteDefensivo("Azul_01", "DEFENSA", "wss://...")
