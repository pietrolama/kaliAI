# show_memories.py

import os
import chromadb

# Percorso coerente con quello usato nel tuo tools.py
CHROMA_DB_PATH = os.path.join(os.path.dirname(__file__), 'chroma_db')

def list_all_long_term_memories():
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(name="long_term_memory")
    results = collection.get(include=["documents", "metadatas"])   # <-- SOLO questi!
    memories = []
    for doc, meta, _id in zip(results['documents'], results['metadatas'], results['ids']):
        memories.append({
            "id": _id,
            "text": doc,
            "metadata": meta
        })
    return memories

if __name__ == "__main__":
    print("=== MEMORIA A LUNGO TERMINE ===")
    memories = list_all_long_term_memories()
    if not memories:
        print("Nessun ricordo salvato!")
    else:
        for i, mem in enumerate(memories, 1):
            print(f"\n--- Ricordo #{i} ---")
            print(f"ID: {mem['id']}")
            print(f"Testo:\n{mem['text']}")
            print(f"Metadata: {mem['metadata']}")
