#!/usr/bin/env python3
"""
Container Sandbox - Esecuzione isolata in container Podman
🐳 I comandi pericolosi girano in container effimeri, non sull'host.

Funzionalità:
- Esecuzione bash in container usa-e-getta
- Esecuzione Python scripts in sandbox
- Network isolation configurabile
- Shared volume per output
"""

import os
import subprocess
import tempfile
import logging
import uuid
from typing import Optional, Tuple

logger = logging.getLogger('ContainerSandbox')

# ============================================================================
# CONFIGURATION
# ============================================================================

# Immagine default per sandbox
DEFAULT_IMAGE = "kalilinux/kali-rolling:latest"
FALLBACK_IMAGE = "alpine:latest"

# Directory condivisa per output/script
SHARED_DIR = "/tmp/kali_sandbox"
os.makedirs(SHARED_DIR, exist_ok=True)

# Limiti risorse container
CONTAINER_LIMITS = {
    "memory": "512m",
    "cpus": "1.0",
    "timeout": 120,
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _get_container_runtime() -> str:
    """
    Determina se usare podman o docker.
    Preferisce podman (rootless).
    """
    # Check podman
    try:
        result = subprocess.run(
            ["podman", "--version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return "podman"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    # Fallback a docker
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            return "docker"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    
    logger.error("[ContainerSandbox] Neither podman nor docker found!")
    return None

def _check_image_exists(runtime: str, image: str) -> bool:
    """Verifica se l'immagine esiste localmente."""
    try:
        result = subprocess.run(
            [runtime, "image", "exists", image],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except:
        return False

def _pull_image(runtime: str, image: str) -> bool:
    """Scarica l'immagine se non presente."""
    logger.info(f"[ContainerSandbox] Pulling image: {image}")
    try:
        result = subprocess.run(
            [runtime, "pull", image],
            capture_output=True,
            text=True,
            timeout=300  # 5 minuti per il pull
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"[ContainerSandbox] Pull failed: {e}")
        return False

# ============================================================================
# MAIN FUNCTIONS
# ============================================================================

def run_command_in_sandbox(
    command: str,
    image: str = None,
    network: bool = True,
    timeout: int = None,
    workdir: str = "/workspace"
) -> str:
    """
    Esegue un comando bash in un container isolato.
    
    Args:
        command: Comando bash da eseguire
        image: Immagine container (default: kali-rolling)
        network: Abilita accesso rete (True/False)
        timeout: Timeout in secondi
        workdir: Directory di lavoro nel container
        
    Returns:
        Output del comando (stdout + stderr)
    """
    runtime = _get_container_runtime()
    if not runtime:
        return "[SANDBOX ERROR] No container runtime (podman/docker) available"
    
    image = image or DEFAULT_IMAGE
    timeout = timeout or CONTAINER_LIMITS["timeout"]
    
    # Verifica/scarica immagine
    if not _check_image_exists(runtime, image):
        if not _pull_image(runtime, image):
            # Fallback a alpine
            logger.warning(f"[ContainerSandbox] Using fallback image: {FALLBACK_IMAGE}")
            image = FALLBACK_IMAGE
            if not _check_image_exists(runtime, image):
                _pull_image(runtime, image)
    
    # Costruisci comando container
    container_id = f"sandbox_{uuid.uuid4().hex[:8]}"
    
    cmd = [
        runtime, "run",
        "--rm",                                    # Rimuovi dopo esecuzione
        "--name", container_id,
        "--memory", CONTAINER_LIMITS["memory"],
        "--cpus", CONTAINER_LIMITS["cpus"],
        "-w", workdir,
    ]
    
    # Network mode
    if network:
        cmd.extend(["--network", "host"])  # Accesso rete host (per scan)
    else:
        cmd.extend(["--network", "none"])  # Isolamento totale
    
    # Mount shared directory (read-only per sicurezza)
    cmd.extend(["-v", f"{SHARED_DIR}:/shared:ro"])
    
    # Immagine e comando
    cmd.extend([
        image,
        "/bin/bash", "-c", command
    ])
    
    logger.info(f"[ContainerSandbox] Running in {image}: {command[:60]}...")
    logger.debug(f"[ContainerSandbox] Full command: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        output = result.stdout.strip()
        errors = result.stderr.strip()
        
        if result.returncode == 0:
            return output if output else "[Container executed - no output]"
        else:
            combined = f"{output}\n{errors}".strip()
            return f"[CONTAINER ERROR] {combined}" if combined else f"[CONTAINER ERROR] Exit code {result.returncode}"
            
    except subprocess.TimeoutExpired:
        # Forza stop del container
        try:
            subprocess.run([runtime, "stop", container_id], timeout=5)
        except:
            pass
        return f"[SANDBOX TIMEOUT] Command exceeded {timeout}s limit"
    except Exception as e:
        logger.error(f"[ContainerSandbox] Execution error: {e}")
        return f"[SANDBOX ERROR] {str(e)}"

def run_python_in_sandbox(
    script_content: str,
    image: str = None,
    network: bool = True,
    timeout: int = None
) -> str:
    """
    Esegue uno script Python in un container isolato.
    
    Args:
        script_content: Contenuto dello script Python
        image: Immagine container
        network: Abilita accesso rete
        timeout: Timeout in secondi
        
    Returns:
        Output dello script
    """
    # Scrivi script in file temporaneo (nella shared dir)
    script_id = uuid.uuid4().hex[:8]
    script_path = os.path.join(SHARED_DIR, f"script_{script_id}.py")
    
    try:
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Esegui lo script nel container
        command = f"python3 /shared/script_{script_id}.py"
        
        return run_command_in_sandbox(
            command=command,
            image=image,
            network=network,
            timeout=timeout
        )
    finally:
        # Cleanup script file
        try:
            os.remove(script_path)
        except:
            pass

def run_nmap_in_sandbox(
    target: str,
    ports: str = "1-1000",
    flags: str = "-sT"
) -> str:
    """
    Esegue nmap in sandbox con parametri standard.
    
    Args:
        target: IP o hostname target
        ports: Range porte (default: 1-1000)
        flags: Flag nmap (default: -sT TCP connect)
        
    Returns:
        Output nmap
    """
    command = f"nmap {flags} -p {ports} {target}"
    
    return run_command_in_sandbox(
        command=command,
        image=DEFAULT_IMAGE,
        network=True,
        timeout=300  # 5 minuti per scan
    )

# ============================================================================
# DIRECT EXECUTION (Fallback)
# ============================================================================

def run_direct_fallback(command: str, timeout: int = 120) -> str:
    """
    Esecuzione diretta (fallback se container non disponibile).
    
    ⚠️ Usare solo se sandbox non funziona!
    """
    logger.warning(f"[ContainerSandbox] FALLBACK: Direct execution for: {command[:50]}...")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            executable="/bin/bash",
            capture_output=True,
            text=True,
            timeout=timeout
        )
        
        if result.returncode == 0:
            return result.stdout.strip() or "[No output]"
        else:
            return f"[ERROR] {result.stderr.strip()}"
            
    except subprocess.TimeoutExpired:
        return "[ERROR] Command timeout"
    except Exception as e:
        return f"[ERROR] {str(e)}"

# ============================================================================
# STATUS CHECK
# ============================================================================

def get_sandbox_status() -> dict:
    """
    Verifica lo stato del sandbox system.
    
    Returns:
        Dict con stato componenti
    """
    runtime = _get_container_runtime()
    
    status = {
        "available": runtime is not None,
        "runtime": runtime,
        "default_image": DEFAULT_IMAGE,
        "shared_dir": SHARED_DIR,
    }
    
    if runtime:
        # Check se immagine disponibile
        status["image_ready"] = _check_image_exists(runtime, DEFAULT_IMAGE)
    
    return status

# Log inizializzazione
_runtime = _get_container_runtime()
if _runtime:
    logger.info(f"[ContainerSandbox] Initialized with {_runtime}")
else:
    logger.warning("[ContainerSandbox] No container runtime available - will use direct execution")
