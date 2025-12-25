#!/usr/bin/env python3
"""
Test Interattivo RAG - Testa query specifiche e mostra risultati dettagliati
"""
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge import knowledge_enhancer

def test_query(query: str, top_k: int = 5):
    """Testa una query e mostra risultati dettagliati"""
    print(f"\n🔍 Query: '{query}'")
    print("=" * 70)
    
    results = knowledge_enhancer.enhanced_search(query, top_k=top_k)
    
    if not results:
        print("❌ Nessun risultato trovato")
        return
    
    print(f"✅ Trovati {len(results)} risultati\n")
    
    for i, res in enumerate(results, 1):
        source = res.get('source', 'unknown')
        distance = res.get('distance', 1.0)
        doc = res.get('doc', '')
        meta = res.get('meta', {})
        
        # Relevance indicator
        if distance < 0.3:
            rel_icon = "🟢 Molto rilevante"
        elif distance < 0.5:
            rel_icon = "🟡 Rilevante"
        elif distance < 0.7:
            rel_icon = "🟠 Poco rilevante"
        else:
            rel_icon = "🔴 Non rilevante"
        
        print(f"--- Risultato #{i} ---")
        print(f"Source: {source.upper()}")
        print(f"Distance: {distance:.4f} | {rel_icon}")
        if meta:
            print(f"Metadata: {meta}")
        print(f"Content: {doc[:300]}...")
        print()

def main():
    print("🧪 TEST INTERATTIVO RAG")
    print("=" * 70)
    print("Inserisci query da testare (o 'exit' per uscire)")
    print()
    
    while True:
        try:
            query = input("Query: ").strip()
            
            if query.lower() in ['exit', 'quit', 'q']:
                print("👋 Arrivederci!")
                break
            
            if not query:
                print("⚠️  Query vuota, riprova")
                continue
            
            # Opzionale: numero risultati
            top_k = input("Numero risultati (default 5): ").strip()
            top_k = int(top_k) if top_k.isdigit() else 5
            
            test_query(query, top_k)
            
        except KeyboardInterrupt:
            print("\n👋 Arrivederci!")
            break
        except Exception as e:
            print(f"❌ Errore: {e}")

if __name__ == "__main__":
    main()

