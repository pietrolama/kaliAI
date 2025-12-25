#!/usr/bin/env python3
"""
Memory Manager - Gestione memorie a lungo termine e contextual
"""
import os
import json
import uuid
import chromadb
import logging
from datetime import datetime
from typing import Optional, List, Dict

logger = logging.getLogger('MemoryManager')

# Percorsi
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, 'chroma_db')
DATA_PATH = os.path.join(PROJECT_ROOT, "data")
SESSION_PATH = os.path.join(DATA_PATH, "session")
CONTEXTUAL_MEMORY_PATH = os.path.join(SESSION_PATH, "contextual_memory.json")

def log_info(msg):
    logger.info(msg)

# === LONG TERM MEMORY (ChromaDB Vector Store) ===

def add_memory_to_vectordb(summary_text: str, metadata: Optional[Dict] = None):
    # Disabilita telemetria ChromaDB
    import os
    import warnings
    os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
    warnings.filterwarnings("ignore", message=".*telemetry.*")
    """
    Aggiunge memoria a lungo termine in ChromaDB.
    
    Args:
        summary_text: Testo da memorizzare
        metadata: Metadati opzionali (dict)
    """
    # Disabilita telemetria
    import warnings
    warnings.filterwarnings("ignore", message=".*telemetry.*")
    try:
        from chromadb.config import Settings
        settings = Settings(anonymized_telemetry=False)
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH, settings=settings)
    except:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name="long_term_memory")
    collection.add(
        documents=[summary_text],
        metadatas=[metadata or {}],
        ids=[f"mem_{uuid.uuid4()}"]
    )

def recall_from_vectordb(query: str, top_k: int = 3) -> List[Dict]:
    """
    Recupera memorie rilevanti dalla vector database.
    
    Args:
        query: Query di ricerca
        top_k: Numero di risultati
        
    Returns:
        Lista di dict con 'doc' e 'meta'
    """
    # Disabilita telemetria
    import warnings
    warnings.filterwarnings("ignore", message=".*telemetry.*")
    try:
        from chromadb.config import Settings
        settings = Settings(anonymized_telemetry=False)
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH, settings=settings)
    except:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name="long_term_memory")
    results = collection.query(query_texts=[query], n_results=top_k)
    out = []
    for docs, metas in zip(results.get('documents', []), results.get('metadatas', [])):
        for doc, meta in zip(docs, metas):
            out.append({"doc": doc, "meta": meta})
    return out

def list_all_long_term_memories() -> List[Dict]:
    """
    Lista tutte le memorie a lungo termine.
    
    Returns:
        Lista di dict con id, text, metadata
    """
    # Disabilita telemetria
    import warnings
    warnings.filterwarnings("ignore", message=".*telemetry.*")
    try:
        from chromadb.config import Settings
        settings = Settings(anonymized_telemetry=False)
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH, settings=settings)
    except:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name="long_term_memory")
    results = collection.get(include=["documents", "metadatas"])
    docs = results.get('documents', [])
    metas = results.get('metadatas', [])
    ids = results.get('ids', [])
    memories = []
    for doc, meta, _id in zip(docs, metas, ids):
        memories.append({
            "id": _id,
            "text": doc,
            "metadata": meta
        })
    return memories

def delete_memory_from_vectordb(memory_id: str) -> bool:
    """
    Elimina una memoria dalla vector database.
    
    Args:
        memory_id: ID della memoria da eliminare
        
    Returns:
        True se eliminata, False altrimenti
    """
    # Disabilita telemetria
    import warnings
    warnings.filterwarnings("ignore", message=".*telemetry.*")
    try:
        from chromadb.config import Settings
        settings = Settings(anonymized_telemetry=False)
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH, settings=settings)
    except:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name="long_term_memory")
    try:
        collection.delete(ids=[memory_id])
        return True
    except Exception as e:
        log_info(f"[MemoryManager] Errore eliminazione memoria: {e}")
        return False

# === CONTEXTUAL MEMORY (JSON File) ===

def add_contextual_solution(title: str, summary: str, prompt: str, solution: str, tags: Optional[List[str]] = None) -> Optional[str]:
    """
    Aggiunge soluzione contextual in JSON file.
    
    Args:
        title: Titolo della soluzione
        summary: Riassunto
        prompt: Prompt originale
        solution: Soluzione trovata
        tags: Tag opzionali
        
    Returns:
        ID della soluzione salvata, None se errore
    """
    entry = {
        "id": f"sol_{uuid.uuid4()}",
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "title": title,
        "summary": summary,
        "prompt": prompt,
        "solution": solution,
        "tags": tags or []
    }
    try:
        memory = []
        if os.path.exists(CONTEXTUAL_MEMORY_PATH):
            with open(CONTEXTUAL_MEMORY_PATH, "r", encoding="utf-8") as f:
                memory = json.load(f)
        memory.append(entry)
        with open(CONTEXTUAL_MEMORY_PATH, "w", encoding="utf-8") as f:
            json.dump(memory, f, ensure_ascii=False, indent=2)
        return entry["id"]
    except Exception as e:
        log_info(f"[MemoryManager][ERRORE] {e}")
        return None

# Funzioni deprecate (non usate, mantenute per backward compatibility)
def search_contextual_memory(query: str, max_results: int = 3) -> List[Dict]:
    """
    DEPRECATED: Cerca in contextual memory JSON.
    Non più usato - mantenuto per backward compatibility.
    """
    if not os.path.exists(CONTEXTUAL_MEMORY_PATH):
        return []
    with open(CONTEXTUAL_MEMORY_PATH, "r", encoding="utf-8") as f:
        memory = json.load(f)
    results = []
    for entry in memory:
        text = (entry['title'] + " " + entry['summary'] + " " + entry['prompt'] + " " + entry['solution']).lower()
        if query.lower() in text:
            results.append(entry)
    return results[:max_results]

def get_contextual_memory() -> List[Dict]:
    """
    DEPRECATED: Ottiene tutta la contextual memory.
    Non più usato - mantenuto per backward compatibility.
    """
    if os.path.exists(CONTEXTUAL_MEMORY_PATH):
        with open(CONTEXTUAL_MEMORY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

