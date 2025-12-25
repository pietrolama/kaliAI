#!/usr/bin/env python3
"""
Monitor Import - Monitora progresso import knowledge export
"""
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge.rag_manager import rag_manager

def main():
    print('📊 MONITOR IMPORT KNOWLEDGE EXPORT')
    print('=' * 70)
    print()
    
    # Target: 5,896 documenti da importare
    target = 5896
    initial_count = 192  # Count iniziale kali_kb (prima dell'import)
    
    print(f'🎯 Target: {target} documenti')
    print(f'📊 Count iniziale kali_kb: {initial_count}')
    print()
    print('⏳ Monitoraggio progresso...')
    print()
    
    last_count = initial_count
    start_time = time.time()
    
    try:
        while True:
            stats = rag_manager.get_stats()
            collections = stats.get('collections', {})
            current_count = collections.get('kali_kb', 0)
            
            # Calcola progresso
            imported = current_count - initial_count
            progress = (imported / target) * 100 if target > 0 else 0
            remaining = target - imported
            
            # Calcola velocità
            elapsed = time.time() - start_time
            if imported > 0 and elapsed > 0:
                speed = imported / elapsed
                eta = remaining / speed if speed > 0 else 0
            else:
                speed = 0
                eta = 0
            
            # Mostra progresso
            bar_length = 50
            filled = int(bar_length * progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            print(f'\r[{bar}] {progress:.1f}% | Importati: {imported:,}/{target:,} | '
                  f'Velocità: {speed:.1f} doc/s | ETA: {eta/60:.1f} min', end='', flush=True)
            
            # Se completato
            if imported >= target:
                print('\n\n✅ IMPORT COMPLETATO!')
                break
            
            # Se non c'è progresso da 30 secondi, potrebbe essere finito
            if current_count == last_count:
                time.sleep(2)
            else:
                last_count = current_count
                time.sleep(1)
            
    except KeyboardInterrupt:
        print('\n\n⏸️  Monitoraggio interrotto')
        stats = rag_manager.get_stats()
        collections = stats.get('collections', {})
        current_count = collections.get('kali_kb', 0)
        imported = current_count - initial_count
        print(f'📊 Stato attuale: {imported:,} documenti importati')

if __name__ == "__main__":
    main()

