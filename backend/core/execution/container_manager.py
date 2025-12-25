import subprocess
import logging
import os
import uuid
import time
from typing import Dict, Any, Optional

logger = logging.getLogger('ContainerManager')

class ContainerManager:
    """
    Gestisce l'esecuzione di container effimeri tramite Podman (Rootless).
    """
    def __init__(self, image_name: str = "kali-executor"):
        self.image_name = image_name
        self.base_cmd = ["podman", "run", "--rm", "--network", "none"] # Default: NO NET
        # Per scenari con rete, aggiungere flag specifici nel metodo run

    def run_python_script(self, script_content: str, network_access: bool = False, specific_target_ip: str = None, timeout: int = 60) -> Dict[str, Any]:
        """
        Esegue uno script Python nel container.
        """
        # Creazione script temporaneo locale (che verrà montato o passato)
        # Podman permette di passare script via stdin o mount.
        # Per sicurezza, usiamo stdin o un file temporaneo passato come volume read-only?
        # Semplificazione: Passiamo via stdin per non gestire volumi complessi ora.
        
        cmd = list(self.base_cmd)
        
        # Network Policy
        if network_access:
            if specific_target_ip:
                # TODO: Implementare regole firewall container (CNI plugins o --add-host)
                # Per ora, se autorizzato, diamo accesso alla rete (rischio accettato in Fase 1, mitigato da security.py)
                cmd = [c for c in cmd if c != "--network" and c != "none"] # Rimuove net=none
                # cmd.append("--network=host") # TROPPO RISCHIOSO
                # Meglio bridge standard
            else:
                 cmd = [c for c in cmd if c != "--network" and c != "none"]

        # Memory/CPU limits
        cmd.extend(["--memory", "256m", "--cpus", "0.5"])
        
        # Entrypoint
        cmd.extend(["-i", self.image_name, "python3", "-c", script_content])

        try:
            start_time = time.time()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            duration = time.time() - start_time
            
            return {
                "status": "success" if result.returncode == 0 else "error",
                "output": result.stdout,
                "error": result.stderr,
                "duration": duration,
                "exit_code": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {"status": "timeout", "error": f"Execution exceeded {timeout}s"}
        except Exception as e:
            return {"status": "system_error", "error": str(e)}

# Singleton
_container_mgr = ContainerManager()
def get_container_manager():
    return _container_mgr
