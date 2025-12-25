#!/usr/bin/env python3
"""
Test Nuova RAG - Test completo delle nuove fonti
"""
import sys
import os
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge.sources import registry
from knowledge.rag_manager import rag_manager

def test_sources_registry():
    """Test registro sources"""
    print("=" * 70)
    print("📋 TEST REGISTRO SOURCES")
    print("=" * 70)
    
    all_sources = registry.list_all()
    enabled_sources = registry.list_enabled()
    
    print(f"\n✅ Sources totali: {len(all_sources)}")
    print(f"✅ Sources abilitati: {len(enabled_sources)}")
    print(f"\n📚 Sources registrati:")
    for name in all_sources:
        source = registry.get(name)
        status = "✅" if source.enabled else "❌"
        print(f"  {status} {name}")
    
    print(f"\n📊 Statistiche:")
    stats = registry.get_stats()
    print(f"  Total: {stats['total_sources']}")
    print(f"  Enabled: {stats['enabled_sources']}")
    print(f"  Disabled: {stats['disabled_sources']}")
    
    return len(all_sources), len(enabled_sources)

def test_source_info():
    """Test info sources"""
    print("\n" + "=" * 70)
    print("ℹ️  INFO SOURCES")
    print("=" * 70)
    
    enabled = registry.list_enabled()
    
    for name in enabled[:5]:  # Prime 5
        source = registry.get(name)
        if source:
            info = source.get_source_info()
            print(f"\n📌 {name.upper()}")
            print(f"   Type: {info.get('type', 'N/A')}")
            print(f"   URL: {info.get('url', 'N/A')}")
            print(f"   Description: {info.get('description', 'N/A')}")
            print(f"   Rate Limit: {info.get('rate_limit', 'N/A')}")

def test_fetch_sources():
    """Test fetch da sources"""
    print("\n" + "=" * 70)
    print("🔄 TEST FETCH SOURCES")
    print("=" * 70)
    print("\n⚠️  Questo può richiedere alcuni minuti...")
    print("    Fetchando da sources abilitati...\n")
    
    try:
        stats = rag_manager.fetch_all_sources()
        
        print("\n📊 RISULTATI FETCH:")
        print("-" * 70)
        
        total_fetched = 0
        total_added = 0
        
        for source_name, result in stats.items():
            status_icon = "✅" if result['status'] == 'success' else "❌"
            fetched = result.get('fetched', 0)
            added = result.get('added', 0)
            
            print(f"{status_icon} {source_name:20} → Fetched: {fetched:3} | Added: {added:3}")
            
            if result['status'] == 'error':
                print(f"   ⚠️  Errore: {result.get('error', 'Unknown')}")
            
            total_fetched += fetched
            total_added += added
        
        print("-" * 70)
        print(f"📈 TOTALE: Fetched: {total_fetched} | Added: {total_added}")
        
        return stats
        
    except Exception as e:
        print(f"❌ Errore durante fetch: {e}")
        import traceback
        traceback.print_exc()
        return {}

def test_search():
    """Test ricerca migliorata"""
    print("\n" + "=" * 70)
    print("🔍 TEST RICERCA MIGLIORATA")
    print("=" * 70)
    
    test_queries = [
        "SQL injection",
        "CVE-2024",
        "authentication bypass",
        "IoT exploit"
    ]
    
    for query in test_queries:
        print(f"\n🔎 Query: '{query}'")
        print("-" * 70)
        
        try:
            results = rag_manager.enhanced_search(query, top_k=3)
            
            if not results:
                print("  ❌ Nessun risultato")
                continue
            
            print(f"  ✅ Trovati {len(results)} risultati:\n")
            
            for i, res in enumerate(results, 1):
                source = res.get('source', 'unknown')
                distance = res.get('distance', 1.0)
                doc = res.get('doc', '')[:200]
                weight = res.get('weight', 1.0)
                
                print(f"  {i}. [{source.upper()}] (distance: {distance:.3f}, weight: {weight:.1f}x)")
                print(f"     {doc}...")
                print()
                
        except Exception as e:
            print(f"  ❌ Errore: {e}")

def test_stats():
    """Test statistiche finali"""
    print("\n" + "=" * 70)
    print("📊 STATISTICHE FINALI RAG")
    print("=" * 70)
    
    try:
        stats = rag_manager.get_stats()
        
        print("\n📚 COLLECTIONS:")
        collections = stats.get('collections', {})
        for name, count in collections.items():
            if name != 'total':
                print(f"  {name:20} {count:6} documenti")
        print(f"  {'TOTAL':20} {collections.get('total', 0):6} documenti")
        
        print("\n🔌 SOURCES:")
        sources_stats = stats.get('sources', {})
        print(f"  Total sources: {sources_stats.get('total_sources', 0)}")
        print(f"  Enabled: {sources_stats.get('enabled_sources', 0)}")
        
    except Exception as e:
        print(f"❌ Errore: {e}")

def main():
    print("\n" + "=" * 70)
    print("🧪 TEST COMPLETO NUOVA RAG")
    print("=" * 70)
    
    # 1. Test registro
    total, enabled = test_sources_registry()
    
    # 2. Test info
    test_source_info()
    
    # 3. Test fetch (opzionale - commenta se vuoi solo test veloce)
    print("\n" + "=" * 70)
    response = input("Vuoi testare il fetch da tutte le fonti? (s/n): ").strip().lower()
    if response == 's':
        test_fetch_sources()
    else:
        print("⏭️  Fetch saltato")
    
    # 4. Test ricerca
    test_search()
    
    # 5. Statistiche
    test_stats()
    
    print("\n" + "=" * 70)
    print("✅ TEST COMPLETATO")
    print("=" * 70)

if __name__ == "__main__":
    main()

