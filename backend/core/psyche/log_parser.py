"""
Log Parser Module - Extracts structured events from mission logs.

Parses technical output and dialog logs to identify:
- Success events (commands completed successfully)
- Failure events (errors, timeouts, permission denied)
- Risk events (anomalies, security alerts)
- Dialog patterns (agent tone, escalation)
"""

import re
from typing import List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class EventType(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RISK = "risk"
    INFO = "info"
    HALLUCINATION = "hallucination"


class DialogTone(Enum):
    NEUTRAL = "neutral"
    CONFIDENT = "confident"
    FRUSTRATED = "frustrated"
    CAUTIOUS = "cautious"
    AGGRESSIVE = "aggressive"


@dataclass
class Event:
    """Represents a parsed event from technical logs."""
    type: EventType
    description: str
    timestamp: str = ""
    severity: float = 0.5  # 0.0 = minor, 1.0 = critical
    raw_output: str = ""


@dataclass
class DialogEvent:
    """Represents a parsed event from agent dialog."""
    agent: str
    message: str
    tone: DialogTone = DialogTone.NEUTRAL
    is_decision: bool = False
    is_tool_call: bool = False


@dataclass
class MissionAnalysis:
    """Aggregated analysis of a mission."""
    events: List[Event] = field(default_factory=list)
    dialog_events: List[DialogEvent] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    risk_count: int = 0
    hallucination_count: int = 0
    mission_score: float = 0.5  # 0.0 = disaster, 1.0 = perfect
    dominant_tone: DialogTone = DialogTone.NEUTRAL


class MissionLogParser:
    """Parses mission logs into structured events."""
    
    # Patterns for event detection - UPDATED to match real tool outputs
    SUCCESS_PATTERNS = [
        r"successfully",
        r"completed",
        r"found \d+",
        r"/tcp\s+open",  # nmap port format: 8081/tcp open
        r"open\s+tcp",   # alternative
        r"vulnerable",
        r"access granted",
        r"login success",
        r"data retrieved",
        r"FLAG\{",       # Captured flag
        r"UNLOCKED",     # Vault/system unlocked
        r"MISSION.*CLOSED",
        r"MISSION.*ACCOMPLISHED",
        r"\[\+\]",       # Common success indicator
        r"exec.?time",   # Execution completed
        r"Nmap done",    # Scan completed
        r"host.?up",     # Host responded
    ]
    
    FAILURE_PATTERNS = [
        r"error:",
        r"\[ERRORE\]",   # Italian error format
        r"failed",
        r"timeout",
        r"permission denied",
        r"connection refused",
        r"no route to host",
        r"command not found",
        r"exception",
        r"traceback",
        r"\[-\]",        # Common failure indicator
        r"INCORRECT",    # Wrong input
        r"ALARM",        # Security triggered
        r"BLOCKED",      # Action blocked
    ]
    
    RISK_PATTERNS = [
        r"alert",
        r"warning",
        r"detected",
        r"suspicious",
        r"blocked",
        r"firewall",
        r"ids",
        r"honeypot",
    ]
    
    HALLUCINATION_PATTERNS = [
        r"simulating",
        r"would have",
        r"assuming",
        r"hypothetically",
        r"in theory",
        r"expected output",
        r"predictive",
    ]
    
    def __init__(self):
        self.compiled_success = [re.compile(p, re.IGNORECASE) for p in self.SUCCESS_PATTERNS]
        self.compiled_failure = [re.compile(p, re.IGNORECASE) for p in self.FAILURE_PATTERNS]
        self.compiled_risk = [re.compile(p, re.IGNORECASE) for p in self.RISK_PATTERNS]
        self.compiled_hallucination = [re.compile(p, re.IGNORECASE) for p in self.HALLUCINATION_PATTERNS]
    
    def parse_technical_log(self, log: str) -> List[Event]:
        """Parse raw technical output into structured events."""
        events = []
        lines = log.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            event_type = EventType.INFO
            severity = 0.3
            
            # Check for hallucination (highest priority)
            for pattern in self.compiled_hallucination:
                if pattern.search(line):
                    event_type = EventType.HALLUCINATION
                    severity = 1.0
                    break
            
            # Check for failure
            if event_type == EventType.INFO:
                for pattern in self.compiled_failure:
                    if pattern.search(line):
                        event_type = EventType.FAILURE
                        severity = 0.7
                        break
            
            # Check for risk
            if event_type == EventType.INFO:
                for pattern in self.compiled_risk:
                    if pattern.search(line):
                        event_type = EventType.RISK
                        severity = 0.6
                        break
            
            # Check for success
            if event_type == EventType.INFO:
                for pattern in self.compiled_success:
                    if pattern.search(line):
                        event_type = EventType.SUCCESS
                        severity = 0.2
                        break
            
            # Only include non-INFO events (significant events)
            if event_type != EventType.INFO:
                events.append(Event(
                    type=event_type,
                    description=line[:200],  # Truncate long lines
                    timestamp=datetime.now().isoformat(),
                    severity=severity,
                    raw_output=line
                ))
        
        return events
    
    def parse_dialog_log(self, messages: List[Dict[str, Any]]) -> List[DialogEvent]:
        """Parse agent dialog messages into structured events."""
        dialog_events = []
        
        for msg in messages:
            agent = msg.get("name", msg.get("role", "unknown"))
            content = msg.get("content", "")
            
            if not content:
                continue
            
            # Detect tone
            tone = self._detect_tone(content)
            
            # Detect if it's a decision or tool call
            is_decision = any(word in content.lower() for word in 
                            ["decide", "plan", "strategy", "should", "recommend", "suggest"])
            is_tool_call = "```" in content or "execute" in content.lower() or "run" in content.lower()
            
            dialog_events.append(DialogEvent(
                agent=agent,
                message=content[:500],  # Truncate
                tone=tone,
                is_decision=is_decision,
                is_tool_call=is_tool_call
            ))
        
        return dialog_events
    
    def _detect_tone(self, text: str) -> DialogTone:
        """Detect emotional tone from text."""
        text_lower = text.lower()
        
        frustrated_words = ["failed", "error", "again", "still", "problem", "issue", "damn", "unfortunately"]
        confident_words = ["successfully", "confirmed", "verified", "done", "completed", "excellent"]
        cautious_words = ["careful", "verify", "double-check", "risk", "warning", "might", "perhaps"]
        aggressive_words = ["attack", "exploit", "breach", "force", "override", "bypass"]
        
        scores = {
            DialogTone.FRUSTRATED: sum(1 for w in frustrated_words if w in text_lower),
            DialogTone.CONFIDENT: sum(1 for w in confident_words if w in text_lower),
            DialogTone.CAUTIOUS: sum(1 for w in cautious_words if w in text_lower),
            DialogTone.AGGRESSIVE: sum(1 for w in aggressive_words if w in text_lower),
        }
        
        max_tone = max(scores, key=scores.get)
        if scores[max_tone] > 0:
            return max_tone
        return DialogTone.NEUTRAL
    
    def analyze_mission(self, technical_log: str, dialog_log: List[Dict[str, Any]]) -> MissionAnalysis:
        """Full mission analysis combining technical and dialog logs."""
        tech_events = self.parse_technical_log(technical_log)
        dialog_events = self.parse_dialog_log(dialog_log)
        
        # Count event types
        success_count = sum(1 for e in tech_events if e.type == EventType.SUCCESS)
        failure_count = sum(1 for e in tech_events if e.type == EventType.FAILURE)
        risk_count = sum(1 for e in tech_events if e.type == EventType.RISK)
        hallucination_count = sum(1 for e in tech_events if e.type == EventType.HALLUCINATION)
        
        # Calculate mission score
        total_events = len(tech_events) or 1
        score = (success_count - failure_count * 1.5 - hallucination_count * 3.0) / total_events
        score = max(0.0, min(1.0, (score + 1) / 2))  # Normalize to 0-1
        
        # Determine dominant tone
        tone_counts = {}
        for de in dialog_events:
            tone_counts[de.tone] = tone_counts.get(de.tone, 0) + 1
        dominant_tone = max(tone_counts, key=tone_counts.get) if tone_counts else DialogTone.NEUTRAL
        
        return MissionAnalysis(
            events=tech_events,
            dialog_events=dialog_events,
            success_count=success_count,
            failure_count=failure_count,
            risk_count=risk_count,
            hallucination_count=hallucination_count,
            mission_score=round(score, 2),
            dominant_tone=dominant_tone
        )


# Singleton instance
_parser = MissionLogParser()

def get_parser() -> MissionLogParser:
    return _parser
