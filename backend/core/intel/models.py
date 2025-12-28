"""
Threat Intelligence Data Models

Unified data structures for vulnerability intelligence.
All sources (CISA, NVD, ExploitDB) normalize to VulnArtifact.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum


class VulnStatus(Enum):
    """Vulnerability triage status."""
    NEW = "NEW"
    TRIAGED = "TRIAGED"
    IGNORED = "IGNORED"
    EXPLOITED = "EXPLOITED"


@dataclass
class VulnArtifact:
    """
    Unified vulnerability artifact.
    
    Standard data model for any vulnerability in the system.
    All intel sources normalize to this format.
    """
    
    # Core identification
    cve_id: str
    title: str
    description: str
    
    # Risk assessment
    risk_score: float = 0.0  # 0-100 scale
    
    # Source tracking
    sources: Dict[str, Any] = field(default_factory=dict)
    # Example: {"cisa_kev": True, "nvd_severity": "HIGH", "exploitdb": [12345]}
    
    # Technical details
    technical_data: Dict[str, Any] = field(default_factory=dict)
    # Example: {"affected_product": "Apache", "vendor": "Apache Foundation", 
    #           "vector": "NETWORK", "cwe": "CWE-79"}
    
    # Status tracking
    status: VulnStatus = VulnStatus.NEW
    
    # Timestamps
    timestamp: datetime = field(default_factory=datetime.now)
    date_added: Optional[str] = None  # Original date from source
    due_date: Optional[str] = None    # CISA remediation deadline
    
    # Exploitation evidence
    known_ransomware: bool = False
    exploitation_activity: str = ""
    
    def calculate_priority(self) -> float:
        """
        Calculate priority score based on intel sources.
        
        Rules:
        - CISA KEV listed = 100 (CRITICAL - actively exploited)
        - Known ransomware = +20
        - NVD severity HIGH/CRITICAL = +30
        - Recent (< 30 days) = +10
        """
        score = self.risk_score
        
        # CISA KEV is automatic critical
        if self.sources.get("cisa_kev"):
            score = 100.0
        
        # Ransomware bonus
        if self.known_ransomware:
            score = min(100.0, score + 20)
        
        # NVD severity
        nvd_sev = self.sources.get("nvd_severity", "").upper()
        if nvd_sev == "CRITICAL":
            score = min(100.0, score + 40)
        elif nvd_sev == "HIGH":
            score = min(100.0, score + 30)
        elif nvd_sev == "MEDIUM":
            score = min(100.0, score + 15)
        
        # Recency bonus
        if self.date_added:
            try:
                added = datetime.fromisoformat(self.date_added.replace("Z", "+00:00"))
                days_old = (datetime.now(added.tzinfo) - added).days
                if days_old < 30:
                    score = min(100.0, score + 10)
            except (ValueError, TypeError):
                pass
        
        self.risk_score = score
        return score
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        data = asdict(self)
        data["status"] = self.status.value
        data["timestamp"] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VulnArtifact":
        """Deserialize from dictionary."""
        # Handle status enum
        if isinstance(data.get("status"), str):
            data["status"] = VulnStatus(data["status"])
        
        # Handle timestamp
        if isinstance(data.get("timestamp"), str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        return cls(**data)
    
    def __str__(self) -> str:
        return f"[{self.cve_id}] {self.title} (Risk: {self.risk_score:.0f})"


@dataclass
class IntelReport:
    """Summary of an intelligence gathering cycle."""
    
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    total_fetched: int = 0
    new_count: int = 0
    updated_count: int = 0
    critical_count: int = 0
    errors: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "total_fetched": self.total_fetched,
            "new_count": self.new_count,
            "updated_count": self.updated_count,
            "critical_count": self.critical_count,
            "errors": self.errors
        }
