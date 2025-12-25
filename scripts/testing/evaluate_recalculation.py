#!/usr/bin/env python3
"""
Evaluate Recalculation - Valuta risultati ricalcolo embeddings
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge.rag_manager import rag_manager
from knowledge.embedding_manager import get_embedding_manager

def main():
    print('=' * 70)
    print('📊 VALUTAZIONE RISULTATI RICALCOLO EMBEDDINGS')
    print('=' * 70)
    print()
    
    # 1. Verifica modello attivo
    print('1️⃣  MODELLO EMBEDDINGS')
    print('-' * 70)
    try:
        manager = get_embedding_manager()
        model_name = manager.get_model_name()
        dims = manager.get_dimensions()
        print(f'✅ Modello: {model_name}')
        print(f'📐 Dimensioni: {dims}')
        
        if 'bge' in model_name.lower():
            print('✅ Usa modello migliorato (BAAI/bge-small-en-v1.5)')
        else:
            print('⚠️  Usa modello vecchio, considera upgrade')
    except Exception as e:
        print(f'❌ Errore: {e}')
    print()
    
    # 2. Statistiche collections
    print('2️⃣  STATISTICHE COLLECTIONS')
    print('-' * 70)
    stats = rag_manager.get_stats()
    collections = stats.get('collections', {})
    
    total = collections.get('total', 0)
    print(f'📊 Total documenti: {total:,}')
    print()
    
    for name, count in sorted(collections.items()):
        if name != 'total':
            pct = (count / total * 100) if total > 0 else 0
            print(f'  {name:20} {count:6,} documenti ({pct:5.1f}%)')
    print()
    
    # 3. Test qualità ricerca
    print('3️⃣  TEST QUALITÀ RICERCA')
    print('-' * 70)
    
    test_queries = [
        ('nmap port scanning', ['nmap', 'port', 'scan']),
        ('Kali Linux installation', ['kali', 'linux', 'installation']),
        ('SQL injection attack', ['sql', 'injection']),
        ('network reconnaissance', ['network', 'reconnaissance']),
        ('penetration testing tools', ['penetration', 'testing', 'tools'])
    ]
    
    total_relevance = 0
    total_distance = 0
    successful_queries = 0
    
    for query, keywords in test_queries:
        results = rag_manager.enhanced_search(query, top_k=3)
        
        if results:
            distances = [r.get('distance', 1.0) for r in results]
            avg_dist = sum(distances) / len(distances)
            min_dist = min(distances)
            relevance = (1.0 - avg_dist) * 100
            
            total_relevance += relevance
            total_distance += avg_dist
            successful_queries += 1
            
            # Verifica keywords
            keywords_found = 0
            for r in results:
                doc_text = r.get('doc', '').lower()
                for kw in keywords:
                    if kw.lower() in doc_text:
                        keywords_found += 1
                        break
            
            print(f'Query: "{query}"')
            print(f'  ✅ {len(results)} risultati')
            print(f'  📊 Distance: min={min_dist:.3f}, avg={avg_dist:.3f}')
            print(f'  🎯 Relevance: {relevance:.1f}%')
            print(f'  🔑 Keywords match: {keywords_found}/{len(results)}')
            print()
        else:
            print(f'Query: "{query}"')
            print(f'  ❌ Nessun risultato')
            print()
    
    # 4. Metriche finali
    if successful_queries > 0:
        avg_relevance = total_relevance / successful_queries
        avg_distance = total_distance / successful_queries
        
        print('4️⃣  METRICHE FINALI')
        print('-' * 70)
        print(f'📈 Relevance media: {avg_relevance:.1f}%')
        print(f'📉 Distance media: {avg_distance:.3f}')
        print(f'✅ Query con risultati: {successful_queries}/{len(test_queries)}')
        print()
        
        # Valutazione qualità
        if avg_distance < 0.5:
            quality = '🟢 ECCELLENTE'
            score = 100
        elif avg_distance < 0.6:
            quality = '🟢 BUONA'
            score = 80
        elif avg_distance < 0.7:
            quality = '🟡 MEDIA'
            score = 60
        elif avg_distance < 0.8:
            quality = '🟠 BASSA'
            score = 40
        else:
            quality = '🔴 MOLTO BASSA'
            score = 20
        
        print(f'📊 Qualità embeddings: {quality}')
        print(f'🎯 Score: {score}/100')
        print()
        
        # Confronto con baseline
        print('5️⃣  CONFRONTO CON BASELINE')
        print('-' * 70)
        baseline_relevance = 24.5  # Prima del miglioramento
        baseline_distance = 0.755
        
        relevance_improvement = avg_relevance - baseline_relevance
        distance_improvement = baseline_distance - avg_distance
        
        print(f'Baseline (all-MiniLM-L6-v2):')
        print(f'  Relevance: {baseline_relevance:.1f}%')
        print(f'  Distance: {baseline_distance:.3f}')
        print()
        print(f'Attuale ({model_name}):')
        print(f'  Relevance: {avg_relevance:.1f}% ({relevance_improvement:+.1f}%)')
        print(f'  Distance: {avg_distance:.3f} ({distance_improvement:+.3f})')
        print()
        
        if relevance_improvement > 0:
            print(f'✅ Miglioramento relevance: +{relevance_improvement:.1f}%')
        if distance_improvement > 0:
            print(f'✅ Miglioramento distance: -{distance_improvement:.3f}')
        
        if relevance_improvement > 10 or distance_improvement > 0.1:
            print()
            print('🎉 Ricalcolo embeddings ha migliorato significativamente la qualità!')
        elif relevance_improvement > 0 or distance_improvement > 0:
            print()
            print('✅ Ricalcolo embeddings ha migliorato la qualità')
        else:
            print()
            print('⚠️  Nessun miglioramento significativo. Verifica:')
            print('   • Gli embeddings sono stati ricalcolati?')
            print('   • Il nuovo modello è configurato correttamente?')
    
    print()
    print('=' * 70)
    print('✅ VALUTAZIONE COMPLETATA')
    print('=' * 70)

if __name__ == "__main__":
    main()

