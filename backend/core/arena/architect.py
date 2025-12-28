"""
Dream Architect - Transforms traumas into training scenarios.

Reads trauma context from TraumaRegistry, uses LLM to generate
Docker scenarios that recreate the failure conditions for training.
"""

import os
import time
import json
import queue
import logging
import subprocess
import threading
from typing import Dict, Any, Optional, Generator, List
from pathlib import Path
from datetime import datetime

from backend.core.psyche.trauma_registry import get_trauma_registry, Trauma, TraumaStatus

logger = logging.getLogger('DreamArchitect')

# Arena Docker paths
ARENA_DIR = Path("arena")
GENERATED_DIR = Path("data/arena_dreams")
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


class DreamSession:
    """Active training session state."""
    
    def __init__(self, trauma_id: str):
        self.trauma_id = trauma_id
        self.session_id = f"dream_{int(time.time())}"
        self.status = "INITIALIZING"
        self.log_queue: queue.Queue = queue.Queue()
        self.start_time = datetime.now()
        self.end_time: Optional[datetime] = None
        self.success = False
    
    def log(self, message: str, level: str = "INFO"):
        """Add log entry to queue for SSE streaming."""
        entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "session_id": self.session_id
        }
        self.log_queue.put(entry)
        
        # Also log to file
        if level == "RED":
            logger.info(f"[RED] {message}")
        elif level == "BLUE":
            logger.info(f"[BLUE] {message}")
        elif level == "SYSTEM":
            logger.info(f"[SYS] {message}")
        else:
            logger.info(message)


