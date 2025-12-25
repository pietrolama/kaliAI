#!/usr/bin/env python3
"""
Analisi Qualità Embeddings - Valuta qualità embeddings e confronta modelli
"""
import sys
import os
from pathlib import Path
import json
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge.rag_manager import rag_manager
from knowledge.sources import registry

def analyze_embedding_distribution():
    """Analizza distribuzione embeddings nel knowledge_export"""
    print('=' * 70)
    print('📊 ANALISI EMBEDDINGS KNOWLEDGE EXPORT')
    print('=' * 70)
    print()
    
    json_path = PROJECT_ROOT / 'data' / 'knowledge_export.json'
    
    if not json_path.exists():
        print('❌ knowledge_export.json non trovato')
        return
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    documents = data.get('documents', [])
    print(f'📄 Documenti totali: {len(documents)}')
    print()
    
    # Analizza embeddings
    embeddings_with_data = []
    embedding_dims = []
    
    for doc in documents[:100]:  # Analizza primi 100
        embedding = doc.get('embedding', [])
        if embedding:
            embeddings_with_data.append(embedding)
            embedding_dims.append(len(embedding))
    
    if not embeddings_with_data:
        print('❌ Nessun embedding trovato')
        return
    
    # Statistiche
    dim = embedding_dims[0]
    print(f'📐 Dimensione embeddings: {dim}')
    print(f'📊 Documenti con embedding: {len(embeddings_with_data)}/{len(documents[:100])}')
    print()
    
    # Analizza distribuzione valori
    all_values = np.array([val for emb in embeddings_with_data[:10] for val in emb])
    print('📈 Statistiche valori:')
    print(f'  Min: {all_values.min():.4f}')
    print(f'  Max: {all_values.max():.4f}')
    print(f'  Media: {all_values.mean():.4f}')
    print(f'  Std: {all_values.std():.4f}')
    print()
    
    # Verifica modello
    print('🔍 Modello probabile:')
    if dim == 384:
        print('  ✅ all-MiniLM-L6-v2 (384 dim)')
        print('     - Compatibile con ChromaDB default')
        print('     - Buona velocità, qualità media')
    elif dim == 768:
        print('  📌 all-mpnet-base-v2 (768 dim)')
        print('     - Qualità superiore, più lento')
    else:
        print(f'  ❓ Sconosciuto ({dim} dim)')
    print()

def test_search_quality():
    """Testa qualità ricerca con query specifiche"""
    print('=' * 70)
    print('🔍 TEST QUALITÀ RICERCA')
    print('=' * 70)
    print()
    
    test_cases = [
        {
            'query': 'nmap port scanning',
            'expected_keywords': ['nmap', 'port', 'scan'],
            'min_distance': 0.5
        },
        {
            'query': 'SQL injection attack',
            'expected_keywords': ['sql', 'injection'],
            'min_distance': 0.5
        },
        {
            'query': 'Kali Linux installation',
            'expected_keywords': ['kali', 'linux', 'installation'],
            'min_distance': 0.5
        }
    ]
    
    results_summary = []
    
    for case in test_cases:
        query = case['query']
        print(f'🔎 Query: "{query}"')
        
        results = rag_manager.enhanced_search(query, top_k=5)
        
        if not results:
            print('  ❌ Nessun risultato')
            results_summary.append({
            'query': query, 
            'results': 0, 
            'avg_distance': 1.0,
            'relevance': 0.0,
            'keywords_found': 0
        })
            continue
        
        distances = [r.get('distance', 1.0) for r in results]
        avg_distance = sum(distances) / len(distances)
        min_distance = min(distances)
        
        # Verifica keywords nei risultati
        keywords_found = 0
        for r in results:
            doc_text = r.get('doc', '').lower()
            for keyword in case['expected_keywords']:
                if keyword.lower() in doc_text:
                    keywords_found += 1
                    break
        
        relevance_score = (1.0 - avg_distance) * 100
        
        print(f'  ✅ {len(results)} risultati')
        print(f'  📊 Distance: min={min_distance:.3f}, avg={avg_distance:.3f}')
        print(f'  🎯 Relevance: {relevance_score:.1f}%')
        print(f'  🔑 Keywords match: {keywords_found}/{len(results)}')
        
        # Valutazione
        if avg_distance < 0.5:
            quality = '🟢 Eccellente'
        elif avg_distance < 0.7:
            quality = '🟡 Buona'
        elif avg_distance < 0.9:
            quality = '🟠 Media'
        else:
            quality = '🔴 Bassa'
        
        print(f'  📈 Qualità: {quality}')
        print()
        
        results_summary.append({
            'query': query,
            'results': len(results),
            'avg_distance': avg_distance,
            'min_distance': min_distance,
            'relevance': relevance_score,
            'quality': quality,
            'keywords_found': keywords_found
        })
    
    # Riepilogo
    print('=' * 70)
    print('📊 RIEPILOGO QUALITÀ')
    print('=' * 70)
    print()
    
    avg_relevance = sum(r['relevance'] for r in results_summary) / len(results_summary)
    avg_distance = sum(r['avg_distance'] for r in results_summary) / len(results_summary)
    
    print(f'📈 Relevance media: {avg_relevance:.1f}%')
    print(f'📉 Distance media: {avg_distance:.3f}')
    print()
    
    if avg_distance < 0.5:
        print('✅ Qualità embeddings: ECCELLENTE')
    elif avg_distance < 0.7:
        print('🟡 Qualità embeddings: BUONA')
    elif avg_distance < 0.9:
        print('🟠 Qualità embeddings: MEDIA - Considera modello migliore')
    else:
        print('🔴 Qualità embeddings: BASSA - Necessita miglioramento')
    
    print()

