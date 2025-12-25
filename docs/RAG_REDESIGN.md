# 🔄 RAG Redesign - Nuova Architettura Modulare

## 📋 Panoramica

La RAG è stata completamente riprogettata con un'architettura modulare che permette di aggiungere facilmente nuove fonti di conoscenza.

## 🏗️ Nuova Architettura

### Struttura Modulare

```
knowledge/
├── sources/                    # ✨ NUOVO: Sistema modulare fonti
│   ├── __init__.py
│   ├── base.py                # Classe base DataSource
│   ├── registry.py             # Registro centrale sources
│   ├── owasp_source.py        # OWASP Top 10
│   ├── nvd_source.py          # NIST NVD completo
│   ├── cve_details_source.py  # CVE Details
│   └── securityfocus_source.py # SecurityFocus
│
├── rag_manager.py             # ✨ NUOVO: Manager unificato
├── rag_config.json            # ✨ NUOVO: Configurazione fonti
├── knowledge_enhancer.py      # Core ChromaDB (mantenuto)
└── ...
```

### Componenti Principali

#### 1. **DataSource Base Class** (`sources/base.py`)

Classe astratta per tutti i data source connectors:

```python
class DataSource(ABC):
    def fetch(self, **kwargs) -> List[SourceResult]
    def get_source_info(self) -> Dict
    def validate(self) -> bool
```

#### 2. **Source Registry** (`sources/registry.py`)

Registro centrale per gestire tutti i sources:

```python
from knowledge.sources import registry

# Lista sources abilitati
enabled = registry.list_enabled()

# Statistiche
stats = registry.get_stats()
```

#### 3. **RAG Manager** (`rag_manager.py`)

Manager unificato che integra tutti i sources:

```python
from knowledge.rag_manager import rag_manager

# Fetcha da tutti i sources
stats = rag_manager.fetch_all_sources()

# Ricerca migliorata con weighting
results = rag_manager.enhanced_search("SQL injection", top_k=5)
```

## 📊 Nuove Fonti Integrate

### ✅ Implementate

1. **OWASP Source** (`owasp_source.py`)
   - OWASP Top 10 2021
   - OWASP IoT Top 10 2024
   - Status: ✅ Completo

2. **NVD Source** (`nvd_source.py`)
   - NIST National Vulnerability Database
   - CVE recenti con CVSS
   - Status: ✅ Completo

3. **CVE Details Source** (`cve_details_source.py`)
   - CVE Details database
   - Status: 🔄 Struttura base (richiede scraping)

4. **SecurityFocus Source** (`securityfocus_source.py`)
   - SecurityFocus Bugtraq
   - Status: 🔄 Struttura base (richiede scraping)

### 🔄 Da Implementare

- Exploit-DB API (quando disponibile)
- HackerOne/Bugcrowd (API)
- Twitter/X security feeds
- Altri vendor blogs (Rapid7, Tenable, etc.)

## ⚙️ Configurazione

### File: `rag_config.json`

```json
{
  "sources": {
    "owasp": {
      "enabled": true,
      "priority": 8,
      "collection": "kb",
      "update_frequency": "weekly"
    },
    "nvd": {
      "enabled": true,
      "priority": 9,
      "collection": "cve",
      "update_frequency": "daily"
    }
  },
  "search": {
    "default_top_k": 5,
    "collection_weights": {
      "cve": 1.2,
      "exploits": 1.3,
      "successes": 1.5
    }
  }
}
```

### Abilitare/Disabilitare Fonti

Modifica `rag_config.json`:

```json
{
  "sources": {
    "owasp": {
      "enabled": false  // Disabilita OWASP
    }
  }
}
```

## 🚀 Utilizzo

### Fetch da Tutte le Fonti

```python
from knowledge.rag_manager import rag_manager

# Fetcha da tutti i sources abilitati
stats = rag_manager.fetch_all_sources()

print(f"OWASP: {stats['owasp']['fetched']} items")
print(f"NVD: {stats['nvd']['fetched']} items")
```

### Ricerca Migliorata

```python
# Ricerca con weighting automatico
results = rag_manager.enhanced_search(
    "SQL injection bypass",
    top_k=5,
    source_filter=['cve', 'exploits']  # Opzionale: filtra per source
)
```

### Aggiungere Nuovo Source

1. Crea nuovo file in `knowledge/sources/`:

```python
# knowledge/sources/my_source.py
from .base import DataSource, SourceResult

class MySource(DataSource):
    def fetch(self, **kwargs):
        # Implementa fetch
        return [SourceResult(...)]
    
    def get_source_info(self):
        return {'name': 'my_source', ...}
```

2. Registra in `sources/__init__.py`:

```python
from .my_source import MySource
registry.register(MySource())
```

3. Aggiungi config in `rag_config.json`

## 📈 Miglioramenti

### 1. Weighting Collections

Le collections ora hanno pesi configurabili:

- `successes`: 1.5x (più rilevante)
- `exploits`: 1.3x
- `cve`: 1.2x
- `tools`: 1.1x
- `kb`: 1.0x (base)

### 2. Filtering Migliorato

- Filtra per source specifici
- Filtra per min relevance score
- Riordina per distance pesata

### 3. Modularità

- Aggiungere nuovo source = 1 file + config
- Nessuna modifica al core necessario
- Testing isolato per source

## 🔄 Migrazione

### Da Vecchio Sistema

**Prima:**
```python
from knowledge import knowledge_enhancer
results = knowledge_enhancer.enhanced_search(query)
```

**Dopo (backward compatible):**
```python
from knowledge import knowledge_enhancer  # Ancora funziona
from knowledge.rag_manager import rag_manager  # Nuovo sistema
results = rag_manager.enhanced_search(query)  # Con weighting
```

### Compatibilità

- ✅ Vecchio `knowledge_enhancer` ancora funziona
- ✅ Nuovo `rag_manager` aggiunge funzionalità
- ✅ Graduale migrazione possibile

## 📊 Statistiche

```python
stats = rag_manager.get_stats()

# Collections
print(stats['collections'])

# Sources
print(stats['sources'])

# Config
print(stats['config'])
```

## 🎯 Prossimi Passi

1. ✅ Architettura modulare creata
2. ✅ OWASP e NVD integrati
3. 🔄 Implementare scraping per CVE Details
4. 🔄 Implementare scraping per SecurityFocus
5. 📅 Aggiungere più fonti (HackerOne, etc.)
6. 📅 Migliorare embeddings per distance più bassa

---

**Data:** 2025-01-XX  
**Versione:** 2.0  
**Status:** ✅ Architettura completa, fonti base implementate

