#!/usr/bin/env python3
"""
Recalculate Embeddings - Ricalcola tutti gli embeddings con il nuovo modello
"""
import sys
import os
from pathlib import Path
import time
import json

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Importa configurazione ChromaDB PRIMA di tutto per disabilitare telemetria
from knowledge.chromadb_config import get_chromadb_client

from knowledge.embedding_manager import get_embedding_manager
from knowledge.knowledge_enhancer import KnowledgeEnhancer
import chromadb
import os

def recalculate_collection(collection, collection_name, embedding_manager, batch_size=100):
    """Ricalcola embeddings per una collection"""
    total_docs = collection.count()
    
    if total_docs == 0:
        print(f'  ⚪ {collection_name}: Vuota, saltata')
        return 0
    
    print(f'  📊 {collection_name}: {total_docs} documenti')
    print(f'     ⏳ Ricalcolo in batch di {batch_size}...')
    
    # Leggi tutti i documenti
    all_docs = collection.get()
    
    if not all_docs or not all_docs.get('ids'):
        print(f'     ⚠️  Nessun documento trovato')
        return 0
    
    ids = all_docs['ids']
    documents = all_docs.get('documents', [])
    metadatas = all_docs.get('metadatas', [])
    
    if len(documents) != len(ids):
        print(f'     ⚠️  Mismatch documenti/ids, saltata')
        return 0
    
    # Usa lo stesso client della collection
    # NOTA: collection._client potrebbe non funzionare, usa enhancer.client
    from knowledge.knowledge_enhancer import KnowledgeEnhancer
    enhancer = KnowledgeEnhancer()
    client = enhancer.client
    temp_name = f"{collection_name}_temp_recalc"
    
    try:
        # Elimina collection temporanea se esiste
        try:
            client.delete_collection(temp_name)
        except:
            pass
        
        # Crea nuova collection (senza embedding function, useremo embeddings pre-calcolati)
        # Usa create_collection invece di get_or_create per evitare problemi
        try:
            client.delete_collection(temp_name)
        except:
            pass
        
        temp_collection = client.create_collection(name=temp_name)
        
        # Verifica che la collection abbia il metodo add
        if not hasattr(temp_collection, 'add'):
            # Prova upsert come alternativa
            if not hasattr(temp_collection, 'upsert'):
                print(f'     ❌ Collection non supporta add/upsert')
                return 0
        
        # Calcola embeddings manualmente e aggiungi in batch
        added = 0
        start_time = time.time()
        
        print(f'     🔄 Calcolo embeddings con nuovo modello...')
        
        for i in range(0, len(documents), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_docs = documents[i:i+batch_size]
            batch_metas = metadatas[i:i+batch_size] if metadatas else [{}] * len(batch_docs)
            
            # Calcola embeddings con nuovo modello
            batch_embeddings = embedding_manager.encode(batch_docs, normalize=True)
            
            # Converti embeddings a lista se necessario
            if isinstance(batch_embeddings, list) and len(batch_embeddings) > 0:
                if not isinstance(batch_embeddings[0], list):
                    # È un array numpy, converti
                    batch_embeddings = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in batch_embeddings]
            
            # Aggiungi con embeddings pre-calcolati usando upsert (più robusto)
            try:
                temp_collection.upsert(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids,
                    embeddings=batch_embeddings
                )
            except AttributeError:
                # Fallback a add se upsert non esiste
                temp_collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids,
                    embeddings=batch_embeddings
                )
            
            added += len(batch_ids)
            elapsed = time.time() - start_time
            progress = (added / total_docs) * 100
            speed = added / elapsed if elapsed > 0 else 0
            
            print(f'     📈 Progresso: {added}/{total_docs} ({progress:.1f}%) | '
                  f'{speed:.1f} doc/s', end='\r')
        
        elapsed = time.time() - start_time
        print(f'\n     ✅ Completato: {added} documenti in {elapsed:.1f}s ({added/elapsed:.1f} doc/s)')
        
        # Sostituisci collection vecchia con nuova
        print(f'     🔄 Sostituzione collection...')
        
        # Elimina vecchia collection
        try:
            client.delete_collection(collection_name)
        except:
            pass
        
        # Crea nuova collection
        try:
            client.delete_collection(collection_name)
        except:
            pass
        
        new_collection = client.create_collection(name=collection_name)
        
        # Copia documenti con embeddings
        temp_docs = temp_collection.get(include=['documents', 'metadatas', 'embeddings'])
        if temp_docs and temp_docs.get('ids'):
            # Copia in batch
            batch_size_copy = 500
            for i in range(0, len(temp_docs['ids']), batch_size_copy):
                batch_ids = temp_docs['ids'][i:i+batch_size_copy]
                batch_docs = temp_docs['documents'][i:i+batch_size_copy]
                batch_metas = temp_docs.get('metadatas', [{}] * len(batch_ids))[i:i+batch_size_copy]
                batch_embs = temp_docs.get('embeddings', [])[i:i+batch_size_copy]
                
                # Converti embeddings se necessario
                if batch_embs and len(batch_embs) > 0:
                    if not isinstance(batch_embs[0], list):
                        batch_embs = [emb.tolist() if hasattr(emb, 'tolist') else emb for emb in batch_embs]
                
                # Usa upsert per essere più robusto
                try:
                    new_collection.upsert(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids,
                        embeddings=batch_embs
                    )
                except AttributeError:
                    new_collection.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids,
                        embeddings=batch_embs
                    )
        
        # Elimina temporanea
        client.delete_collection(temp_name)
        
        print(f'     ✅ Collection aggiornata con nuovi embeddings')
        
        return added
        
    except Exception as e:
        print(f'\n     ❌ Errore: {e}')
        import traceback
        traceback.print_exc()
        
        # Cleanup
        try:
            client.delete_collection(temp_name)
        except:
            pass
        
        return 0