def compare_models():
    """Confronta modelli embeddings disponibili"""
    print('=' * 70)
    print('🔬 CONFRONTO MODELLI EMBEDDINGS')
    print('=' * 70)
    print()
    
    models = [
        {
            'name': 'all-MiniLM-L6-v2',
            'dims': 384,
            'speed': '🟢 Veloce',
            'quality': '🟡 Media',
            'size': '80MB',
            'note': 'Attuale - Buon compromesso'
        },
        {
            'name': 'all-mpnet-base-v2',
            'dims': 768,
            'speed': '🟡 Media',
            'quality': '🟢 Alta',
            'size': '420MB',
            'note': 'Raccomandato per qualità'
        },
        {
            'name': 'sentence-transformers/all-MiniLM-L12-v2',
            'dims': 384,
            'speed': '🟡 Media',
            'quality': '🟢 Buona',
            'size': '120MB',
            'note': 'Miglioramento su L6'
        },
        {
            'name': 'BAAI/bge-small-en-v1.5',
            'dims': 384,
            'speed': '🟢 Veloce',
            'quality': '🟢 Alta',
            'size': '130MB',
            'note': 'State-of-the-art per 384 dim'
        }
    ]
    
    print('Modelli disponibili:')
    print()
    for model in models:
        print(f"📌 {model['name']}")
        print(f"   Dimensione: {model['dims']} dim")
        print(f"   Velocità: {model['speed']}")
        print(f"   Qualità: {model['quality']}")
        print(f"   Size: {model['size']}")
        print(f"   Note: {model['note']}")
        print()
    
    print('💡 Raccomandazione:')
    print('   Per qualità: all-mpnet-base-v2 o BAAI/bge-small-en-v1.5')
    print('   Per velocità: Mantieni all-MiniLM-L6-v2')
    print()

def main():
    analyze_embedding_distribution()
    test_search_quality()
    compare_models()
    
    print('=' * 70)
    print('💡 SUGGERIMENTI MIGLIORAMENTO')
    print('=' * 70)
    print()
    print('1. Considera modello migliore:')
    print('   - all-mpnet-base-v2 (768 dim) per qualità massima')
    print('   - BAAI/bge-small-en-v1.5 (384 dim) per buon compromesso')
    print()
    print('2. Usa embeddings pre-calcolati se compatibili')
    print('3. Migliora chunking (riduci chunk_size, aumenta overlap)')
    print('4. Aggiungi preprocessing (normalizzazione, rimozione noise)')
    print()

if __name__ == "__main__":
    main()

