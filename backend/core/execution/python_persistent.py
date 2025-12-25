import subprocess
import threading
import queue
import uuid
import time
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger('PythonPersistent')

class PythonPersistentExecutor:
    """
    Motore di esecuzione Python persistente (The Hand).
    Mantiene il contesto delle variabili tra le esecuzioni.
    Supporta:
    - Esecuzione stateful (variabili persistono)
    - Output capture in real-time
    - Timeout watchdogs
    """
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.process = None
        self.is_running = False
        self._sentinel = f"__GHOSTBRAIN_END_{uuid.uuid4().hex}__"
        self._queue = queue.Queue()
        self._execution_lock = threading.Lock()
        
    def start(self):
        """Avvia il sottoprocesso Python interattivo."""
        if self.is_running and self.process:
            return

        # Avvia python con -i per modalità interattiva e -u per unbuffered I/O
        self.process = subprocess.Popen(
            ["python3", "-i", "-u"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0,
            cwd=os.getcwd() # Esegue nella root del progetto
        )
        self.is_running = True
        
        # Avvia thread per leggere stdout/stderr
        self._start_reader_thread(self.process.stdout, "STDOUT")
        self._start_reader_thread(self.process.stderr, "STDERR")
        
        # Inizializza l'ambiente
        self.execute_code("import sys; import os; import json; import time", timeout=5)
        logger.info("Python Persistent Kernel avviato.")

    def _start_reader_thread(self, pipe, name):
        def reader():
            while self.is_running:
                try:
                    line = pipe.readline()
                    if not line:
                        break
                    self._queue.put((name, line))
                except Exception:
                    break
        t = threading.Thread(target=reader, daemon=True, name=f"Reader-{name}")
        t.start()

    def restart(self):
        """Riavvia il kernel (pulisce la memoria)."""
        self.stop()
        self.start()

    def stop(self):
        """Termina il processo."""
        self.is_running = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    def execute_code(self, code: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Esegue un blocco di codice e ritorna l'output.
        """
        if not self.is_running or not self.process:
            self.start()

        timeout = timeout or self.timeout
        
        # Pulisci la coda da output precedenti
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

        with self._execution_lock:
            try:
                # Incapsula il codice per gestire errori e segnale di fine
                # Usiamo print con flush per assicurare che il sentinel arrivi
                wrapped_code = f"{code}\nprint('{self._sentinel}', flush=True)\n"
                
                self.process.stdin.write(wrapped_code)
                self.process.stdin.flush()
                
                output = []
                error_output = []
                start_time = time.time()
                finished = False
                
                while (time.time() - start_time) < timeout:
                    try:
                        # Leggi dalla coda con breve timeout
                        name, line = self._queue.get(timeout=0.1)
                        
                        if name == "STDOUT":
                            if self._sentinel in line:
                                finished = True
                                # Rimuovi sentinel dalla linea se presente parzialmente
                                clean_line = line.replace(self._sentinel, "").strip()
                                if clean_line:
                                    output.append(clean_line)
                                break
                            output.append(line.rstrip())
                        elif name == "STDERR":
                            # Ignora il prompt interattivo '>>> ' se appare in stderr
                            if line.strip() in ['>>>', '...']:
                                continue
                            error_output.append(line.rstrip())
                            
                    except queue.Empty:
                        if not self.process or self.process.poll() is not None:
                            return {"status": "crash", "output": "\n".join(output), "error": "Process crashed"}
                        continue

                if not finished:
                    # Timeout
                    self.restart() # Necessario riavviare se bloccato
                    return {
                        "status": "timeout",
                        "output": "\n".join(output),
                        "error": f"Execution timed out after {timeout}s"
                    }

                return {
                    "status": "success" if not error_output else "error",
                    "output": "\n".join(output),
                    "error": "\n".join(error_output)
                }

            except Exception as e:
                logger.error(f"Errore esecuzione codice: {e}")
                return {"status": "system_error", "output": "", "error": str(e)}

# Singleton instance per persistenza globale
_executor_instance = None

def get_persistent_executor():
    global _executor_instance
    if _executor_instance is None:
        _executor_instance = PythonPersistentExecutor()
    return _executor_instance
