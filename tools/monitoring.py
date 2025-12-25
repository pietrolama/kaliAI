import time
import logging
from typing import Dict, Any, List
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger('Monitoring')


class MetricsCollector:
    """Raccolta metriche per monitoraggio performance."""
    
    def __init__(self):
        self.metrics = {
            "llm_calls": 0,
            "llm_errors": 0,
            "command_executions": 0,
            "command_errors": 0,
            "security_blocks": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_llm_time": 0.0,
            "total_execution_time": 0.0,
        }
        
        # Tracciamento dettagliato
        self.llm_call_history: List[Dict] = []
        self.command_history: List[Dict] = []
        self.error_history: List[Dict] = []
        
        # Metriche per modello
        self.model_metrics = defaultdict(lambda: {
            "calls": 0,
            "errors": 0,
            "total_time": 0.0,
            "avg_time": 0.0
        })
    
    def track_llm_call(
        self, 
        duration: float, 
        success: bool, 
        model: str = "unknown",
        tokens: int = 0
    ):
        """Traccia chiamata LLM."""
        self.metrics["llm_calls"] += 1
        self.metrics["total_llm_time"] += duration
        
        if not success:
            self.metrics["llm_errors"] += 1
        
        # Metriche per modello
        model_stats = self.model_metrics[model]
        model_stats["calls"] += 1
        model_stats["total_time"] += duration
        model_stats["avg_time"] = model_stats["total_time"] / model_stats["calls"]
        
        if not success:
            model_stats["errors"] += 1
        
        # History
        self.llm_call_history.append({
            "timestamp": datetime.now().isoformat(),
            "duration": duration,
            "success": success,
            "model": model,
            "tokens": tokens
        })
        
        # Mantieni solo ultimi 1000
        if len(self.llm_call_history) > 1000:
            self.llm_call_history.pop(0)
    
    def track_command_execution(
        self, 
        command: str, 
        duration: float, 
        success: bool,
        output_length: int = 0
    ):
        """Traccia esecuzione comando."""
        self.metrics["command_executions"] += 1
        self.metrics["total_execution_time"] += duration
        
        if not success:
            self.metrics["command_errors"] += 1
        
        # History
        self.command_history.append({
            "timestamp": datetime.now().isoformat(),
            "command": command[:100],  # Tronca comando lungo
            "duration": duration,
            "success": success,
            "output_length": output_length
        })
        
        # Mantieni solo ultimi 1000
        if len(self.command_history) > 1000:
            self.command_history.pop(0)
    
    def track_security_block(self, command: str, reason: str):
        """Traccia blocco sicurezza."""
        self.metrics["security_blocks"] += 1
        
        self.error_history.append({
            "timestamp": datetime.now().isoformat(),
            "type": "security_block",
            "command": command[:100],
            "reason": reason
        })
    
    def track_cache(self, hit: bool):
        """Traccia hit/miss cache."""
        if hit:
            self.metrics["cache_hits"] += 1
        else:
            self.metrics["cache_misses"] += 1
    
    def get_metrics(self) -> Dict[str, Any]:
        """Ritorna metriche aggregate."""
        total_calls = self.metrics["llm_calls"]
        total_commands = self.metrics["command_executions"]
        
        avg_llm_time = (
            self.metrics["total_llm_time"] / total_calls 
            if total_calls > 0 else 0
        )
        
        avg_exec_time = (
            self.metrics["total_execution_time"] / total_commands 
            if total_commands > 0 else 0
        )
        
        llm_error_rate = (
            self.metrics["llm_errors"] / total_calls * 100 
            if total_calls > 0 else 0
        )
        
        cmd_error_rate = (
            self.metrics["command_errors"] / total_commands * 100 
            if total_commands > 0 else 0
        )
        
        cache_total = self.metrics["cache_hits"] + self.metrics["cache_misses"]
        cache_hit_rate = (
            self.metrics["cache_hits"] / cache_total * 100
            if cache_total > 0 else 0
        )
        
        return {
            "llm": {
                "total_calls": total_calls,
                "errors": self.metrics["llm_errors"],
                "error_rate": f"{llm_error_rate:.2f}%",
                "avg_response_time": f"{avg_llm_time:.3f}s",
                "total_time": f"{self.metrics['total_llm_time']:.2f}s"
            },
            "commands": {
                "total_executions": total_commands,
                "errors": self.metrics["command_errors"],
                "error_rate": f"{cmd_error_rate:.2f}%",
                "avg_execution_time": f"{avg_exec_time:.3f}s",
                "total_time": f"{self.metrics['total_execution_time']:.2f}s"
            },
            "security": {
                "blocks": self.metrics["security_blocks"]
            },
            "cache": {
                "hits": self.metrics["cache_hits"],
                "misses": self.metrics["cache_misses"],
                "hit_rate": f"{cache_hit_rate:.2f}%"
            }
        }
    
    def get_model_metrics(self) -> Dict[str, Any]:
        """Ritorna metriche per modello."""
        return dict(self.model_metrics)
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """Ritorna errori recenti."""
        return self.error_history[-limit:]
    
    def get_recent_commands(self, limit: int = 10) -> List[Dict]:
        """Ritorna comandi recenti."""
        return self.command_history[-limit:]
    
    def reset(self):
        """Reset metriche."""
        self.metrics = {
            "llm_calls": 0,
            "llm_errors": 0,
            "command_executions": 0,
            "command_errors": 0,
            "security_blocks": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_llm_time": 0.0,
            "total_execution_time": 0.0,
        }
        self.llm_call_history.clear()
        self.command_history.clear()
        self.error_history.clear()
        self.model_metrics.clear()
        logger.info("Metriche resettate")


class PerformanceMonitor:
    """Monitor performance con context manager."""
    
    def __init__(self, collector: MetricsCollector, operation_type: str):
        self.collector = collector
        self.operation_type = operation_type
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        
        if self.operation_type == "llm":
            self.collector.track_llm_call(duration, success)
        elif self.operation_type == "command":
            self.collector.track_command_execution("", duration, success)
        
        return False  # Non sopprime eccezioni


# Istanza globale
metrics_collector = MetricsCollector()


def get_system_stats() -> Dict[str, Any]:
    """Ritorna statistiche di sistema."""
    import psutil
    
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.1),
        "memory_percent": psutil.virtual_memory().percent,
        "disk_percent": psutil.disk_usage('/').percent,
        "process_count": len(psutil.pids())
    }

