#!/usr/bin/env python3
"""
Goal Tracker - Traccia obiettivi e progressi della missione
🎯 Mantiene focus sull'obiettivo finale e suggerisce prossime azioni.

Funzionalità:
- Definizione obiettivi gerarchici (goal -> subgoals)
- Tracking progressi con evidence
- Suggerimento prossima azione basato su stato
- Detection blocchi e suggerimenti alternativi
"""

import os
import json
import logging
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger('GoalTracker')

class GoalStatus(Enum):
    """Stato di un obiettivo"""
    PENDING = "pending"      # Non ancora iniziato
    IN_PROGRESS = "in_progress"  # Lavoro in corso
    BLOCKED = "blocked"      # Bloccato, serve alternativa
    ACHIEVED = "achieved"    # Completato con successo
    FAILED = "failed"        # Fallito definitivamente
    SKIPPED = "skipped"      # Saltato (non più rilevante)

class GoalPriority(Enum):
    """Priorità obiettivo"""
    CRITICAL = 1    # Missione fallisce senza questo
    HIGH = 2        # Molto importante
    MEDIUM = 3      # Nice to have
    LOW = 4         # Opportunistico

@dataclass
class Goal:
    """Rappresenta un obiettivo"""
    id: str
    name: str
    description: str
    status: GoalStatus = GoalStatus.PENDING
    priority: GoalPriority = GoalPriority.MEDIUM
    parent_id: Optional[str] = None
    evidence: List[str] = field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 5
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    
    def add_evidence(self, evidence: str):
        self.evidence.append(f"[{datetime.now().strftime('%H:%M:%S')}] {evidence}")
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d['status'] = self.status.value
        d['priority'] = self.priority.value
        return d

@dataclass
class MissionState:
    """Stato complessivo della missione"""
    mission_id: str
    primary_goal: str
    start_time: str
    goals: Dict[str, Goal] = field(default_factory=dict)
    current_focus: Optional[str] = None
    blocked_paths: List[str] = field(default_factory=list)
    
    def get_progress(self) -> float:
        """Calcola progresso 0-100%"""
        if not self.goals:
            return 0.0
        achieved = sum(1 for g in self.goals.values() if g.status == GoalStatus.ACHIEVED)
        return (achieved / len(self.goals)) * 100

