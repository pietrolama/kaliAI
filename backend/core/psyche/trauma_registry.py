"""
Trauma Registry - Persistent tracking of mission failures.

Records "traumas" (failed operations) that become training scenarios.
The Therapist writes here, the DreamArchitect reads to generate training.
"""

import os
import json
import uuid
import logging
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from pathlib import Path
from enum import Enum

logger = logging.getLogger('TraumaRegistry')


class TraumaStatus(Enum):
    UNRESOLVED = "UNRESOLVED"
    IN_THERAPY = "IN_THERAPY"
    HEALED = "HEALED"


@dataclass
class Trauma:
    """
    A recorded failure that requires training to overcome.
    """
    trauma_id: str
    description: str
    severity: float  # 0.0-1.0 (maps to cortisol impact)
    status: TraumaStatus = TraumaStatus.UNRESOLVED
    technical_context: Dict[str, Any] = field(default_factory=dict)
    # Example: {"protocol": "TCP", "port": 50100, "error": "timeout", "command": "nc -v ..."}
    mission_id: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    healed_at: Optional[str] = None
    healing_attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Trauma":
        if isinstance(data.get("status"), str):
            data["status"] = TraumaStatus(data["status"])
        return cls(**data)
    
    def __str__(self) -> str:
        return f"[{self.trauma_id}] {self.description} (Severity: {self.severity:.0%})"


# Storage path
TRAUMA_DIR = Path("data/traumas")
TRAUMA_DIR.mkdir(parents=True, exist_ok=True)
TRAUMA_FILE = TRAUMA_DIR / "traumas.jsonl"


class TraumaRegistry:
    """
    Persistent registry of mission failures (traumas).
    
    Used by:
    - Therapist: Records new traumas on mission failure
    - DreamArchitect: Reads traumas to generate training scenarios
    - Arena: Marks traumas as healed after successful training
    """
    
    def __init__(self):
        self._traumas: Dict[str, Trauma] = {}
        self._load()
    
    def _load(self):
        """Load existing traumas from disk."""
        if TRAUMA_FILE.exists():
            try:
                with open(TRAUMA_FILE, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                data = json.loads(line)
                                trauma = Trauma.from_dict(data)
                                self._traumas[trauma.trauma_id] = trauma
                            except (json.JSONDecodeError, KeyError, TypeError) as e:
                                logger.warning(f"Skipping invalid trauma entry: {e}")
                logger.info(f"Loaded {len(self._traumas)} traumas from registry")
            except Exception as e:
                logger.error(f"Failed to load trauma registry: {e}")
    
    def _save(self, trauma: Trauma):
        """Append trauma to JSONL file."""
        with open(TRAUMA_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(trauma.to_dict(), ensure_ascii=False) + "\n")
    
    def _rewrite_all(self):
        """Rewrite entire file (for updates/deletes)."""
        with open(TRAUMA_FILE, "w", encoding="utf-8") as f:
            for trauma in self._traumas.values():
                f.write(json.dumps(trauma.to_dict(), ensure_ascii=False) + "\n")
    
    def record_trauma(
        self,
        description: str,
        severity: float,
        technical_context: Dict[str, Any],
        mission_id: Optional[str] = None
    ) -> Trauma:
        """
        Record a new trauma from a failed mission.
        
        Called by Therapist when mission score < 0.3.
        
        Args:
            description: Human-readable failure description
            severity: 0.0-1.0 impact level
            technical_context: {protocol, port, error, command, etc.}
            mission_id: Optional link to mission
            
        Returns:
            Created Trauma object
        """
        # Generate ID from context
        context_hash = hash(frozenset(str(v) for v in technical_context.values()))
        trauma_id = f"T-{abs(context_hash) % 100000:05d}-{description[:10].upper().replace(' ', '_')}"
        
        # Check for duplicate
        if trauma_id in self._traumas:
            existing = self._traumas[trauma_id]
            if existing.status == TraumaStatus.UNRESOLVED:
                logger.info(f"Trauma already exists: {trauma_id}")
                return existing
        
        trauma = Trauma(
            trauma_id=trauma_id,
            description=description,
            severity=min(1.0, max(0.0, severity)),
            technical_context=technical_context,
            mission_id=mission_id
        )
        
        self._traumas[trauma_id] = trauma
        self._save(trauma)
        
        logger.info(f"[TRAUMA RECORDED] {trauma}")
        return trauma
    
    def get_unresolved(self) -> List[Trauma]:
        """Get all unresolved traumas for training."""
        return [
            t for t in self._traumas.values() 
            if t.status == TraumaStatus.UNRESOLVED
        ]
    
    def get_trauma(self, trauma_id: str) -> Optional[Trauma]:
        """Get specific trauma by ID."""
        return self._traumas.get(trauma_id)
    
    def start_therapy(self, trauma_id: str) -> bool:
        """Mark trauma as being treated."""
        if trauma_id not in self._traumas:
            return False
        
        trauma = self._traumas[trauma_id]
        trauma.status = TraumaStatus.IN_THERAPY
        trauma.healing_attempts += 1
        self._rewrite_all()
        
        logger.info(f"[THERAPY STARTED] {trauma_id} (Attempt #{trauma.healing_attempts})")
        return True
    
    def heal_trauma(self, trauma_id: str) -> bool:
        """Mark trauma as healed after successful training."""
        if trauma_id not in self._traumas:
            return False
        
        trauma = self._traumas[trauma_id]
        trauma.status = TraumaStatus.HEALED
        trauma.healed_at = datetime.now().isoformat()
        self._rewrite_all()
        
        logger.info(f"[TRAUMA HEALED] {trauma_id} 🩹")
        return True
    
    def fail_therapy(self, trauma_id: str) -> bool:
        """Mark therapy as failed, return to unresolved."""
        if trauma_id not in self._traumas:
            return False
        
        trauma = self._traumas[trauma_id]
        trauma.status = TraumaStatus.UNRESOLVED
        self._rewrite_all()
        
        logger.info(f"[THERAPY FAILED] {trauma_id} - needs more training")
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        all_traumas = list(self._traumas.values())
        return {
            "total": len(all_traumas),
            "unresolved": sum(1 for t in all_traumas if t.status == TraumaStatus.UNRESOLVED),
            "in_therapy": sum(1 for t in all_traumas if t.status == TraumaStatus.IN_THERAPY),
            "healed": sum(1 for t in all_traumas if t.status == TraumaStatus.HEALED),
            "avg_severity": sum(t.severity for t in all_traumas) / max(len(all_traumas), 1)
        }
    
    def to_list(self) -> List[Dict[str, Any]]:
        """Export all traumas as list of dicts."""
        return [t.to_dict() for t in self._traumas.values()]


# Singleton instance
_registry: Optional[TraumaRegistry] = None


def get_trauma_registry() -> TraumaRegistry:
    """Get or create the global trauma registry."""
    global _registry
    if _registry is None:
        _registry = TraumaRegistry()
    return _registry


# Convenience functions
def record_trauma(
    description: str,
    severity: float,
    technical_context: Dict[str, Any],
    mission_id: Optional[str] = None
) -> Trauma:
    """Record a new trauma."""
    return get_trauma_registry().record_trauma(
        description, severity, technical_context, mission_id
    )
