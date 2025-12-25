#!/usr/bin/env python3
"""
Full Knowledge Update - Aggiorna TUTTE le fonti di conoscenza abilitate.
Usa RAGManager per orchestrare il fetch da fonti multiple (HackTricks, PayloadsAllTheThings, OWASP, etc.)
"""
import sys
import os
import logging
from pathlib import Path
import argparse

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge.rag_manager import rag_manager
from knowledge.sources import registry

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(name)s] %(message)s'
)
logger = logging.getLogger('FullUpdate')

def main():
    parser = argparse.ArgumentParser(description="Full Knowledge Base Update")
    parser.add_argument('--dry-run', action='store_true', help="Non salvare nel DB, solo test fetch")
    parser.add_argument('--source', type=str, help="Esegui solo per una specifica source (es. 'hacktricks')")
    args = parser.parse_args()

    print("=" * 70)
    print("🚀 FULL KNOWLEDGE BASE UPDATE")
    print("=" * 70)
    
    # Check enabled sources
    enabled_sources = registry.list_enabled()
    print(f"📋 Fonti abilitate ({len(enabled_sources)}):")
    for source in enabled_sources:
        print(f"  - {source}")
    print()

    if args.source:
        if args.source not in enabled_sources:
            print(f"❌ Source '{args.source}' non trovata o non abilitata.")
            return
        print(f"🎯 Esecuzione singola source: {args.source}")
        # Disabilita temporaneamente le altre per il fetch
        for s in list(enabled_sources):
            if s != args.source:
                registry.get(s).enabled = False
    
    print("⏳ Avvio aggiornamento (questo processo può richiedere tempo)...")
    print()

    try:
        # Execute fetch via RAG Manager
        stats = rag_manager.fetch_all_sources()
        
        print()
        print("=" * 70)
        print("📊 RISULTATI AGGIORNAMENTO")
        print("=" * 70)
        
        total_fetched = 0
        total_added = 0
        
        for source, stat in stats.items():
            status_icon = "✅" if stat.get('status') == 'success' else "❌"
            fetched = stat.get('fetched', 0)
            added = stat.get('added', 0)
            total_fetched += fetched
            total_added += added
            
            print(f"{status_icon} {source}:")
            print(f"   Fetchati: {fetched}")
            print(f"   Aggiunti: {added}")
            if stat.get('error'):
                print(f"   Errore: {stat.get('error')}")
        
        print()
        print(f"📈 Totale Fetchati: {total_fetched}")
        print(f"💾 Totale Aggiunti: {total_added}")
        
        # Final stats
        print()
        final_stats = rag_manager.get_stats()
        print("📚 Stato Knowledge Base:")
        print(f"  Totale documenti: {final_stats['collections']['total']}")
        
    except Exception as e:
        print(f"\n❌ Errore critico durante l'aggiornamento: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