class GoalTracker:
    """
    Traccia obiettivi e guida l'AI verso il completamento.
    
    Uso:
        tracker = GoalTracker()
        tracker.set_mission("Ottieni accesso root a 192.168.1.1")
        tracker.add_subgoal("root_access", "Enum ports", "Scopri servizi aperti")
        tracker.mark_achieved("enum_ports", "Trovati: 22, 80, 443")
        tracker.get_next_action()  # Suggerisce prossimo passo
    """
    
    def __init__(self, persistence_dir: str = None):
        self.state: Optional[MissionState] = None
        self.persistence_dir = Path(persistence_dir or "/tmp/kali_goals")
        self.persistence_dir.mkdir(parents=True, exist_ok=True)
    
    def set_mission(self, primary_goal: str, mission_id: str = None) -> str:
        """
        Inizia una nuova missione con obiettivo primario.
        
        Args:
            primary_goal: Obiettivo finale (es: "Ottieni flag dal server")
            mission_id: ID opzionale
            
        Returns:
            mission_id
        """
        mission_id = mission_id or f"mission_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.state = MissionState(
            mission_id=mission_id,
            primary_goal=primary_goal,
            start_time=datetime.now().isoformat()
        )
        
        # Crea goal primario
        primary = Goal(
            id="primary",
            name="Primary Objective",
            description=primary_goal,
            priority=GoalPriority.CRITICAL
        )
        self.state.goals["primary"] = primary
        self.state.current_focus = "primary"
        
        logger.info(f"[GoalTracker] Mission started: {primary_goal}")
        self._persist()
        
        return mission_id
    
    def add_subgoal(
        self, 
        goal_id: str, 
        name: str, 
        description: str,
        parent_id: str = "primary",
        priority: GoalPriority = GoalPriority.MEDIUM
    ) -> Goal:
        """
        Aggiunge un sotto-obiettivo.
        
        Args:
            goal_id: Identificatore univoco
            name: Nome breve
            description: Descrizione dettagliata
            parent_id: Goal padre
            priority: Priorità
        """
        if not self.state:
            raise ValueError("No mission active. Call set_mission first.")
        
        goal = Goal(
            id=goal_id,
            name=name,
            description=description,
            parent_id=parent_id,
            priority=priority
        )
        
        self.state.goals[goal_id] = goal
        logger.debug(f"[GoalTracker] Subgoal added: {goal_id} -> {name}")
        self._persist()
        
        return goal
    
    def start_goal(self, goal_id: str):
        """Marca un goal come in corso"""
        if goal_id in self.state.goals:
            self.state.goals[goal_id].status = GoalStatus.IN_PROGRESS
            self.state.goals[goal_id].attempts += 1
            self.state.current_focus = goal_id
            self._persist()
    
    def mark_achieved(self, goal_id: str, evidence: str = ""):
        """
        Marca un obiettivo come raggiunto.
        
        Args:
            goal_id: ID dell'obiettivo
            evidence: Prova del completamento
        """
        if goal_id not in self.state.goals:
            logger.warning(f"[GoalTracker] Unknown goal: {goal_id}")
            return
        
        goal = self.state.goals[goal_id]
        goal.status = GoalStatus.ACHIEVED
        goal.completed_at = datetime.now().isoformat()
        
        if evidence:
            goal.add_evidence(f"ACHIEVED: {evidence}")
        
        logger.info(f"[GoalTracker] ✅ Goal achieved: {goal.name}")
        self._persist()
    
    def mark_blocked(self, goal_id: str, reason: str):
        """
        Marca un obiettivo come bloccato.
        
        Args:
            goal_id: ID dell'obiettivo
            reason: Motivo del blocco
        """
        if goal_id not in self.state.goals:
            return
        
        goal = self.state.goals[goal_id]
        goal.status = GoalStatus.BLOCKED
        goal.add_evidence(f"BLOCKED: {reason}")
        
        self.state.blocked_paths.append(f"{goal_id}: {reason}")
        
        logger.warning(f"[GoalTracker] ⚠️ Goal blocked: {goal.name} - {reason}")
        self._persist()
    
    def mark_failed(self, goal_id: str, reason: str):
        """Marca un obiettivo come fallito definitivamente"""
        if goal_id not in self.state.goals:
            return
        
        goal = self.state.goals[goal_id]
        goal.status = GoalStatus.FAILED
        goal.add_evidence(f"FAILED: {reason}")
        
        logger.error(f"[GoalTracker] ❌ Goal failed: {goal.name}")
        self._persist()
    
    def get_next_action(self) -> Tuple[str, str]:
        """
        Suggerisce la prossima azione basata sullo stato.
        
        Returns:
            Tuple (action_type, suggestion)
        """
        if not self.state:
            return ("error", "No mission active")
        
        # Trova goal non completati ordinati per priorità
        pending = [
            g for g in self.state.goals.values() 
            if g.status in [GoalStatus.PENDING, GoalStatus.IN_PROGRESS]
        ]
        
        if not pending:
            # Tutti completati?
            achieved = sum(1 for g in self.state.goals.values() if g.status == GoalStatus.ACHIEVED)
            if achieved == len(self.state.goals):
                return ("complete", "🎉 Tutti gli obiettivi raggiunti! MISSION CLOSED.")
            else:
                return ("stuck", "Tutti i path sono bloccati. Serve nuovo vettore d'attacco.")
        
        # Ordina per priorità
        pending.sort(key=lambda g: g.priority.value)
        next_goal = pending[0]
        
        # Check se bloccato troppe volte
        if next_goal.attempts >= next_goal.max_attempts:
            return (
                "change_vector", 
                f"Goal '{next_goal.name}' ha fallito {next_goal.attempts} volte. "
                f"Cerca un vettore alternativo. Path bloccati: {self.state.blocked_paths[-3:]}"
            )
        
        # Suggerimenti basati sul tipo di goal
        if "enum" in next_goal.name.lower() or "recon" in next_goal.name.lower():
            return (
                "enumerate",
                f"Procedi con: {next_goal.description}\n"
                f"Suggerimento: nmap, gobuster, nikto, whatweb"
            )
        elif "exploit" in next_goal.name.lower():
            return (
                "exploit",
                f"Procedi con: {next_goal.description}\n"
                f"Suggerimento: searchsploit, metasploit, manual exploit"
            )
        elif "priv" in next_goal.name.lower() or "root" in next_goal.name.lower():
            return (
                "privesc",
                f"Procedi con: {next_goal.description}\n"
                f"Suggerimento: linpeas, winpeas, sudo -l, SUID"
            )
        else:
            return (
                "proceed",
                f"Prossimo obiettivo: {next_goal.name}\n{next_goal.description}"
            )
    
    def get_status_report(self) -> str:
        """Genera report leggibile dello stato"""
        if not self.state:
            return "No mission active."
        
        lines = [
            f"## Mission Status: {self.state.mission_id}",
            f"**Primary Goal:** {self.state.primary_goal}",
            f"**Progress:** {self.state.get_progress():.1f}%",
            "",
            "### Goals:"
        ]
        
        for goal_id, goal in self.state.goals.items():
            status_emoji = {
                GoalStatus.PENDING: "⚪",
                GoalStatus.IN_PROGRESS: "🔵",
                GoalStatus.BLOCKED: "🟠",
                GoalStatus.ACHIEVED: "✅",
                GoalStatus.FAILED: "❌",
                GoalStatus.SKIPPED: "⏭️"
            }.get(goal.status, "❓")
            
            lines.append(f"- {status_emoji} **{goal.name}** [{goal.status.value}]")
            if goal.evidence:
                lines.append(f"  - Last: {goal.evidence[-1]}")
        
        if self.state.blocked_paths:
            lines.append("")
            lines.append("### Blocked Paths:")
            for path in self.state.blocked_paths[-5:]:
                lines.append(f"- {path}")
        
        return "\n".join(lines)
    
    def _persist(self):
        """Salva stato su disco"""
        if not self.state:
            return
        
        filepath = self.persistence_dir / f"{self.state.mission_id}.json"
        
        data = {
            "mission_id": self.state.mission_id,
            "primary_goal": self.state.primary_goal,
            "start_time": self.state.start_time,
            "current_focus": self.state.current_focus,
            "blocked_paths": self.state.blocked_paths,
            "goals": {k: v.to_dict() for k, v in self.state.goals.items()}
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_mission(self, mission_id: str) -> bool:
        """Carica una missione salvata"""
        filepath = self.persistence_dir / f"{mission_id}.json"
        
        if not filepath.exists():
            return False
        
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        self.state = MissionState(
            mission_id=data["mission_id"],
            primary_goal=data["primary_goal"],
            start_time=data["start_time"],
            current_focus=data.get("current_focus"),
            blocked_paths=data.get("blocked_paths", [])
        )
        
        for goal_id, goal_data in data.get("goals", {}).items():
            self.state.goals[goal_id] = Goal(
                id=goal_data["id"],
                name=goal_data["name"],
                description=goal_data["description"],
                status=GoalStatus(goal_data["status"]),
                priority=GoalPriority(goal_data["priority"]),
                parent_id=goal_data.get("parent_id"),
                evidence=goal_data.get("evidence", []),
                attempts=goal_data.get("attempts", 0),
                created_at=goal_data.get("created_at", ""),
                completed_at=goal_data.get("completed_at")
            )
        
        logger.info(f"[GoalTracker] Mission loaded: {mission_id}")
        return True

# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_tracker_instance: Optional[GoalTracker] = None

def get_goal_tracker() -> GoalTracker:
    """Restituisce l'istanza singleton del GoalTracker"""
    global _tracker_instance
    if _tracker_instance is None:
        _tracker_instance = GoalTracker()
    return _tracker_instance