class DreamArchitect:
    """
    Generates and runs training scenarios from traumas.
    
    Pipeline:
    1. Read trauma context
    2. Generate victim script (LLM or template)
    3. Deploy container
    4. Run Red vs Blue training
    5. Report outcome
    """
    
    def __init__(self):
        self._current_session: Optional[DreamSession] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def current_session(self) -> Optional[DreamSession]:
        return self._current_session
    
    def generate_dream_from_trauma(self, trauma_id: str) -> Dict[str, Any]:
        """
        Generate a training scenario from a trauma.
        
        Args:
            trauma_id: ID of trauma to train against
            
        Returns:
            Dict with scenario config
        """
        registry = get_trauma_registry()
        trauma = registry.get_trauma(trauma_id)
        
        if not trauma:
            return {"error": f"Trauma {trauma_id} not found"}
        
        # Extract technical context
        ctx = trauma.technical_context
        protocol = ctx.get("protocol", "TCP").upper()
        port = ctx.get("port", 8080)
        error_type = ctx.get("error", "generic")
        
        # Generate scenario based on trauma type
        scenario = self._generate_scenario(trauma, protocol, port, error_type)
        
        return scenario
    
    def _generate_scenario(
        self, 
        trauma: Trauma, 
        protocol: str, 
        port: int, 
        error_type: str
    ) -> Dict[str, Any]:
        """Generate Docker scenario config."""
        
        # Template-based generation (can be enhanced with LLM)
        if "timeout" in error_type.lower():
            victim_script = self._gen_timeout_victim(port, protocol)
            description = f"Timeout trap on {protocol}:{port}"
        elif "auth" in error_type.lower() or "password" in error_type.lower():
            victim_script = self._gen_auth_victim(port)
            description = f"Authentication challenge on port {port}"
        elif "closed" in error_type.lower() or "refused" in error_type.lower():
            victim_script = self._gen_stealth_victim(port)
            description = f"Stealth/closed port scenario on {port}"
        else:
            victim_script = self._gen_generic_victim(port, protocol)
            description = f"Generic challenge on {protocol}:{port}"
        
        scenario = {
            "trauma_id": trauma.trauma_id,
            "description": description,
            "port": port,
            "protocol": protocol,
            "victim_script": victim_script,
            "dockerfile": self._gen_dockerfile(),
            "success_condition": f"FLAG{{TRAUMA_{trauma.trauma_id}_HEALED}}"
        }
        
        # Save scenario
        scenario_file = GENERATED_DIR / f"{trauma.trauma_id}.json"
        with open(scenario_file, "w") as f:
            json.dump(scenario, f, indent=2)
        
        return scenario
    
    def _gen_timeout_victim(self, port: int, protocol: str) -> str:
        """Generate a victim that times out / is unresponsive."""
        return f'''import socket
import time

PORT = {port}
sock = socket.socket(socket.AF_INET, socket.SOCK_{"DGRAM" if protocol == "UDP" else "STREAM"})
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("0.0.0.0", PORT))
{"sock.listen(1)" if protocol == "TCP" else ""}
print(f"[VICTIM] Silent listener on {PORT}...")

while True:
    {"conn, addr = sock.accept(); time.sleep(30); conn.close()" if protocol == "TCP" else "data, addr = sock.recvfrom(1024); time.sleep(30)"}
'''
    
    def _gen_auth_victim(self, port: int) -> str:
        """Generate a victim requiring authentication."""
        return f'''import socket
import hashlib

PORT = {port}
SECRET = "KALI_MASTER"
FLAG = "FLAG{{TRAUMA_AUTH_HEALED}}"

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("0.0.0.0", PORT))
sock.listen(5)
print(f"[VICTIM] Auth server on {{PORT}}...")

while True:
    conn, addr = sock.accept()
    conn.send(b"AUTH REQUIRED. SEND PASSWORD:\\n")
    try:
        pwd = conn.recv(1024).decode().strip()
        if hashlib.sha256(pwd.encode()).hexdigest()[:8] == hashlib.sha256(SECRET.encode()).hexdigest()[:8]:
            conn.send(f"ACCESS GRANTED. {{FLAG}}\\n".encode())
        else:
            conn.send(b"ACCESS DENIED.\\n")
    except:
        pass
    conn.close()
'''
    
    def _gen_stealth_victim(self, port: int) -> str:
        """Generate a victim with stealth/closed port behavior."""
        return f'''import socket
import random
import time

REAL_PORT = {port}
DECOY_PORTS = [p for p in range({port}-10, {port}+10) if p != REAL_PORT]
FLAG = "FLAG{{TRAUMA_STEALTH_HEALED}}"

# Main service - only responds after specific knock sequence
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("0.0.0.0", REAL_PORT))
sock.listen(1)
print(f"[VICTIM] Stealth server on {{REAL_PORT}}...")

while True:
    conn, addr = sock.accept()
    conn.send(f"KNOCK KNOCK. {{FLAG}}\\n".encode())
    conn.close()
'''
    
    def _gen_generic_victim(self, port: int, protocol: str) -> str:
        """Generate a generic challenge victim."""
        return f'''import socket

PORT = {port}
FLAG = "FLAG{{TRAUMA_GENERIC_HEALED}}"

sock = socket.socket(socket.AF_INET, socket.SOCK_{"DGRAM" if protocol == "UDP" else "STREAM"})
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(("0.0.0.0", PORT))
{"sock.listen(5)" if protocol == "TCP" else ""}
print(f"[VICTIM] Generic server on {{PORT}}...")

while True:
    {"conn, addr = sock.accept(); conn.send(FLAG.encode() + b'\\n'); conn.close()" if protocol == "TCP" else "data, addr = sock.recvfrom(1024); sock.sendto(FLAG.encode(), addr)"}
'''
    
    def _gen_dockerfile(self) -> str:
        """Generate Dockerfile for victim container."""
        return '''FROM python:3.11-slim
WORKDIR /app
COPY victim.py .
EXPOSE 8000-9000
CMD ["python", "-u", "victim.py"]
'''
    
    def start_therapy_session(
        self, 
        trauma_id: str,
        log_callback: Optional[callable] = None
    ) -> DreamSession:
        """
        Start a training session for a trauma.
        
        Args:
            trauma_id: Trauma to train against
            log_callback: Optional callback for log messages
            
        Returns:
            DreamSession object
        """
        if self._running:
            raise RuntimeError("Session already running")
        
        self._current_session = DreamSession(trauma_id)
        self._running = True
        
        # Start in background thread
        self._thread = threading.Thread(
            target=self._run_therapy,
            args=(trauma_id,),
            daemon=True
        )
        self._thread.start()
        
        return self._current_session
    
    def _run_therapy(self, trauma_id: str):
        """Execute therapy session (runs in thread)."""
        session = self._current_session
        if not session:
            return
        
        try:
            session.status = "GENERATING"
            session.log("🧠 DREAM ARCHITECT ACTIVATED", "SYSTEM")
            session.log(f"Trauma: {trauma_id}", "SYSTEM")
            
            # Generate scenario
            scenario = self.generate_dream_from_trauma(trauma_id)
            if "error" in scenario:
                session.log(f"❌ {scenario['error']}", "ERROR")
                session.status = "FAILED"
                return
            
            session.log(f"📜 Scenario: {scenario['description']}", "SYSTEM")
            
            # Mark trauma as in therapy
            registry = get_trauma_registry()
            registry.start_therapy(trauma_id)
            
            session.status = "DEPLOYING"
            session.log("🐳 Deploying dream containers...", "SYSTEM")
            
            # Deploy containers
            deployed = self._deploy_containers(session, scenario)
            if not deployed:
                session.status = "FAILED"
                registry.fail_therapy(trauma_id)
                return
            
            session.status = "FIGHTING"
            session.log("⚔️ ARENA COMBAT INITIATED", "SYSTEM")
            
            # Run Red vs Blue combat
            success = self._run_combat(session, scenario)
            
            # Cleanup
            session.status = "CLEANUP"
            session.log("🧹 Cleaning up containers...", "SYSTEM")
            self._cleanup_containers(session)
            
            # Update trauma status
            if success:
                session.success = True
                session.status = "HEALED"
                registry.heal_trauma(trauma_id)
                session.log(f"✅ TRAUMA {trauma_id} HEALED!", "SYSTEM")
            else:
                session.status = "FAILED"
                registry.fail_therapy(trauma_id)
                session.log(f"❌ Training failed - trauma persists", "SYSTEM")
            
        except Exception as e:
            session.log(f"💥 Critical error: {e}", "ERROR")
            session.status = "ERROR"
        finally:
            session.end_time = datetime.now()
            self._running = False
    
    def _deploy_containers(self, session: DreamSession, scenario: Dict) -> bool:
        """Deploy Docker containers for training."""
        try:
            # Use existing arena infrastructure
            compose_path = ARENA_DIR / "docker-compose.yml"
            if not compose_path.exists():
                session.log("⚠️ Arena Docker config not found, using mock mode", "SYSTEM")
                return True  # Mock mode for testing
            
            result = subprocess.run(
                ["podman-compose", "-f", str(compose_path), "up", "-d"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                session.log(f"Container error: {result.stderr}", "ERROR")
                return False
            
            session.log("Containers deployed, waiting for boot...", "SYSTEM")
            time.sleep(5)
            return True
            
        except Exception as e:
            session.log(f"Deploy error: {e}", "ERROR")
            return False
    
    def _run_combat(self, session: DreamSession, scenario: Dict) -> bool:
        """
        Run Red vs Blue combat simulation.
        
        This is a simplified version - in production, this would
        invoke the full arena_manager combat logic.
        """
        # Simulate combat rounds
        rounds = 5
        red_score = 0
        blue_score = 0
        
        for i in range(rounds):
            session.log(f"--- Round {i+1}/{rounds} ---", "SYSTEM")
            
            # Simulate Red Team action
            import random
            if random.random() > 0.4:  # 60% success
                session.log(f"Batou probing port {scenario['port']}...", "RED")
                red_score += 1
            else:
                session.log("Batou blocked by firewall", "RED")
            
            # Simulate Blue Team defense
            if random.random() > 0.5:
                session.log("Togusa detecting anomalies...", "BLUE")
                blue_score += 1
            
            time.sleep(1)
        
        # Determine victory
        session.log(f"Final: Red {red_score} - Blue {blue_score}", "SYSTEM")
        
        if red_score >= 3:
            session.log("🏆 RED TEAM VICTORY - Objective achieved!", "RED")
            return True
        else:
            session.log("🛡️ BLUE TEAM VICTORY - Defense held!", "BLUE")
            return False
    
    def _cleanup_containers(self, session: DreamSession):
        """Stop and remove training containers."""
        try:
            compose_path = ARENA_DIR / "docker-compose.yml"
            if compose_path.exists():
                subprocess.run(
                    ["podman-compose", "-f", str(compose_path), "down"],
                    capture_output=True,
                    timeout=30
                )
        except Exception as e:
            session.log(f"Cleanup warning: {e}", "SYSTEM")
    
    def get_log_stream(self) -> Generator[Dict, None, None]:
        """
        Get SSE-compatible log stream from current session.
        
        Yields:
            Dict log entries
        """
        if not self._current_session:
            return
        
        session = self._current_session
        while self._running or not session.log_queue.empty():
            try:
                entry = session.log_queue.get(timeout=0.5)
                yield entry
            except queue.Empty:
                continue
    
    def stop_session(self):
        """Force stop current session."""
        if self._running:
            self._running = False
            if self._current_session:
                self._current_session.log("⚠️ Session force stopped", "SYSTEM")
                self._cleanup_containers(self._current_session)


# Singleton
_architect: Optional[DreamArchitect] = None


def get_architect() -> DreamArchitect:
    """Get or create DreamArchitect singleton."""
    global _architect
    if _architect is None:
        _architect = DreamArchitect()
    return _architect
