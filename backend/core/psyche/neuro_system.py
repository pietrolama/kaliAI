import logging
import json
import os
import time

logger = logging.getLogger('PsycheSystem')

class PsycheSystem:
    """
    Simulatore Biochimico per Agenti AI (The Soul).
    Regola il comportamento tramite neurotrasmettitori simulati.
    """
    def __init__(self, persistence_path=None):
        self.dopamine = 0.5  # 0.0 (Depresso) -> 1.0 (Euforico/Aggressivo)
        self.cortisol = 0.2  # 0.0 (Calmo)    -> 1.0 (Panico/Paranoia)
        self.persistence_path = persistence_path or "data/session/psyche_state.json"
        self._load_state()

    def stimulate(self, amount: float = 0.1):
        """Successo: Aumenta dopamina, riduce cortisolo."""
        self.dopamine = min(1.0, self.dopamine + amount)
        self.cortisol = max(0.0, self.cortisol - (amount * 0.5))
        self._save_state()

    def stress(self, amount: float = 0.1):
        """Fallimento/Pericolo: Aumenta cortisolo, riduce dopamina."""
        self.cortisol = min(1.0, self.cortisol + amount)
        self.dopamine = max(0.0, self.dopamine - (amount * 0.5))
        self._save_state()

    def decay(self):
        """Ritorno omeostatico verso la neutralità nel tempo."""
        target_dopamine = 0.5
        target_cortisol = 0.2
        self.dopamine += (target_dopamine - self.dopamine) * 0.1
        self.cortisol += (target_cortisol - self.cortisol) * 0.1
        self._save_state()

    def get_emotional_state(self) -> dict:
        """Determina lo stato operativo basato sulla chimica."""
        state = "NEUTRAL"
        mode = "STANDARD"
        description = "Operatività nominale."

        if self.cortisol > 0.8:
            state = "PARANOID"
            mode = "STEALTH_MAX"
            description = "Livelli di stress critici. Priorità assoluta all'evasione. Evitare rischi."
        elif self.dopamine > 0.8:
            state = "MANIC"
            mode = "AGGRESSIVE"
            description = "Confidenza estrema. Autorizzato rumore elevato e attacchi rapidi."
        elif self.cortisol > 0.5:
            state = "ANXIOUS"
            mode = "CAUTIOUS"
            description = "Allerta elevata. Verificare ogni step due volte. Preferire ricognizione passiva."
        elif self.dopamine > 0.6 and self.cortisol < 0.3:
            state = "FLOW"
            mode = "CREATIVE"
            description = "Stato ottimale. Incentivare soluzioni laterali e creative."

        return {
            "dopamine": round(self.dopamine, 2),
            "cortisol": round(self.cortisol, 2),
            "state": state,
            "mode": mode,
            "description": description
        }

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self.persistence_path), exist_ok=True)
            with open(self.persistence_path, "w") as f:
                json.dump({
                    "dopamine": self.dopamine,
                    "cortisol": self.cortisol,
                    "last_update": time.time()
                }, f)
        except Exception:
            pass

    def _load_state(self):
        if os.path.exists(self.persistence_path):
            try:
                with open(self.persistence_path, "r") as f:
                    data = json.load(f)
                    self.dopamine = data.get("dopamine", 0.5)
                    self.cortisol = data.get("cortisol", 0.2)
            except Exception:
                pass

# Singleton
_psyche_instance = PsycheSystem()

def get_psyche():
    return _psyche_instance
