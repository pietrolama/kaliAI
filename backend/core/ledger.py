"""
Execution Ledger - Append-only log of all tool executions and agent decisions.

The "black box" of KaliAI:
- Anti-hallucination: Only what's in the ledger happened
- Metacognition: Therapist analyzes real events
- Crash recovery: State preserved to millisecond before failure
"""

import json
import time
import uuid
import hashlib
import threading
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class ExecutionLedger:
    """
    Append-only ledger for recording all system events.
    
    Event Types:
    - TOOL_CALL: Tool invocation (before execution)
    - TOOL_OUTPUT: Tool result (after execution)
    - CHAT: Agent message in swarm
    - DECISION: Strategic decision by an agent
    - ERROR: System or execution error
    """
    
    def __init__(self, log_dir: str = "data/ledger"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Session-based file to avoid lock contention
        self._session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_file = self.log_dir / f"ledger_{self._session_id}.jsonl"
        
        # Thread safety for concurrent writes
        self._lock = threading.Lock()
        
        # In-memory cache for quick access (last N events)
        self._cache: List[Dict] = []
        self._cache_limit = 500
        
        # Current run_id (set per mission)
        self._current_run_id: Optional[str] = None
    
    def start_run(self, objective: str = "") -> str:
        """Start a new run/mission and return its ID."""
        self._current_run_id = f"run_{uuid.uuid4().hex[:8]}"
        self.record("System", "RUN_START", {
            "objective": objective[:500] if objective else "",
            "run_id": self._current_run_id
        })
        return self._current_run_id
    
    def end_run(self, status: str = "COMPLETED"):
        """End the current run."""
        if self._current_run_id:
            self.record("System", "RUN_END", {
                "status": status,
                "run_id": self._current_run_id
            })
        self._current_run_id = None
    
    def record(
        self, 
        actor: str, 
        event_type: str, 
        data: Dict[str, Any], 
        correlation_id: Optional[str] = None
    ) -> str:
        """
        Record an event to the ledger (atomic, append-only).
        
        Args:
            actor: Who triggered the event (agent name or "System")
            event_type: TOOL_CALL, TOOL_OUTPUT, CHAT, DECISION, ERROR
            data: Event-specific data (command, output, content, etc.)
            correlation_id: Links this event to a previous event (e.g., output to call)
            
        Returns:
            event_id: Unique identifier for this event
        """
        event_id = uuid.uuid4().hex[:12]
        timestamp = time.time()
        
        entry = {
            "event_id": event_id,
            "timestamp": timestamp,
            "iso_time": datetime.fromtimestamp(timestamp).isoformat(),
            "run_id": self._current_run_id,
            "actor": actor,
            "type": event_type,
            "correlation_id": correlation_id,
            **data
        }
        
        # Compute hash of content for verification
        if "output" in data or "content" in data:
            content = data.get("output", data.get("content", ""))
            if content:
                entry["content_hash"] = hashlib.sha256(
                    str(content).encode()
                ).hexdigest()[:16]
        
        with self._lock:
            # Atomic append to file
            with open(self.current_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            
            # Update cache
            self._cache.append(entry)
            if len(self._cache) > self._cache_limit:
                self._cache = self._cache[-self._cache_limit:]
        
        return event_id
    
    def get_recent_events(
        self, 
        run_id: Optional[str] = None, 
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Get recent events from cache, optionally filtered.
        
        Args:
            run_id: Filter by run_id (None = current run)
            event_type: Filter by event type
            limit: Maximum events to return
        """
        target_run = run_id or self._current_run_id
        
        with self._lock:
            events = self._cache.copy()
        
        # Filter
        if target_run:
            events = [e for e in events if e.get("run_id") == target_run]
        if event_type:
            events = [e for e in events if e.get("type") == event_type]
        
        return events[-limit:]
    
    def get_current_session_events(self) -> List[Dict]:
        """
        Get all events from the current session/run.
        Convenience method for post-mission analysis.
        """
        return self.get_recent_events(run_id=self._current_run_id, limit=500)
    
    def get_tool_events(self, run_id: Optional[str] = None) -> List[Dict]:
        """Get all TOOL_CALL and TOOL_OUTPUT events for analysis."""
        events = self.get_recent_events(run_id=run_id, limit=500)
        return [e for e in events if e.get("type") in ("TOOL_CALL", "TOOL_OUTPUT")]
    
    def get_full_history(self, run_id: Optional[str] = None) -> List[Dict]:
        """
        Read full history from disk (for post-mortem analysis).
        More expensive than get_recent_events.
        """
        events = []
        
        # Read all ledger files
        for ledger_file in sorted(self.log_dir.glob("ledger_*.jsonl")):
            try:
                with open(ledger_file, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            try:
                                entry = json.loads(line)
                                if run_id is None or entry.get("run_id") == run_id:
                                    events.append(entry)
                            except json.JSONDecodeError:
                                continue
            except Exception:
                continue
        
        return events
    
    def compute_metrics(self, run_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Compute metrics for Reflector/Metacognition.
        
        Returns:
            success_rate: Tool execution success rate
            tool_entropy: Variety of tools used
            risk_score: Number of risky commands
            chat_to_action_ratio: Talk vs Do ratio
        """
        events = self.get_recent_events(run_id=run_id, limit=500)
        
        tool_calls = [e for e in events if e.get("type") == "TOOL_CALL"]
        tool_outputs = [e for e in events if e.get("type") == "TOOL_OUTPUT"]
        chat_events = [e for e in events if e.get("type") == "CHAT"]
        
        # Success rate
        successes = sum(1 for e in tool_outputs if e.get("status") == "SUCCESS")
        total_outputs = len(tool_outputs) or 1
        success_rate = successes / total_outputs
        
        # Tool entropy (variety)
        tools_used = set(e.get("tool", "unknown") for e in tool_calls)
        tool_entropy = len(tools_used) / max(len(tool_calls), 1)
        
        # Risk score (sudo, rm, etc.)
        risky_keywords = ["sudo", "rm -rf", "chmod 777", "dd if=", "> /dev/"]
        risk_count = sum(
            1 for e in tool_calls 
            if any(kw in str(e.get("command", "")).lower() for kw in risky_keywords)
        )
        risk_score = risk_count / max(len(tool_calls), 1)
        
        # Chat to action ratio
        chat_to_action = len(chat_events) / max(len(tool_calls), 1)
        
        return {
            "success_rate": round(success_rate, 2),
            "tool_entropy": round(tool_entropy, 2),
            "risk_score": round(risk_score, 2),
            "chat_to_action_ratio": round(chat_to_action, 2),
            "total_tool_calls": len(tool_calls),
            "total_chat_messages": len(chat_events),
            "tools_used": list(tools_used)
        }


# Global singleton instance
_ledger: Optional[ExecutionLedger] = None
_ledger_lock = threading.Lock()


def get_ledger() -> ExecutionLedger:
    """Get or create the global ledger instance."""
    global _ledger
    with _ledger_lock:
        if _ledger is None:
            _ledger = ExecutionLedger()
        return _ledger


# Convenience functions
def record_tool_call(actor: str, tool: str, command: str, **kwargs) -> str:
    """Record a tool call event."""
    return get_ledger().record(actor, "TOOL_CALL", {
        "tool": tool,
        "command": command[:2000],  # Truncate very long commands
        **kwargs
    })


def record_tool_output(
    correlation_id: str, 
    output: str, 
    status: str = "SUCCESS",
    return_code: int = 0,
    **kwargs
) -> str:
    """Record a tool output event."""
    return get_ledger().record("System", "TOOL_OUTPUT", {
        "output_preview": output[:1000] if output else "",
        "output_length": len(output) if output else 0,
        "status": status,
        "return_code": return_code,
        **kwargs
    }, correlation_id=correlation_id)


def record_chat(actor: str, content: str, **kwargs) -> str:
    """Record a chat message event."""
    return get_ledger().record(actor, "CHAT", {
        "content": content[:2000] if content else "",
        **kwargs
    })


def record_error(actor: str, error: str, **kwargs) -> str:
    """Record an error event."""
    return get_ledger().record(actor, "ERROR", {
        "error": str(error)[:1000],
        **kwargs
    })
