#!/usr/bin/env python3
"""
Task Context Manager - Gestisce la persistenza del contesto dei task
"""
import uuid
import logging
import os
import re
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger('TaskContextManager')

# Execution modes - determines operational behavior
class ExecutionMode:
    SELF_ANALYSIS = "SELF_ANALYSIS"    # Analyzing own codebase/files
    LOCAL_HOST = "LOCAL_HOST"          # Operating on local filesystem
    REMOTE_TARGET = "REMOTE_TARGET"    # Pentesting remote target
    ARENA = "ARENA"                    # Controlled arena environment

class TaskContextManager:
    """
    Gestisce la cache dei contesti dei task in memoria.
    Ogni task ha un ID univoco e mantiene tutto il contesto dell'esecuzione.
    """
    
    # Project root for self-analysis detection
    PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    
    def __init__(self, ttl_hours: int = 24):
        """
        Args:
            ttl_hours: Tempo di vita dei task in cache (default: 24 ore)
        """
        self.task_cache: Dict[str, Dict[str, Any]] = {}
        self.ttl_hours = ttl_hours
    
    def _detect_mode(self, prompt: str) -> tuple:
        """
        Auto-detect execution mode from prompt content.
        
        Returns:
            (mode, root_path, target_type)
        """
        prompt_lower = prompt.lower()
        
        # Patterns that indicate self-analysis
        self_analysis_patterns = [
            r"backend/",
            r"frontend/",
            r"kaliAI",
            r"python_sandbox",
            r"swarm\.py",
            r"app\.py",
            r"nostro|proprio|questo progetto",
            r"analizza.*codice",
            r"file.*locale",
        ]
        
        for pattern in self_analysis_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                return (ExecutionMode.SELF_ANALYSIS, self.PROJECT_ROOT, "LOCAL_FILE")
        
        # Patterns that indicate remote target
        remote_patterns = [
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",  # IP address
            r"target",
            r"scansiona",
            r"exploit",
            r"penetration",
            r"attacco",
        ]
        
        for pattern in remote_patterns:
            if re.search(pattern, prompt, re.IGNORECASE):
                return (ExecutionMode.REMOTE_TARGET, None, "REMOTE_HOST")
        
        # Default to local host for file system tasks
        if any(word in prompt_lower for word in ["file", "directory", "trova", "cerca", "ls", "find"]):
            return (ExecutionMode.LOCAL_HOST, "/home", "LOCAL_FS")
        
        # Default
        return (ExecutionMode.LOCAL_HOST, self.PROJECT_ROOT, "UNKNOWN")
    
    def create_task(self, prompt: str, objective_analysis: Optional[Dict] = None, 
                   mode: Optional[str] = None) -> str:
        """
        Crea un nuovo task e restituisce il task-id.
        
        Args:
            prompt: Prompt originale dell'utente
            objective_analysis: Analisi dell'obiettivo (se disponibile)
            mode: Override manuale del modo di esecuzione
            
        Returns:
            task_id: ID univoco del task
        """
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        
        # Auto-detect or use provided mode
        if mode:
            detected_mode = mode
            root_path = self.PROJECT_ROOT if mode == ExecutionMode.SELF_ANALYSIS else None
            target_type = "MANUAL_OVERRIDE"
        else:
            detected_mode, root_path, target_type = self._detect_mode(prompt)
        
        logger.info(f"[TASK-CONTEXT] Mode detected: {detected_mode} (target: {target_type})")
        
        self.task_cache[task_id] = {
            "task_id": task_id,
            "created_at": datetime.now(),
            "prompt": prompt,
            "objective_analysis": objective_analysis or {},
            # NEW: Execution context
            "execution_mode": detected_mode,
            "root_path": root_path,
            "target_type": target_type,
            # Existing fields
            "target_ip": None,
            "confirmed_target_ip": None,
            "steps": [],
            "step_results": [],
            "completed_context": "",
            "last_step_number": 0,
            "last_failure": None,
            "open_ports": [],
            "discovered_services": [],
            "status": "running"  # running, completed, failed
        }
        
        logger.info(f"[TASK-CONTEXT] Task creato: {task_id}")
        return task_id
    
    def update_task(self, task_id: str, **updates) -> bool:
        """
        Aggiorna i dati di un task.
        
        Args:
            task_id: ID del task
            **updates: Campi da aggiornare
            
        Returns:
            True se il task esiste e è stato aggiornato, False altrimenti
        """
        if task_id not in self.task_cache:
            logger.warning(f"[TASK-CONTEXT] Task non trovato: {task_id}")
            return False
        
        self.task_cache[task_id].update(updates)
        self.task_cache[task_id]["updated_at"] = datetime.now()
        logger.debug(f"[TASK-CONTEXT] Task aggiornato: {task_id} - {list(updates.keys())}")
        return True
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera il contesto di un task.
        
        Args:
            task_id: ID del task
            
        Returns:
            Dizionario con il contesto del task o None se non trovato/scaduto
        """
        if task_id not in self.task_cache:
            logger.warning(f"[TASK-CONTEXT] Task non trovato: {task_id}")
            return None
        
        task = self.task_cache[task_id]
        
        # Verifica se il task è scaduto
        created_at = task.get("created_at")
        if created_at:
            age = datetime.now() - created_at
            if age > timedelta(hours=self.ttl_hours):
                logger.info(f"[TASK-CONTEXT] Task scaduto: {task_id} (età: {age})")
                del self.task_cache[task_id]
                return None
        
        return task
    
    def get_task_context_for_chat(self, task_id: str) -> Optional[str]:
        """
        Genera un prompt di contesto per la chat basato sul task.
        
        Args:
            task_id: ID del task
            
        Returns:
            Stringa con il contesto formattato per l'LLM o None
        """
        task = self.get_task(task_id)
        if not task:
            return None
        
        context = "══════════════════════════════════════════════════\n"
        context += "📋 CONTESTO DELLA MISSIONE PRECEDENTE\n"
        context += "══════════════════════════════════════════════════\n\n"
        
        # Obiettivo
        context += f"🎯 OBIETTIVO ORIGINALE:\n{task.get('prompt', 'N/A')}\n\n"
        
        # Target IP
        target_ip = task.get('confirmed_target_ip') or task.get('target_ip')
        if target_ip:
            context += f"🎯 IP TARGET CONFERMATO: {target_ip}\n\n"
        
        # Analisi obiettivo
        obj_analysis = task.get('objective_analysis', {})
        if obj_analysis:
            target_desc = obj_analysis.get('target_description', '')
            if target_desc:
                context += f"📱 TARGET: {target_desc}\n"
            target_hints = obj_analysis.get('target_hints', [])
            if target_hints:
                context += f"💡 HINT IDENTIFICAZIONE: {', '.join(target_hints[:3])}\n"
            context += "\n"
        
        # Step eseguiti
        steps = task.get('steps', [])
        step_results = task.get('step_results', [])
        if steps:
            context += f"📝 STEP ESEGUITI ({len(steps)} totali):\n"
            for i, step in enumerate(steps[:5], 1):  # Mostra max 5 step
                context += f"   {i}. {step}\n"
                # Aggiungi risultato se disponibile
                if i <= len(step_results):
                    result = step_results[i-1]
                    if result.get('status') == 'completato':
                        context += f"      ✅ Completato\n"
                    elif result.get('status') == 'fallito':
                        context += f"      ❌ Fallito: {result.get('result', 'N/A')[:100]}\n"
            context += "\n"
        
        # Ultimo step fallito
        last_failure = task.get('last_failure')
        if last_failure:
            context += f"⚠️ ULTIMO STEP FALLITO:\n"
            context += f"   Step: {last_failure.get('step_number', 'N/A')}\n"
            context += f"   Descrizione: {last_failure.get('step_description', 'N/A')}\n"
            context += f"   Errore: {last_failure.get('error', 'N/A')}\n\n"
        
        # Porte aperte scoperte
        open_ports = task.get('open_ports', [])
        if open_ports:
            context += f"🔌 PORTE APERTE SCOPERTE:\n"
            context += f"   {', '.join(open_ports)}\n\n"
        
        # Servizi scoperti
        services = task.get('discovered_services', [])
        if services:
            context += f"🌐 SERVIZI SCOPERTI:\n"
            for service in services[:3]:
                context += f"   • {service}\n"
            context += "\n"
        
        # Stato
        status = task.get('status', 'unknown')
        context += f"📊 STATO MISSIONE: {status.upper()}\n"
        
        context += "\n══════════════════════════════════════════════════\n"
        context += "💬 DOMANDA DELL'UTENTE (riferita a questa missione):\n"
        context += "══════════════════════════════════════════════════\n"
        
        return context
    
    def cleanup_expired_tasks(self):
        """Rimuove i task scaduti dalla cache."""
        now = datetime.now()
        expired = []
        
        for task_id, task in self.task_cache.items():
            created_at = task.get("created_at")
            if created_at:
                age = now - created_at
                if age > timedelta(hours=self.ttl_hours):
                    expired.append(task_id)
        
        for task_id in expired:
            del self.task_cache[task_id]
            logger.info(f"[TASK-CONTEXT] Task rimosso (scaduto): {task_id}")
        
        if expired:
            logger.info(f"[TASK-CONTEXT] Pulizia completata: {len(expired)} task rimossi")
    
    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche sulla cache."""
        return {
            "total_tasks": len(self.task_cache),
            "ttl_hours": self.ttl_hours
        }


# Istanza globale
_task_context_manager = None

def get_task_context_manager() -> TaskContextManager:
    """Restituisce l'istanza globale del TaskContextManager."""
    global _task_context_manager
    if _task_context_manager is None:
        _task_context_manager = TaskContextManager()
    return _task_context_manager

