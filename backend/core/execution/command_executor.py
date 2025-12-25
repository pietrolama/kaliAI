#!/usr/bin/env python3
"""
Command Executor - Esecuzione comandi bash con sandbox Docker o subprocess
⚡ Supporta esecuzione parallela per comandi su più IP.
"""
import os
import subprocess
import logging
import time
import docker
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

logger = logging.getLogger('CommandExecutor')

# Percorsi
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
BASE_TEST_DIR = os.path.join(PROJECT_ROOT, 'test_env')
os.makedirs(BASE_TEST_DIR, exist_ok=True)

# Config da ENV
USE_DOCKER_SANDBOX = os.getenv("USE_DOCKER_SANDBOX", "false").lower() == "true"

def log_info(msg):
    logger.info(msg)

def execute_bash_command_docker(command: str, timeout: int = 8) -> str:
    """
    Esegue comando in sandbox Docker isolata.
    
    Args:
        command: Comando bash da eseguire
        timeout: Timeout in secondi
        
    Returns:
        Output del comando o messaggio di errore
    """
    try:
        client = docker.from_env()
        output = client.containers.run(
            "alpine",
            command=["sh", "-c", command],
            remove=True,
            network_mode="none",
            mem_limit="128m",
            cpu_period=100000, cpu_quota=50000,
            stdout=True,
            stderr=True,
            user="nobody",
            working_dir="/tmp",
            detach=False,
            timeout=timeout
        )
        decoded = output.decode()[:2048]
        log_info(f"[DOCKER][OUT] {decoded}")
        return decoded
    except Exception as e:
        log_info(f"[SANDBOX ERROR][DOCKER] {e}")
        return f"[SANDBOX ERROR] {e}"

def execute_bash_command_subprocess(command: str) -> str:
    """
    Esegue comando con subprocess in test_env directory.
    Include auto-installazione tool mancanti.
    
    Args:
        command: Comando bash da eseguire
        
    Returns:
        Output del comando o messaggio di errore
    """
    log_info(f"Tentativo di esecuzione comando Bash limitato: {command}")
    
    # === AUTO-INSTALL TOOL MANCANTI ===
    try:
        from tools.tool_manager import tool_manager
        
        # Identifica tool dal comando
        first_word = command.strip().split()[0] if command.strip() else ""
        
        # Tool comuni che potrebbero essere richiesti
        tool_keywords = {
            'dirb': 'dirb',
            'gobuster': 'gobuster',
            'whatweb': 'whatweb',
            'nikto': 'nikto',
            'sqlmap': 'sqlmap',
            'hydra': 'hydra',
            'wfuzz': 'wfuzz',
            'masscan': 'masscan',
            'ffmpeg': 'ffmpeg',
            'sslscan': 'sslscan'
        }
        
        if first_word in tool_keywords:
            tool_name = tool_keywords[first_word]
            if not tool_manager.is_tool_installed(tool_name):
                log_info(f"[TOOL-MANAGER] {tool_name} mancante, installazione automatica...")
                success = tool_manager.auto_install_if_missing(tool_name)
                if success:
                    log_info(f"[TOOL-MANAGER] ✅ {tool_name} installato con successo")
                else:
                    log_info(f"[TOOL-MANAGER] ❌ Installazione {tool_name} fallita")
                    return f"[TOOLS][ERRORE] Tool {tool_name} non disponibile e installazione fallita. Installa manualmente: sudo apt install {tool_name}"
    except Exception as e:
        log_info(f"[TOOL-MANAGER] Errore auto-install: {e}")
    
    # 🔓 SECURITY CHECKS DISABILITATI - tutti i comandi permessi
    # blocked_patterns = [
    #     "cd ../", "../", "rm -rf /", "rm -f /", "shutdown", "reboot", "mkfs", 
    #     "dd if=", "scp", "nc -e", "python -c", "chmod 777", "chown root"
    # ]
    # 
    # # Verifica pattern pericolosi
    # for pattern in blocked_patterns:
    #     if pattern in command:
    #         return "[TOOLS] Comando bloccato per sicurezza."
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=BASE_TEST_DIR,
            capture_output=True,
            text=True,
            timeout=120  # Timeout aumentato per scan complessi
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            log_info(f"[SUBPROCESS][OUT] {output}")
            return output if output else "[TOOLS] Comando eseguito (nessun output)."
        else:
            err = result.stderr.strip()
            log_info(f"[SUBPROCESS][ERR] {err}")
            return f"[TOOLS][ERRORE] {err}"
    except subprocess.TimeoutExpired:
        return "[TOOLS][ERRORE] Comando scaduto (timeout)."
    except FileNotFoundError:
        return f"[TOOLS][ERRORE] Comando '{command}' non trovato nell'ambiente di test."
    except Exception as e:
        return f"[TOOLS][ERRORE] Errore imprevisto: {e}"