def main():
    print('=' * 70)
    print('🔄 RICALCOLO EMBEDDINGS CON NUOVO MODELLO')
    print('=' * 70)
    print()
    
    # Carica embedding manager
    print('📥 Caricamento nuovo modello embeddings...')
    try:
        embedding_manager = get_embedding_manager()
        model_name = embedding_manager.get_model_name()
        print(f'✅ Modello: {model_name}')
        print(f'📐 Dimensioni: {embedding_manager.get_dimensions()}')
    except Exception as e:
        print(f'❌ Errore caricamento modello: {e}')
        return
    
    print()
    print('⚠️  ATTENZIONE:')
    print('   Questo processo ricalcolerà TUTTI gli embeddings esistenti.')
    print('   Potrebbe richiedere molto tempo (minuti/ore).')
    print('   Le collections verranno temporaneamente sostituite.')
    print()
    
    response = input('Procedere con ricalcolo completo? (s/n): ').strip().lower()
    
    if response != 's':
        print('❌ Operazione annullata')
        return
    
    print()
    print('⏳ Avvio ricalcolo...')
    print()
    
    # Carica enhancer
    enhancer = KnowledgeEnhancer()
    
    # Collections da ricalcolare
    collections_to_recalc = {
        'kali_linux_kb': enhancer.kb_collection,
        'exploits_db': enhancer.exploits_collection,
        'cve_database': enhancer.cve_collection,
        'successful_attacks': enhancer.success_collection,
        'tool_manuals': enhancer.tools_collection,
    }
    
    # Aggiungi full_kb se esiste
    if enhancer.full_kb_collection:
        collections_to_recalc['kali_knowledge_full'] = enhancer.full_kb_collection
    
    total_start = time.time()
    total_recalculated = 0
    
    print('📚 Collections da ricalcolare:')
    for name in collections_to_recalc.keys():
        count = collections_to_recalc[name].count()
        print(f'  • {name}: {count} documenti')
    print()
    
    # Ricalcola ogni collection
    for collection_name, collection in collections_to_recalc.items():
        print(f'🔄 {collection_name}:')
        recalculated = recalculate_collection(
            collection, 
            collection_name, 
            embedding_manager,
            batch_size=500  # Batch più grandi per velocità
        )
        total_recalculated += recalculated
        print()
    
    total_time = time.time() - total_start
    
    print('=' * 70)
    print('📊 RISULTATI RICALCOLO')
    print('=' * 70)
    print(f'✅ Documenti ricalcolati: {total_recalculated:,}')
    print(f'⏱️  Tempo totale: {total_time/60:.1f} minuti ({total_time:.1f}s)')
    if total_time > 0:
        print(f'📈 Velocità media: {total_recalculated/total_time:.1f} doc/s')
    print()
    print('✅ Ricalcolo completato!')
    print()
    print('💡 Testa qualità migliorata:')
    print('   python scripts/analyze_embeddings_quality.py')
    print('=' * 70)

if __name__ == "__main__":
    main()

