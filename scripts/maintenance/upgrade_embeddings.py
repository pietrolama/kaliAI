#!/usr/bin/env python3
"""
Upgrade Embeddings - Migra a modello embeddings migliore
"""
import sys
import os
from pathlib import Path
import json

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def main():
    print('=' * 70)
    print('🚀 UPGRADE EMBEDDINGS MODEL')
    print('=' * 70)
    print()
    
    print('📊 Modello attuale: all-MiniLM-L6-v2 (384 dim)')
    print('   Qualità: 🟡 Media (Relevance: 24.5%, Distance: 0.755)')
    print()
    
    print('💡 Opzioni disponibili:')
    print()
    print('1. BAAI/bge-small-en-v1.5 (384 dim) - RACCOMANDATO')
    print('   ✅ Stessa dimensione (compatibile)')
    print('   ✅ Qualità superiore')
    print('   ✅ Velocità simile')
    print('   📦 Size: 130MB')
    print()
    print('2. all-mpnet-base-v2 (768 dim) - Massima qualità')
    print('   ⚠️  Dimensione diversa (richiede ricalcolo completo)')
    print('   ✅ Qualità massima')
    print('   ⚠️  Più lento')
    print('   📦 Size: 420MB')
    print()
    
    choice = input('Scegli opzione (1/2) o "q" per uscire: ').strip()
    
    if choice == 'q':
        print('❌ Operazione annullata')
        return
    
    if choice == '1':
        model_name = 'BAAI/bge-small-en-v1.5'
        model_dims = 384
        print(f'\n✅ Selezionato: {model_name}')
    elif choice == '2':
        model_name = 'all-mpnet-base-v2'
        model_dims = 768
        print(f'\n✅ Selezionato: {model_name}')
        print('⚠️  ATTENZIONE: Richiede ricalcolo completo di tutti gli embeddings!')
        confirm = input('   Procedere? (s/n): ').strip().lower()
        if confirm != 's':
            print('❌ Operazione annullata')
            return
    else:
        print('❌ Opzione non valida')
        return
    
    print()
    print('📝 Aggiornamento configurazione...')
    
    # Aggiorna rag_config.json
    config_path = PROJECT_ROOT / 'knowledge' / 'rag_config.json'
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    config['embeddings']['model'] = model_name
    config['embeddings']['dims'] = model_dims
    
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f'✅ Config aggiornato: {model_name}')
    print()
    
    print('⚠️  IMPORTANTE:')
    print('   1. Installa il modello: pip install sentence-transformers')
    print(f'   2. Il modello verrà scaricato automaticamente al primo uso')
    print('   3. Per usare il nuovo modello, aggiorna KnowledgeEnhancer')
    print('      per usare il nuovo embedding function')
    print()
    
    print('📋 Prossimi passi:')
    print('   1. Aggiorna knowledge_enhancer.py per usare nuovo modello')
    print('   2. (Opzionale) Ricalcola embeddings esistenti')
    print('   3. Testa qualità con: python scripts/analyze_embeddings_quality.py')
    print()

if __name__ == "__main__":
    main()

