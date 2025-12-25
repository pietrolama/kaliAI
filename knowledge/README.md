# 📚 Knowledge System

Sistema completo di gestione della conoscenza per KaliAI.

## 📁 Struttura

```
knowledge/
├── __init__.py                     # Package initialization
├── knowledge_enhancer.py           # Core: gestione ChromaDB, BM25 e ricerca Ibrida
├── bm25_manager.py                 # Manager ricerca keyword (BM25)
├── knowledge_fetcher.py            # Fetching da fonti curate (RSS, API)
├── exploit_hunter.py               # Hunting exploit da multiple sources
├── exploit_hunter_config.json      # Configurazione hunting
├── scripts/                        # Script specifici knowledge
│   ├── maintenance/                # Script di manutenzione e import
│   └── ...
│
└── docs/                           # Documentazione
    ├── EXPLOIT_HUNTER.md           # Guida exploit hunter
    ├── INTEGRAZIONE_RAG.md         # Come il RAG è integrato
    └── KNOWLEDGE_SYSTEM.md         # Overview sistema
```

## 📁 Script Globali

Gli script di utilità sono stati riorganizzati in `scripts/`:

- `scripts/maintenance/`: Import, unificazione, ricalcolo embeddings, monitoraggio.
- `scripts/testing/`: Test RAG, embedding quality, evaluation.
- `scripts/setup/`: Installazione tool.
- `scripts/utils/`: Utility varie (memorie, wiz).

---

## 🔧 Moduli Core

### `knowledge_enhancer.py`
**Core del sistema di conoscenza**

- Gestisce collections ChromaDB (ora unificate principalmente in `kali_linux_kb`).
- **Ricerca Ibrida (Hybrid Search)**: Combina Vettoriale e Keyword.
- Collections attive:
  - `kali_linux_kb` - Conoscenza generale (unificata: contiene exploit, tools, manuali)
  - `cve_database` - CVE
  - `successful_attacks` - Success cases (prioritari nella ricerca)
  - `long_term_memory` - Memoria a lungo termine

**Funzioni principali**:
```python
from knowledge.knowledge_enhancer import knowledge_enhancer

# Ricerca multi-collection (prioritizza successi)
# Usa RRF (Reciprocal Rank Fusion) per combinare ChromaDB + BM25
results = knowledge_enhancer.enhanced_search("query", top_k=5)

# Ricostruzione indice testuale (se necessario)
knowledge_enhancer.rebuild_search_index()

# Statistiche
stats = knowledge_enhancer.get_stats()
```

### `bm25_manager.py`
**Gestore Ricerca Testuale**
- Mantiene indice BM25 in memoria e su disco (`data/bm25_index.pkl`).
- Tokenizzazione ottimizzata per termini tecnici (CVE, flag, IP).

### `knowledge_fetcher.py`
**Download da fonti curate**

Fonti supportate:
- ✅ CISA KEV (Known Exploited Vulnerabilities)
- ✅ NVD Recent CVEs
- ✅ RSS feeds (US-CERT, Packet Storm, BleepingComputer)
- ✅ Reddit security subreddits
- ✅ MITRE ATT&CK

### `exploit_hunter.py`
**Hunting exploit automatico**

Fonti:
- ✅ GitHub (API search PoC)
- ✅ Exploit-DB (scraping)
- ✅ Packet Storm (RSS)
- ✅ Google Project Zero (blog)
- ✅ Reddit r/ExploitDev
- ✅ NVD API

---

## 🚀 Script di Automazione

### Aggiornamento/Import
```bash
# Import da export (maintenance)
python scripts/maintenance/import_knowledge_export.py

# Ricostruzione manuale indice ibrido (se serve)
python -m knowledge.knowledge_enhancer
```

### Test
```bash
# Test RAG completo
python scripts/testing/test_new_rag.py
```

---

## 📊 Statistiche Attuali

```
Knowledge Base: ~6,085 documenti totali

Collections:
  • kali_kb: 5,916 documenti (Unificata)
  • cve: 95 documenti
  • successes: 74 documenti
  • tools: 0 documenti (integrati in kali_kb)
  • exploits: 0 documenti (integrati in kali_kb)
```

---

## 🛠️ Maintenance

### Ricalcolo Embeddings
Se si cambia modello di embedding:
```bash
python scripts/maintenance/recalculate_embeddings.py
```

### Verifica Integrità
```bash
python -c "from knowledge.rag_manager import rag_manager; print(rag_manager.get_stats())"
```

---

## 🔗 Integrazione con Sistema Principale

Il sistema di conoscenza è integrato in:

### `modules/smart_context_builder.py`
Durante la generazione degli step, il RAG viene consultato automaticamente.

### `modules/tools.py`
Tool RAG disponibile per l'agente: `rag_search_tool(query)`
