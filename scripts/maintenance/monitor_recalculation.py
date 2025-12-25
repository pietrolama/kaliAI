#!/usr/bin/env python3
"""
Monitor Recalculation - Monitora progresso ricalcolo embeddings
"""
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge.rag_manager import rag_manager

def main():
    print('📊 MONITOR RICALCOLO EMBEDDINGS')
    print('=' * 70)
    print()
    
    # Statistiche iniziali
    stats = rag_manager.get_stats()
    collections = stats.get('collections', {})
    initial_total = collections.get('total', 0)
    
    print(f'📊 Documenti iniziali: {initial_total:,}')
    print()
    print('⏳ Monitoraggio in corso...')
    print('   Premi Ctrl+C per interrompere')
    print()
    
    last_count = initial_total
    start_time = time.time()
    
    try:
        while True:
            stats = rag_manager.get_stats()
            collections = stats.get('collections', {})
            current_total = collections.get('total', 0)
            
            elapsed = time.time() - start_time
            
            # Mostra progresso
            if current_total != last_count:
                print(f'⏱️  {elapsed/60:.1f} min | Total: {current_total:,} documenti')
                last_count = current_total
            else:
                print(f'⏱️  {elapsed/60:.1f} min | In attesa...', end='\r')
            
            time.sleep(5)
            
    except KeyboardInterrupt:
        print('\n\n⏸️  Monitoraggio interrotto')
        stats = rag_manager.get_stats()
        collections = stats.get('collections', {})
        current_total = collections.get('total', 0)
        print(f'📊 Stato finale: {current_total:,} documenti')
        print()
        print('💡 Per valutare risultati:')
        print('   python scripts/evaluate_recalculation.py')

if __name__ == "__main__":
    main()

