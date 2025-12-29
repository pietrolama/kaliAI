#!/usr/bin/env python3
"""
Strategic Memory - Cross-Session Persistence
🧠 Ricorda tecniche, exploit, e strategie vincenti tra le sessioni.

Funzionalità:
- Memorizza tecniche usate e loro successo/fallimento
- Recall di strategie simili per target simili
- Learning from failures
- MITRE ATT&CK alignment
"""

import os
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from contextlib import contextmanager

logger = logging.getLogger('StrategicMemory')

# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class TechniqueResult:
    """Risultato di una tecnica usata"""
    technique_id: str
    technique_name: str
    mitre_id: str
    target_service: str
    target_port: int
    success: bool
    output_summary: str
    timestamp: str
    context: Dict[str, Any] = None
    
    def to_dict(self) -> dict:
        return asdict(self)

@dataclass
class AttackStrategy:
    """Strategia d'attacco memorizzata"""
    strategy_id: str
    name: str
    target_profile: str  # es: "linux_ssh_22", "windows_smb_445"
    steps: List[str]
    success_rate: float
    last_used: str
    times_used: int
    
@dataclass
class LearnedLesson:
    """Lezione appresa da un fallimento"""
    lesson_id: str
    original_attempt: str
    failure_reason: str
    learned_insight: str
    alternative_approach: str
    timestamp: str

# ============================================================================
# STRATEGIC MEMORY CLASS
# ============================================================================

