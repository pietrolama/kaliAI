#!/usr/bin/env python3
"""
ChromaDB Configuration - Configurazione centralizzata per disabilitare telemetria
"""
import os
import warnings
import sys
import logging

# Disabilita telemetria ChromaDB
os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
warnings.filterwarnings("ignore", message=".*telemetry.*")
warnings.filterwarnings("ignore", message=".*Failed to send telemetry.*")

# Sopprimi warning telemetria a livello di logging
logging.getLogger("chromadb").setLevel(logging.ERROR)

# Redirect stderr per sopprimere warning telemetria
class TelemetryFilter:
    """Filtra messaggi telemetria da stderr"""
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr
    
    def write(self, message):
        if "telemetry" not in message.lower() and "Failed to send telemetry" not in message:
            self.original_stderr.write(message)
    
    def flush(self):
        self.original_stderr.flush()

# Applica filtro solo se non già applicato
if not isinstance(sys.stderr, TelemetryFilter):
    sys.stderr = TelemetryFilter(sys.stderr)

def get_chromadb_client(path: str = "chroma_db"):
    """Crea client ChromaDB con telemetria disabilitata"""
    import chromadb
    try:
        from chromadb.config import Settings
        settings = Settings(anonymized_telemetry=False)
        return chromadb.PersistentClient(path=path, settings=settings)
    except:
        return chromadb.PersistentClient(path=path)