def execute_commands_parallel(commands: List[str], max_workers: int = 5) -> List[Dict[str, str]]:
    """
    ⚡ ESECUZIONE PARALLELA: Esegue più comandi contemporaneamente.
    
    Utile quando devi eseguire lo stesso comando su più IP o testare più porte.
    Riduce drasticamente i tempi di attesa durante la fase di discovery.
    
    Args:
        commands: Lista di comandi da eseguire in parallelo
        max_workers: Numero massimo di thread paralleli (default: 5)
        
    Returns:
        Lista di dict con 'command', 'output', 'success' per ogni comando
    """
    results = []
    
    def execute_single(command: str) -> Dict[str, str]:
        """Esegue un singolo comando e ritorna risultato"""
        try:
            output = execute_bash_command(command)
            return {
                'command': command,
                'output': output,
                'success': not output.startswith('[TOOLS][ERRORE]')
            }
        except Exception as e:
            return {
                'command': command,
                'output': f"[TOOLS][ERRORE] {str(e)}",
                'success': False
            }
    
    # Esegui comandi in parallelo
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Sottometti tutti i comandi
        future_to_command = {
            executor.submit(execute_single, cmd): cmd 
            for cmd in commands
        }
        
        # Raccogli risultati man mano che completano
        for future in as_completed(future_to_command):
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                command = future_to_command[future]
                results.append({
                    'command': command,
                    'output': f"[TOOLS][ERRORE] {str(e)}",
                    'success': False
                })
    
    # Ordina risultati per mantenere ordine originale (opzionale)
    # results.sort(key=lambda x: commands.index(x['command']))
    
    return results

def execute_bash_command(command: str) -> str:
    """
    Esegue comando bash con validazione sicurezza e metriche.
    Funzione unificata che usa Docker o subprocess in base a USE_DOCKER_SANDBOX.
    
    Args:
        command: Comando bash da eseguire
        
    Returns:
        Output del comando o messaggio di errore
    """
    start_time = time.time()
    
    # 🔓 SECURITY BYPASS SEMPRE ATTIVO (disabilitato per permettere tutti i comandi)
    bypass_enabled = True  # SEMPRE TRUE - controlli sicurezza disattivati
    
    # Controlla se security bypass è attivo (solo in sessione Flask) - DISABILITATO
    # try:
    #     from flask import session
    #     bypass_enabled = session.get('security_bypass', False)
    # except RuntimeError:
    #     # Non in contesto Flask (es. test standalone)
    #     pass
    
    # Validazione sicurezza
    from tools.security import SecurityValidator, auditor
    is_valid, reason = SecurityValidator.validate_command(command, bypass=bypass_enabled)
    if not is_valid:
        auditor.log_blocked(command, reason)
        error_msg = f"[SECURITY] Comando bloccato: {reason}"
        from tools.monitoring import metrics_collector
        metrics_collector.track_security_block(command, reason)
        return error_msg
    
    # Log comando permesso
    auditor.log_allowed(command)
    
    # Esegui
    try:
        if USE_DOCKER_SANDBOX:
            output = execute_bash_command_docker(command)
        else:
            output = execute_bash_command_subprocess(command)
        
        # Track metrics
        duration = time.time() - start_time
        success = "[ERRORE]" not in output and "[ERROR]" not in output
        from tools.monitoring import metrics_collector
        metrics_collector.track_command_execution(
            command, 
            duration, 
            success,
            len(output)
        )
        
        return output
        
    except Exception as e:
        duration = time.time() - start_time
        from tools.monitoring import metrics_collector
        metrics_collector.track_command_execution(command, duration, False)
        return f"[TOOLS][ERRORE] {str(e)}"