class StrategicMemory:
    """
    Memoria persistente per strategie e tecniche.
    
    Uso:
        memory = StrategicMemory()
        memory.remember_technique("ssh_brute", "Hydra SSH", "T1110", ...)
        strategies = memory.recall_for_target("linux", 22, "ssh")
    """
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or os.path.expanduser("~/kaliAI/data/strategic_memory.db")
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    @contextmanager
    def _get_connection(self):
        """Context manager per connessione DB"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()
    
    def _init_db(self):
        """Inizializza schema database"""
        with self._get_connection() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS techniques (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    technique_id TEXT NOT NULL,
                    technique_name TEXT NOT NULL,
                    mitre_id TEXT,
                    target_service TEXT,
                    target_port INTEGER,
                    success INTEGER NOT NULL,
                    output_summary TEXT,
                    context_json TEXT,
                    timestamp TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS strategies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    strategy_id TEXT UNIQUE NOT NULL,
                    name TEXT NOT NULL,
                    target_profile TEXT NOT NULL,
                    steps_json TEXT NOT NULL,
                    success_rate REAL DEFAULT 0.0,
                    last_used TEXT,
                    times_used INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_id TEXT UNIQUE NOT NULL,
                    original_attempt TEXT NOT NULL,
                    failure_reason TEXT NOT NULL,
                    learned_insight TEXT NOT NULL,
                    alternative_approach TEXT,
                    timestamp TEXT NOT NULL
                );
                
                CREATE TABLE IF NOT EXISTS target_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    target_ip TEXT NOT NULL,
                    os_guess TEXT,
                    open_ports TEXT,
                    services_json TEXT,
                    last_seen TEXT,
                    notes TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_techniques_service 
                    ON techniques(target_service, target_port);
                CREATE INDEX IF NOT EXISTS idx_strategies_profile 
                    ON strategies(target_profile);
            """)
        logger.info(f"[StrategicMemory] Database initialized: {self.db_path}")
    
    # ========================================================================
    # TECHNIQUE MEMORY
    # ========================================================================
    
    def remember_technique(
        self,
        technique_id: str,
        technique_name: str,
        mitre_id: str,
        target_service: str,
        target_port: int,
        success: bool,
        output_summary: str = "",
        context: Dict = None
    ) -> int:
        """
        Memorizza l'uso di una tecnica.
        
        Returns:
            ID del record inserito
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO techniques 
                (technique_id, technique_name, mitre_id, target_service, 
                 target_port, success, output_summary, context_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                technique_id,
                technique_name,
                mitre_id,
                target_service,
                target_port,
                1 if success else 0,
                output_summary[:500],  # Limita lunghezza
                json.dumps(context) if context else None,
                datetime.now().isoformat()
            ))
            
            record_id = cursor.lastrowid
            logger.debug(f"[StrategicMemory] Technique recorded: {technique_name} -> {'SUCCESS' if success else 'FAIL'}")
            return record_id
    
    def get_success_rate(self, technique_id: str) -> Tuple[float, int]:
        """
        Calcola success rate per una tecnica.
        
        Returns:
            Tuple (success_rate, total_attempts)
        """
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(success) as successes
                FROM techniques 
                WHERE technique_id = ?
            """, (technique_id,)).fetchone()
            
            if row['total'] == 0:
                return (0.0, 0)
            
            return (row['successes'] / row['total'], row['total'])
    
    def get_winning_techniques(self, target_service: str, limit: int = 5) -> List[dict]:
        """
        Ritorna le tecniche più efficaci per un servizio.
        
        Args:
            target_service: Nome del servizio (es: "ssh", "http", "smb")
            limit: Numero massimo di risultati
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT 
                    technique_id,
                    technique_name,
                    mitre_id,
                    COUNT(*) as attempts,
                    SUM(success) as successes,
                    CAST(SUM(success) AS FLOAT) / COUNT(*) as success_rate
                FROM techniques
                WHERE target_service LIKE ?
                GROUP BY technique_id
                HAVING attempts >= 1
                ORDER BY success_rate DESC, successes DESC
                LIMIT ?
            """, (f"%{target_service}%", limit)).fetchall()
            
            return [dict(row) for row in rows]
    
    # ========================================================================
    # STRATEGY MEMORY
    # ========================================================================
    
    def save_strategy(
        self,
        strategy_id: str,
        name: str,
        target_profile: str,
        steps: List[str],
        success: bool
    ):
        """
        Salva o aggiorna una strategia.
        
        Args:
            strategy_id: ID univoco
            name: Nome descrittivo
            target_profile: Profilo target (es: "linux_ssh_22")
            steps: Lista passi della strategia
            success: Se l'ultimo uso ha avuto successo
        """
        with self._get_connection() as conn:
            # Check se esiste
            existing = conn.execute(
                "SELECT * FROM strategies WHERE strategy_id = ?",
                (strategy_id,)
            ).fetchone()
            
            if existing:
                # Aggiorna
                new_times = existing['times_used'] + 1
                total_success = existing['success_rate'] * existing['times_used']
                new_rate = (total_success + (1 if success else 0)) / new_times
                
                conn.execute("""
                    UPDATE strategies 
                    SET success_rate = ?, times_used = ?, last_used = ?
                    WHERE strategy_id = ?
                """, (new_rate, new_times, datetime.now().isoformat(), strategy_id))
            else:
                # Inserisci
                conn.execute("""
                    INSERT INTO strategies 
                    (strategy_id, name, target_profile, steps_json, 
                     success_rate, last_used, times_used)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    strategy_id,
                    name,
                    target_profile,
                    json.dumps(steps),
                    1.0 if success else 0.0,
                    datetime.now().isoformat(),
                    1
                ))
        
        logger.info(f"[StrategicMemory] Strategy saved: {name}")
    
    def recall_strategies(self, target_profile: str, min_success: float = 0.5) -> List[dict]:
        """
        Richiama strategie per un profilo target.
        
        Args:
            target_profile: Profilo (es: "linux_ssh", "windows_smb")
            min_success: Success rate minimo
        """
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM strategies
                WHERE target_profile LIKE ?
                AND success_rate >= ?
                ORDER BY success_rate DESC, times_used DESC
            """, (f"%{target_profile}%", min_success)).fetchall()
            
            result = []
            for row in rows:
                d = dict(row)
                d['steps'] = json.loads(d['steps_json'])
                del d['steps_json']
                result.append(d)
            
            return result
    
    # ========================================================================
    # LESSONS LEARNED
    # ========================================================================
    
    def learn_from_failure(
        self,
        original_attempt: str,
        failure_reason: str,
        learned_insight: str,
        alternative_approach: str = ""
    ) -> str:
        """
        Registra una lezione appresa da un fallimento.
        
        Returns:
            lesson_id
        """
        lesson_id = f"lesson_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO lessons
                (lesson_id, original_attempt, failure_reason, 
                 learned_insight, alternative_approach, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                lesson_id,
                original_attempt,
                failure_reason,
                learned_insight,
                alternative_approach,
                datetime.now().isoformat()
            ))
        
        logger.info(f"[StrategicMemory] Lesson learned: {learned_insight[:50]}...")
        return lesson_id
    
    def recall_lessons(self, keyword: str = None, limit: int = 10) -> List[dict]:
        """Richiama lezioni apprese, opzionalmente filtrate"""
        with self._get_connection() as conn:
            if keyword:
                rows = conn.execute("""
                    SELECT * FROM lessons
                    WHERE original_attempt LIKE ? 
                       OR failure_reason LIKE ?
                       OR learned_insight LIKE ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (f"%{keyword}%", f"%{keyword}%", f"%{keyword}%", limit)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT * FROM lessons
                    ORDER BY timestamp DESC
                    LIMIT ?
                """, (limit,)).fetchall()
            
            return [dict(row) for row in rows]
    
    # ========================================================================
    # TARGET PROFILES
    # ========================================================================
    
    def remember_target(
        self,
        target_ip: str,
        os_guess: str = None,
        open_ports: List[int] = None,
        services: Dict[int, str] = None,
        notes: str = None
    ):
        """Memorizza info su un target"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO target_profiles
                (target_ip, os_guess, open_ports, services_json, last_seen, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                target_ip,
                os_guess,
                json.dumps(open_ports) if open_ports else None,
                json.dumps(services) if services else None,
                datetime.now().isoformat(),
                notes
            ))
    
    def recall_target(self, target_ip: str) -> Optional[dict]:
        """Richiama info su un target"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM target_profiles WHERE target_ip = ?",
                (target_ip,)
            ).fetchone()
            
            if not row:
                return None
            
            d = dict(row)
            d['open_ports'] = json.loads(d['open_ports']) if d['open_ports'] else []
            d['services_json'] = json.loads(d['services_json']) if d['services_json'] else {}
            return d
    
    # ========================================================================
    # AGENT INTEGRATION
    # ========================================================================
    
    def get_context_for_target(self, target_service: str, target_port: int = None) -> str:
        """
        Genera contesto strategico per gli agenti.
        
        Returns:
            Stringa formattata per injection nel prompt
        """
        lines = ["## 🧠 Strategic Memory Context\n"]
        
        # Tecniche vincenti
        winning = self.get_winning_techniques(target_service)
        if winning:
            lines.append("### Winning Techniques:")
            for tech in winning[:3]:
                rate = tech['success_rate'] * 100
                lines.append(f"- **{tech['technique_name']}** ({rate:.0f}% success, {tech['attempts']} attempts)")
        
        # Strategie esistenti
        profile = f"*_{target_service}"
        if target_port:
            profile = f"*_{target_service}_{target_port}"
        
        strategies = self.recall_strategies(profile)
        if strategies:
            lines.append("\n### Known Strategies:")
            for strat in strategies[:2]:
                lines.append(f"- **{strat['name']}** ({strat['success_rate']*100:.0f}% success)")
                lines.append(f"  Steps: {' → '.join(strat['steps'][:4])}")
        
        # Lezioni recenti
        lessons = self.recall_lessons(target_service, limit=3)
        if lessons:
            lines.append("\n### Lessons Learned:")
            for lesson in lessons:
                lines.append(f"- ⚠️ {lesson['learned_insight']}")
        
        return "\n".join(lines) if len(lines) > 1 else ""
    
    def get_stats(self) -> dict:
        """Statistiche della memoria"""
        with self._get_connection() as conn:
            stats = {
                "techniques_recorded": conn.execute("SELECT COUNT(*) FROM techniques").fetchone()[0],
                "strategies_saved": conn.execute("SELECT COUNT(*) FROM strategies").fetchone()[0],
                "lessons_learned": conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0],
                "targets_profiled": conn.execute("SELECT COUNT(*) FROM target_profiles").fetchone()[0],
            }
            
            # Success rate globale
            row = conn.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(success) as successes
                FROM techniques
            """).fetchone()
            
            if row['total'] > 0:
                stats['global_success_rate'] = row['successes'] / row['total']
            else:
                stats['global_success_rate'] = 0.0
            
            return stats

# ============================================================================
# SINGLETON
# ============================================================================

_memory_instance: Optional[StrategicMemory] = None

def get_strategic_memory() -> StrategicMemory:
    """Restituisce istanza singleton"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = StrategicMemory()
    return _memory_instance
