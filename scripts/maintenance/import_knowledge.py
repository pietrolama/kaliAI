#!/usr/bin/env python3
"""
Import massive knowledge base into ChromaDB
"""
import json
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import chromadb
from chromadb.config import Settings
from tqdm import tqdm

def import_knowledge(json_file: str, chroma_db_path: str):
    """Import knowledge from JSON export into ChromaDB"""
    
    print(f"📂 Caricamento {json_file}...")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_docs = data['total_documents']
    documents = data['documents']
    
    print(f"📊 Trovati {total_docs} documenti")
    print(f"📅 Export del: {data['export_date']}")
    
    # Connetti a ChromaDB
    print(f"\n🔗 Connessione a ChromaDB: {chroma_db_path}")
    client = chromadb.PersistentClient(
        path=chroma_db_path,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Nome collection basato sul source
    collection_name = "kali_linux_kb"
    
    print(f"📦 Collection: {collection_name}")
    
    # Get or create collection
    try:
        collection = client.get_collection(collection_name)
        print(f"✅ Collection esistente trovata")
        existing_count = collection.count()
        print(f"   Documenti esistenti: {existing_count}")
        
        # Ask for confirmation
        response = input(f"\n⚠️  Aggiungere {total_docs} documenti alla collection esistente? [s/N]: ")
        if response.lower() != 's':
            print("❌ Importazione annullata")
            return
    except:
        print(f"🆕 Creazione nuova collection")
        collection = client.create_collection(
            name=collection_name,
            metadata={"description": "Full Kali Linux knowledge base"}
        )
    
    # Prepare data for ChromaDB
    print(f"\n📝 Preparazione dati...")
    
    ids = []
    embeddings = []
    metadatas = []
    documents_content = []
    
    for doc in tqdm(documents, desc="Processing"):
        ids.append(doc['id'])
        embeddings.append(doc['embedding'])
        
        # Metadata (converti tags da string a lista se necessario)
        metadata = doc['metadata'].copy()
        if 'tags' in metadata and isinstance(metadata['tags'], str):
            try:
                import ast
                metadata['tags'] = str(ast.literal_eval(metadata['tags']))
            except:
                pass  # Lascia come stringa se parsing fallisce
        
        metadatas.append(metadata)
        documents_content.append(doc['content'])
    
    # Import in batches (ChromaDB ha limiti)
    BATCH_SIZE = 1000
    total_batches = (len(ids) + BATCH_SIZE - 1) // BATCH_SIZE
    
    print(f"\n💾 Importazione in {total_batches} batch da {BATCH_SIZE} documenti...")
    
    for i in tqdm(range(0, len(ids), BATCH_SIZE), desc="Importing"):
        batch_end = min(i + BATCH_SIZE, len(ids))
        
        collection.add(
            ids=ids[i:batch_end],
            embeddings=embeddings[i:batch_end],
            metadatas=metadatas[i:batch_end],
            documents=documents_content[i:batch_end]
        )
    
    final_count = collection.count()
    print(f"\n✅ Importazione completata!")
    print(f"📊 Totale documenti nella collection: {final_count}")
    print(f"🎯 Collection: {collection_name}")
    print(f"📂 Path: {chroma_db_path}")
    
    # Test query
    print(f"\n🔍 Test query...")
    results = collection.query(
        query_texts=["nmap port scanning"],
        n_results=3
    )
    
    print(f"   Trovati {len(results['documents'][0])} risultati:")
    for i, doc in enumerate(results['documents'][0], 1):
        print(f"   {i}. {doc[:100]}...")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Import knowledge base into ChromaDB")
    parser.add_argument(
        '--json', 
        default='knowledge_export.json',
        help='Path to JSON export file (default: knowledge_export.json)'
    )
    parser.add_argument(
        '--db',
        default='chroma_db',
        help='Path to ChromaDB directory (default: chroma_db)'
    )
    
    args = parser.parse_args()
    
    json_path = PROJECT_ROOT / args.json
    db_path = PROJECT_ROOT / args.db
    
    if not json_path.exists():
        print(f"❌ File non trovato: {json_path}")
        sys.exit(1)
    
    import_knowledge(str(json_path), str(db_path))

