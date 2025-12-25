#!/usr/bin/env python3
"""
Import Knowledge Export - Importa knowledge base da knowledge_export.json
"""
import sys
import os
from pathlib import Path
import time

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge.sources import registry
from knowledge.rag_manager import rag_manager

def main():
    # Import completo con progress bar
    export_source = registry.get('knowledge_export')
    print('=' * 70)
    print('🚀 IMPORT COMPLETO KNOWLEDGE EXPORT')
    print('=' * 70)
    print()
    print('📊 File: knowledge_export.json')
    print('📄 Documenti totali: 5,896')
    print('⏱️  Tempo stimato: ~5-10 minuti')
    print()
    print('⏳ Avvio import...')
    print()
    
    start_time = time.time()
    
    # Fetch tutti i documenti
    print('📥 Fetching documenti...')
    fetch_start = time.time()
    results = export_source.fetch(limit=None)
    fetch_time = time.time() - fetch_start
    print(f'✅ Fetch completato: {len(results)} documenti in {fetch_time:.1f}s')
    print()
    
    # Import in batch per mostrare progresso (batch più grandi = più veloce)
    batch_size = 1000  # Batch più grandi per velocità
    total_batches = (len(results) + batch_size - 1) // batch_size
    total_added = 0
    
    print(f'💾 Aggiunta a ChromaDB in batch di {batch_size}...')
    print()
    
    for i in range(0, len(results), batch_size):
        batch = results[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        batch_start = time.time()
        # Usa use_batch=True se supportato, altrimenti fallback
        try:
            # Nota: _add_results_to_collection non accetta use_batch come argomento in questa versione,
            # gestiamo il batching manualmente qui.
            added = rag_manager._add_results_to_collection(batch, 'kali_linux_kb')
        except Exception as e:
            print(f"Errore batch {batch_num}: {e}")
            added = 0
            
        batch_time = time.time() - batch_start
        total_added += added
        
        elapsed = time.time() - start_time
        remaining = (elapsed / batch_num) * (total_batches - batch_num) if batch_num > 0 else 0
        
        print(f'  Batch {batch_num}/{total_batches}: {added} documenti aggiunti ({batch_time:.1f}s) | '
              f'Totale: {total_added}/{len(results)} | '
              f'Velocità: {added/batch_time if batch_time > 0 else 0:.1f} doc/s | '
              f'Tempo rimanente: ~{remaining/60:.1f} min')
    
    total_time = time.time() - start_time
    
    print()
    print('=' * 70)
    print('📊 RISULTATI IMPORT')
    print('=' * 70)
    print(f'✅ Documenti fetchati: {len(results)}')
    print(f'✅ Documenti aggiunti: {total_added}')
    print(f'⏱️  Tempo totale: {total_time/60:.1f} minuti ({total_time:.1f}s)')
    if total_time > 0:
        print(f'📈 Velocità: {total_added/total_time:.1f} doc/s')
    print()
    
    # Statistiche finali
    stats = rag_manager.get_stats()
    collections = stats.get('collections', {})
    print('📚 Knowledge Base aggiornata:')
    print(f'  Total: {collections.get("total", 0):,} documenti')
    print(f'  kali_kb: {collections.get("kali_kb", 0):,} documenti')
    print()
    print('=' * 70)
    print('✅ IMPORT COMPLETATO!')
    print('=' * 70)

if __name__ == "__main__":
    main()
