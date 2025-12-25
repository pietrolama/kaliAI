#!/usr/bin/env python3
"""
Test Hybrid Search - Verifica RRF e BM25
"""
import sys
import os
from pathlib import Path
import logging

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Configura logging
logging.basicConfig(level=logging.INFO)

from knowledge.knowledge_enhancer import knowledge_enhancer

def test_search():
    print("=" * 70)
    print("🔍 TEST RICERCA IBRIDA")
    print("=" * 70)
    
    # 1. Ricostruisci indice se necessario
    if not knowledge_enhancer.bm25_manager or not knowledge_enhancer.bm25_manager.bm25:
        print("⏳ Ricostruzione indice BM25...")
        knowledge_enhancer.rebuild_search_index()
    
    queries = [
        "nmap -sS",  # Sintattico puro (flag)
        "port scanning techniques", # Semantico
        "CVE-2021-36260", # Identificatore esatto
        "exploit hikvision authentication" # Misto
    ]
    
    for query in queries:
        print(f"\n🔎 QUERY: '{query}'")
        print("-" * 70)
        
        results = knowledge_enhancer.enhanced_search(query, top_k=3)
        
        if not results:
            print("❌ Nessun risultato")
            continue
            
        for i, res in enumerate(results, 1):
            source = res.get('source', 'unknown')
            is_keyword = res.get('is_keyword_match', False)
            doc_preview = res['doc'][:100].replace('\n', ' ')
            
            match_type = "🔤 KEYWORD" if is_keyword else "🧠 HYBRID/VECTOR"
            print(f"{i}. [{source}] {match_type}")
            print(f"   {doc_preview}...")
            
            # Se è BM25, mostra lo score originale
            if 'score' in res:
                 print(f"   BM25 Score: {res['score']:.2f}")
            if 'distance' in res:
                 print(f"   Vector Dist: {res['distance']:.2f}")
                 
if __name__ == "__main__":
    test_search()

