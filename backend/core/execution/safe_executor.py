#!/usr/bin/env python3
"""
Safe Executor - Security Proxy tra l'AI e il Sistema Operativo
🛡️ Intercetta, valida e logga ogni comando prima dell'esecuzione.

Funzionalità:
- Validazione IP/Domini contro whitelist
- Blocco pattern distruttivi
- Audit logging completo
- Integrazione con Container Sandbox
"""

import os
import re
import logging
import subprocess
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime

# Import security config
from backend.config.security import (
    SecurityLevel,
    CURRENT_SECURITY_LEVEL,
    full_security_check,
    validate_target,
    validate_command,
    extract_targets_from_command,
    log_security_event,
)

logger = logging.getLogger('SafeExecutor')

# ============================================================================
# EXCEPTIONS
# ============================================================================

class SecurityViolation(Exception):
    """Eccezione sollevata quando un comando viola le policy di sicurezza."""
    
    def __init__(self, command: str, reason: str, targets: list = None):
        self.command = command
        self.reason = reason
        self.targets = targets or []
        self.timestamp = datetime.now().isoformat()
        super().__init__(f"SECURITY VIOLATION: {reason}")
    
    def to_dict(self) -> dict:
        return {
            "type": "SecurityViolation",
            "command": self.command[:100],
            "reason": self.reason,
            "targets": self.targets,
            "timestamp": self.timestamp,
        }

# ============================================================================
# EXECUTION CONTEXT
# ============================================================================

@dataclass
class ExecutionContext:
    """Contesto di esecuzione per tracking e audit."""
    actor: str = "unknown"          # Chi ha richiesto (Batou, Major, etc.)
    mission_id: str = None          # ID missione corrente
    sandbox_mode: bool = True       # Esegui in container?
    allow_network: bool = True      # Permetti accesso rete nel sandbox?
    timeout: int = 120              # Timeout in secondi

# ============================================================================
# SAFE EXECUTOR CLASS
# ============================================================================

