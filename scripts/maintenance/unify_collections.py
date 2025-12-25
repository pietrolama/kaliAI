#!/usr/bin/env python3
"""
Unify Collections - Unifica tutte le collections in kali_linux_kb
"""
import sys
from pathlib import Path
import time

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge.chromadb_config import get_chromadb_client

def main():
    print('=' * 70)
    print('🔄 UNIFICAZIONE COLLECTIONS')
    print('=' * 70)
    print()
    
    client = get_chromadb_client()
    
    # Lista tutte le collections
    collections = client.list_collections()
    print('📚 Collections esistenti:')
    for c in collections:
        print(f'  {c.name:30} {c.count():6,} documenti')
    print()
    
    # Collection principale
    main_collection_name = 'kali_linux_kb'
    main_collection = client.get_collection(main_collection_name)
    
    print(f'📦 Collection principale: {main_collection_name}')
    print(f'   Documenti attuali: {main_collection.count():,}')
    print()
    
    # Collections da unificare (escludi main e long_term_memory)
    collections_to_merge = [
        'kali_knowledge_full',  # Vuota, da rimuovere
        'tool_manuals',  # Se ha documenti, unificali
        'exploits_db',  # Se ha documenti, unificali
    ]
    
    total_merged = 0
    
    for coll_name in collections_to_merge:
        try:
            coll = client.get_collection(coll_name)
            count = coll.count()
            
            if count == 0:
                print(f'⚪ {coll_name}: Vuota, da rimuovere')
                try:
                    client.delete_collection(coll_name)
                    print(f'   ✅ Rimossa')
                except Exception as e:
                    print(f'   ⚠️  Errore rimozione: {e}')
                continue
            
            print(f'📥 {coll_name}: {count:,} documenti da unificare...')
            
            # Ottieni tutti i documenti
            all_docs = coll.get()
            ids = all_docs.get('ids', [])
            documents = all_docs.get('documents', [])
            metadatas = all_docs.get('metadatas', [])
            embeddings = all_docs.get('embeddings', [])
            
            if not ids:
                print(f'   ⚠️  Nessun documento trovato')
                continue
            
            # Prepara batch per aggiunta
            batch_size = 1000
            added = 0
            
            for i in range(0, len(ids), batch_size):
                batch_end = min(i + batch_size, len(ids))
                batch_ids = ids[i:batch_end]
                batch_docs = documents[i:batch_end]
                batch_metas = metadatas[i:batch_end] if metadatas else [{}] * len(batch_ids)
                batch_embs = embeddings[i:batch_end] if embeddings else None
                
                # Aggiungi metadata per tracciare origine
                for meta in batch_metas:
                    meta['original_collection'] = coll_name
                    meta['merged_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
                
                # Aggiungi con prefisso per evitare conflitti ID
                prefixed_ids = [f"{coll_name}_{id}" for id in batch_ids]
                
                try:
                    if batch_embs and all(e is not None for e in batch_embs):
                        main_collection.add(
                            ids=prefixed_ids,
                            documents=batch_docs,
                            metadatas=batch_metas,
                            embeddings=batch_embs
                        )
                    else:
                        main_collection.add(
                            ids=prefixed_ids,
                            documents=batch_docs,
                            metadatas=batch_metas
                        )
                    added += len(batch_ids)
                except Exception as e:
                    print(f'   ⚠️  Errore batch {i//batch_size + 1}: {e}')
                    # Prova uno per uno
                    for j, (id, doc, meta) in enumerate(zip(batch_ids, batch_docs, batch_metas)):
                        try:
                            prefixed_id = f"{coll_name}_{id}"
                            main_collection.add(
                                ids=[prefixed_id],
                                documents=[doc],
                                metadatas=[meta]
                            )
                            added += 1
                        except Exception as e2:
                            print(f'      ⚠️  Errore documento {id[:50]}: {e2}')
            
            print(f'   ✅ Unificati: {added:,} documenti')
            total_merged += added
            
            # Rimuovi collection originale dopo merge
            try:
                client.delete_collection(coll_name)
                print(f'   🗑️  Collection originale rimossa')
            except Exception as e:
                print(f'   ⚠️  Errore rimozione collection: {e}')
            
            print()
        
        except Exception as e:
            print(f'⚠️  Errore processando {coll_name}: {e}')
            print()
    
    # Statistiche finali
    final_count = main_collection.count()
    print('=' * 70)
    print('📊 RISULTATI')
    print('=' * 70)
    print(f'✅ Documenti unificati: {total_merged:,}')
    print(f'📦 Total in {main_collection_name}: {final_count:,}')
    print()
    
    # Verifica collections rimanenti
    remaining = client.list_collections()
    print('📚 Collections rimanenti:')
    for c in remaining:
        print(f'  {c.name:30} {c.count():6,} documenti')
    print()
    
    print('=' * 70)
    print('✅ UNIFICAZIONE COMPLETATA!')
    print('=' * 70)

if __name__ == "__main__":
    main()

