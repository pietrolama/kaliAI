#!/usr/bin/env python3
"""
Command Executor - Esecuzione comandi bash con sandbox Docker o subprocess
⚡ Supporta esecuzione parallela per comandi su più IP.
📝 Integrato con Execution Ledger per logging atomico.
"""
import os
import subprocess
import logging
import time
import docker
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional

# Execution Ledger for audit trail
from backend.core.ledger import record_tool_call, record_tool_output, record_error

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
    # Log raw command with repr() to preserve special chars like *
    logger.info(f"Tentativo di esecuzione comando Bash limitato: {command}")
    logger.debug(f"[RAW_CMD] {repr(command)}")  # Debug level shows actual string with escapes
    
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
            executable="/bin/bash",  # Use bash for brace expansion, arrays, etc.
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

def execute_bash_command(command: str, actor: str = "Batou") -> str:
    """
    Esegue comando bash con validazione sicurezza, metriche e logging su Ledger.
    Funzione unificata che usa Docker o subprocess in base a USE_DOCKER_SANDBOX.
    
    Args:
        command: Comando bash da eseguire
        actor: Nome dell'agente che ha richiesto l'esecuzione (per Ledger)
        
    Returns:
        Output del comando o messaggio di errore
    """
    start_time = time.time()
    
    # 📝 LEDGER: Record TOOL_CALL before execution
    call_id = record_tool_call(actor, "bash", command)
    
    # 🔒 NEW SECURITY LAYER (SafeExecutor) - DENY-WINS
    new_security_validated = False
    try:
        from backend.config.security import (
            full_security_check, 
            log_security_event,
            CURRENT_SECURITY_LEVEL,
            SecurityLevel
        )
        
        is_safe, reason = full_security_check(command)
        
        if not is_safe:
            log_security_event("VIOLATION", command, reason, blocked=True)
            error_msg = f"[SECURITY BLOCK] {reason}"
            logger.warning(f"[Security] 🚫 BLOCKED: {command[:50]}... - {reason}")
            record_tool_output(call_id, error_msg, status="BLOCKED", return_code=-1)
            return error_msg
        
        # New security layer validated successfully
        new_security_validated = True
        log_security_event("EXECUTE", command, f"Approved ({actor})", blocked=False)
        level_str = CURRENT_SECURITY_LEVEL.value.upper()
        logger.info(f"[Security] ⚠️ SECURITY PROFILE: {level_str} for: {command[:50]}")
        
    except ImportError:
        # Fallback al vecchio sistema se nuovo non disponibile
        logger.warning("[Security] SafeExecutor not available, using legacy security")
    
    # 🔓 LEGACY SECURITY (skip if new system already validated)
    if not new_security_validated:
        from tools.security import SecurityValidator, auditor
        bypass_enabled = True  # Bypass legacy - usiamo il nuovo sistema sopra
        is_valid, reason = SecurityValidator.validate_command(command, bypass=bypass_enabled)
        if not is_valid:
            auditor.log_blocked(command, reason)
            error_msg = f"[SECURITY] Comando bloccato: {reason}"
            from tools.monitoring import metrics_collector
            metrics_collector.track_security_block(command, reason)
            record_tool_output(call_id, error_msg, status="BLOCKED", return_code=-1)
            return error_msg
        
        # Log comando permesso (solo se legacy è attivo)
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
        
        # 🧠 STRATEGIC MEMORY: Track technique for cross-session learning
        try:
            from backend.core.memory.strategic_memory import get_strategic_memory
            memory = get_strategic_memory()
            
            # Extract technique info from command
            first_word = command.split()[0].split('/')[-1] if command.strip() else "unknown"
            
            # Try to extract target service/port
            target_service = "unknown"
            target_port = 0
            
            # Common patterns
            if "ssh" in command.lower():
                target_service = "ssh"
                target_port = 22
            elif "http" in command.lower() or "curl" in command.lower() or "wget" in command.lower():
                target_service = "http"
                target_port = 80
            elif "smb" in command.lower() or "445" in command:
                target_service = "smb"
                target_port = 445
            elif "ftp" in command.lower():
                target_service = "ftp"
                target_port = 21
            elif "nmap" in command.lower():
                target_service = "recon"
            
            memory.remember_technique(
                technique_id=first_word,
                technique_name=first_word.capitalize(),
                mitre_id="",  # Could be enhanced with mapping
                target_service=target_service,
                target_port=target_port,
                success=success,
                output_summary=output[:200] if success else "",
                context={"actor": actor, "full_command": command[:100]}
            )
        except Exception as e:
            logger.debug(f"[StrategicMemory] Could not record: {e}")
        
        # 📝 LEDGER: Record TOOL_OUTPUT after execution
        record_tool_output(
            call_id, 
            output, 
            status="SUCCESS" if success else "ERROR",
            return_code=0 if success else 1,
            duration_ms=int(duration * 1000)
        )
        
        return output
        
    except Exception as e:
        duration = time.time() - start_time
        from tools.monitoring import metrics_collector
        metrics_collector.track_command_execution(command, duration, False)
        # 📝 LEDGER: Record error
        record_error(actor, str(e), command=command, correlation_id=call_id)
        return f"[TOOLS][ERRORE] {str(e)}"