class SafeExecutor:
    """
    Proxy sicuro per l'esecuzione di comandi.
    
    Ogni comando passa attraverso:
    1. Security Check (IP, pattern, tool)
    2. Audit Logging
    3. Esecuzione (sandbox o direct)
    """
    
    def __init__(self):
        self.security_level = CURRENT_SECURITY_LEVEL
        self._execution_count = 0
        self._blocked_count = 0
        logger.info(f"[SafeExecutor] Initialized with security level: {self.security_level.value}")
    
    def execute(
        self, 
        command: str, 
        context: ExecutionContext = None
    ) -> Tuple[bool, str]:
        """
        Esegue un comando dopo validazione di sicurezza.
        
        Args:
            command: Comando bash da eseguire
            context: Contesto di esecuzione opzionale
            
        Returns:
            Tuple (success, output/error)
            
        Raises:
            SecurityViolation: Se il comando viola le policy
        """
        if context is None:
            context = ExecutionContext()
        
        self._execution_count += 1
        
        # === STEP 1: Security Check ===
        try:
            self._security_check(command, context)
        except SecurityViolation as e:
            self._blocked_count += 1
            log_security_event(
                event_type="VIOLATION",
                command=command,
                reason=e.reason,
                blocked=True
            )
            raise
        
        # === STEP 2: Audit Log (comando approvato) ===
        log_security_event(
            event_type="EXECUTE",
            command=command,
            reason=f"Approved by {context.actor}",
            blocked=False
        )
        
        # === STEP 3: Esecuzione ===
        if context.sandbox_mode:
            return self._execute_in_sandbox(command, context)
        else:
            return self._execute_direct(command, context)
    
    def _security_check(self, command: str, context: ExecutionContext) -> None:
        """
        Esegue tutti i controlli di sicurezza.
        
        Raises:
            SecurityViolation: Se qualsiasi check fallisce
        """
        # Check completo (comando + target)
        is_safe, reason = full_security_check(command)
        
        if not is_safe:
            targets = extract_targets_from_command(command)
            raise SecurityViolation(
                command=command,
                reason=reason,
                targets=targets
            )
        
        logger.debug(f"[SafeExecutor] Security check passed: {reason}")
    
    def _execute_in_sandbox(
        self, 
        command: str, 
        context: ExecutionContext
    ) -> Tuple[bool, str]:
        """
        Esegue il comando in un container Podman isolato.
        """
        try:
            from backend.core.execution.container_sandbox import run_command_in_sandbox
            
            output = run_command_in_sandbox(
                command=command,
                network=context.allow_network,
                timeout=context.timeout
            )
            return (True, output)
            
        except ImportError:
            # Fallback a esecuzione diretta se sandbox non disponibile
            logger.warning("[SafeExecutor] Sandbox not available, falling back to direct execution")
            return self._execute_direct(command, context)
        except Exception as e:
            logger.error(f"[SafeExecutor] Sandbox execution failed: {e}")
            return (False, f"[SANDBOX ERROR] {str(e)}")
    
    def _execute_direct(
        self, 
        command: str, 
        context: ExecutionContext
    ) -> Tuple[bool, str]:
        """
        Esegue il comando direttamente con subprocess.
        
        ⚠️ Usare solo se sandbox non disponibile o per comandi fidati.
        """
        logger.info(f"[SafeExecutor] Direct execution: {command[:80]}...")
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                executable="/bin/bash",
                capture_output=True,
                text=True,
                timeout=context.timeout,
                cwd=os.path.expanduser("~")
            )
            
            if result.returncode == 0:
                output = result.stdout.strip() or "[No output]"
                return (True, output)
            else:
                error = result.stderr.strip() or f"Exit code: {result.returncode}"
                return (False, f"[ERROR] {error}")
                
        except subprocess.TimeoutExpired:
            return (False, "[ERROR] Command timeout")
        except Exception as e:
            return (False, f"[ERROR] {str(e)}")
    
    def get_stats(self) -> dict:
        """Restituisce statistiche di esecuzione."""
        return {
            "security_level": self.security_level.value,
            "total_executions": self._execution_count,
            "blocked_executions": self._blocked_count,
            "block_rate": f"{(self._blocked_count / max(1, self._execution_count)) * 100:.1f}%"
        }

# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_executor_instance: Optional[SafeExecutor] = None

def get_safe_executor() -> SafeExecutor:
    """Restituisce l'istanza singleton di SafeExecutor."""
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = SafeExecutor()
    return _executor_instance

def safe_execute(command: str, actor: str = "AI", sandbox: bool = True) -> str:
    """
    Funzione di convenienza per esecuzione sicura.
    
    Args:
        command: Comando da eseguire
        actor: Chi richiede l'esecuzione
        sandbox: Usa container sandbox
        
    Returns:
        Output del comando o messaggio di errore
        
    Raises:
        SecurityViolation: Se il comando è bloccato
    """
    executor = get_safe_executor()
    context = ExecutionContext(actor=actor, sandbox_mode=sandbox)
    
    success, output = executor.execute(command, context)
    
    if success:
        return output
    else:
        return output  # Gli errori sono già formattati

# ============================================================================
# TOGUSA INTEGRATION
# ============================================================================

def format_violation_for_togusa(violation: SecurityViolation) -> str:
    """
    Formatta una SecurityViolation per il report di Togusa.
    """
    return (
        f"🚨 **VIOLAZIONE RILEVATA** 🚨\n"
        f"**Motivo**: {violation.reason}\n"
        f"**Target coinvolti**: {', '.join(violation.targets) if violation.targets else 'N/A'}\n"
        f"**Timestamp**: {violation.timestamp}\n"
        f"**Azione**: Comando BLOCCATO. Maggiore, richiedi autorizzazione manuale o cambia strategia."
    )
