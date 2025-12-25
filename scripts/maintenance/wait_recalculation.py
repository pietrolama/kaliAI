#!/usr/bin/env python3
"""
Wait Recalculation - Attende completamento ricalcolo e mostra risultati
"""
import sys
import time
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def check_process_running():
    """Verifica se il processo è in esecuzione"""
    try:
        result = subprocess.run(
            ['ps', 'aux'],
            capture_output=True,
            text=True
        )
        return 'recalculate_embeddings' in result.stdout and 'grep' not in result.stdout
    except:
        return False

def main():
    print('=' * 70)
    print('⏳ ATTESA COMPLETAMENTO RICALCOLO EMBEDDINGS')
    print('=' * 70)
    print()
    print('🔍 Monitoraggio processo in corso...')
    print('   Premi Ctrl+C per interrompere')
    print()
    
    start_time = time.time()
    last_check = 0
    
    while True:
        if not check_process_running():
            elapsed = time.time() - start_time
            print()
            print('=' * 70)
            print('✅ RICALCOLO COMPLETATO!')
            print('=' * 70)
            print(f'⏱️  Tempo totale: {elapsed/60:.1f} minuti')
            print()
            print('📊 Valutazione risultati...')
            print()
            
            # Esegui valutazione
            try:
                from knowledge.rag_manager import rag_manager
                from knowledge.embedding_manager import get_embedding_manager
                
                # Statistiche
                stats = rag_manager.get_stats()
                collections = stats.get('collections', {})
                total = collections.get('total', 0)
                
                print(f'📚 Documenti totali: {total:,}')
                print()
                
                # Test rapido
                results = rag_manager.enhanced_search('nmap port scanning', top_k=3)
                if results:
                    distances = [r.get('distance', 1.0) for r in results]
                    avg_dist = sum(distances) / len(distances)
                    relevance = (1.0 - avg_dist) * 100
                    
                    print(f'🔍 Test ricerca:')
                    print(f'   Distance media: {avg_dist:.3f}')
                    print(f'   Relevance: {relevance:.1f}%')
                    print()
                    
                    if avg_dist < 0.5:
                        quality = '🟢 ECCELLENTE'
                    elif avg_dist < 0.6:
                        quality = '🟢 BUONA'
                    elif avg_dist < 0.7:
                        quality = '🟡 MEDIA'
                    else:
                        quality = '🟠 BASSA'
                    
                    print(f'📊 Qualità: {quality}')
                    print()
                
                print('💡 Per valutazione completa:')
                print('   python scripts/evaluate_recalculation.py')
                
            except Exception as e:
                print(f'⚠️  Errore valutazione: {e}')
            
            print()
            print('=' * 70)
            break
        
        # Mostra progresso ogni minuto
        elapsed = time.time() - start_time
        if elapsed - last_check >= 60:
            minutes = int(elapsed / 60)
            print(f'⏱️  {minutes} minuti trascorsi... (processo ancora in esecuzione)')
            last_check = elapsed
        
        time.sleep(10)  # Controlla ogni 10 secondi

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n⏸️  Monitoraggio interrotto')
        sys.exit(0)

