# 📁 KaliAI Project Structure v3.0

Struttura completamente riorganizzata seguendo best practices per progetti Python enterprise.

## 🎯 Architettura

```
kaliAI/                              # Root del progetto
│
├── run.py ⚡                         # Entry point principale
├── start.sh                         # Script avvio (wrapper)
├── requirements.txt                 # Dipendenze
├── .env                             # Environment vars (git-ignored)
└── .env.example                     # Template env
```

---

## 🖥️ Backend (`backend/`)

Backend completo con architettura a 3 layer.

```
backend/
├── __init__.py                      # Package init
├── app.py                           # Flask application
│
├── core/                            # Core Business Logic
│   ├── __init__.py
│   ├── ghostbrain_autogen.py        # LLM + AutoGen (400 linee)
│   ├── smart_context_builder.py     # Context + RAG (300 linee)
│   ├── step_executor_improved.py    # Adaptive executor (550 linee)
│   ├── command_validator.py         # Command validation (320 linee)
│   └── tools.py                     # Tool collection (1100 linee)
│
├── api/                             # REST API Endpoints (future)
│   └── __init__.py
│       ├── chat.py                  # Planned: /api/chat
│       ├── steps.py                 # Planned: /api/deepstep
│       └── knowledge.py             # Planned: /api/rag
│
└── database/                        # Database Layer (future)
    └── __init__.py
        ├── models.py                # Planned: DB models
        └── migrations/              # Planned: DB migrations
```

**Total**: ~2,700 linee di codice backend

---

## 📚 Knowledge System (`knowledge/`)

Sistema completo di gestione conoscenza.

```
knowledge/
├── __init__.py                      # Package exports
├── knowledge_enhancer.py            # Core ChromaDB (340 linee)
├── knowledge_fetcher.py             # Fetching fonti (320 linee)
├── exploit_hunter.py                # Hunting exploit (500 linee)
├── improve_knowledge.py             # Miglioramento manuale (170 linee)
├── exploit_hunter_config.json       # Configurazione
├── README.md                        # Documentazione knowledge
│
├── scripts/                         # Automazione
│   ├── update_knowledge.sh          # Update completo
│   └── hunt_exploits.sh             # Exploit hunting
│
└── docs/                            # Documentazione specifica
    ├── EXPLOIT_HUNTER.md
    ├── INTEGRAZIONE_RAG.md
    └── KNOWLEDGE_SYSTEM.md
```

**Total**: ~1,800 linee
**Collections**: 5 (kali_kb, exploits, cve, successes, tools)
**Documents**: 298 documenti vettorizzati

---

## 🔧 Tools (`tools/`)

Utility e gestione sistema.

```
tools/
├── __init__.py
├── tool_manager.py                  # Gestione tool
├── memory_manager.py                # Gestione memoria
├── caching.py                       # Sistema caching
├── monitoring.py                    # Monitoring e metriche
├── security.py                      # Security layer
└── error_handling.py                # Gestione errori
```

**Total**: ~1,200 linee

---

## 🎨 Frontend (`frontend/`)

Interfaccia utente completa.

```
frontend/
├── templates/                       # Template HTML
│   ├── index.html                   # UI principale (110 linee)
│   └── memory.html                  # Memory viewer
│
└── static/                          # Assets statici
    ├── script.js                    # JavaScript UI (960 linee)
    ├── style.css                    # Styling (800 linee)
    ├── chat_history.json            # Storia conversazioni
    └── results/                     # Output esecuzioni
```

**Total**: ~1,900 linee (HTML+CSS+JS)

---

## ⚙️ Config (`config/`)

File di configurazione.

```
config/
├── config.json                      # Configurazione generale
└── config.py                        # Configurazione Python
```

---

## 📊 Data (`data/`)

Knowledge sources e cache.

```
data/
├── kaliAI.md                        # KB principale (20 KB)
├── google_home_vulnerabilities.md   # CVE Google Home
├── kali_guide.json                  # Guida strutturata
├── knowledge_cache/                 # Cache download
└── exploit_cache/                   # Cache exploit
```

---

## 📝 Scripts (`scripts/`)

Script utility standalone.

```
scripts/
├── show_memories.py                 # Visualizza memorie
├── install_pentest_tools.py         # Installer tool
└── wiz_control.py                   # Controller WiZ lights
```

---

## 📚 Docs (`docs/`)

Documentazione completa centralizzata.

```
docs/
├── README.md                        # Overview progetto
├── PROJECT_STRUCTURE_V3.md          # Questa struttura
├── QUICKSTART.md                    # Quick start guide
├── CHANGELOG.md                     # Change log
├── IMPROVEMENTS.md                  # Miglioramenti
├── FIX_GOOGLE_HOME_TEST.md          # Fix test Google Home
├── VALIDATOR_IMPROVEMENTS.md        # Miglioramenti validator
├── INTELLIGENT_SYSTEM.md            # Sistema intelligente
├── SISTEMA_INTELLIGENTE.md          # Versione italiana
├── TOOL_MANAGEMENT.md               # Gestione tool
├── UNIFIED_WORKFLOW.md              # Workflow unificato
├── TEST_WORKFLOW.md                 # Test workflow
├── TEST_CHAT.md                     # Test chat
└── RIEPILOGO_FINALE.md              # Riepilogo
```

**Total**: 15+ documenti, ~8,000 linee

---

## 🧪 Tests (`tests/`)

Test suite completa (future expansion).

```
tests/
├── __init__.py
└── test_security.py                 # Test security layer
    ├── test_validator.py            # Planned
    ├── test_rag.py                  # Planned
    └── test_executor.py             # Planned
```

---

## 💾 Database (`chroma_db/`)

Database vettoriale ChromaDB.

```
chroma_db/
├── kali_linux_kb/                   # 140 documenti
├── exploits_db/                     # 15 documenti
├── cve_database/                    # 143 documenti
├── successful_attacks/              # 0 documenti
└── tool_manuals/                    # 0 documenti
```

**Total**: 298 documenti vettorizzati

---

## 🔄 Flow di Esecuzione

### 1. **Startup**
```
start.sh
    ↓
run.py
    ↓
backend/app.py
    ├─ Carica backend/core/ghostbrain_autogen
    ├─ Carica backend/core/tools
    └─ Inizializza ChromaDB (knowledge/)
```

### 2. **Request Handling**
```
User HTTP Request
    ↓
backend/app.py (Flask routes)
    ↓
backend/core/tools.py (execute_step_by_step)
    ├─ backend/core/smart_context_builder (network + RAG)
    ├─ backend/core/step_executor_improved (execution)
    └─ backend/core/command_validator (validation)
    ↓
tools/security.py (security check)
    ↓
Response to User
```

### 3. **Knowledge Updates**
```
knowledge/scripts/update_knowledge.sh
    ├─ knowledge/knowledge_fetcher.py (CISA, NVD, RSS)
    └─ knowledge/exploit_hunter.py (GitHub, Exploit-DB)
        ↓
    knowledge/knowledge_enhancer.py (ChromaDB indexing)
        ↓
    chroma_db/ (vector store)
```

---

## 📊 Statistiche Progetto

### Codice Sorgente
```
Totale file: ~65 (escluso venv)
Totale righe: ~20,000+

Breakdown per modulo:
  backend/core/:  ~2,700 linee
  knowledge/:     ~1,800 linee
  tools/:         ~1,200 linee
  frontend/:      ~1,900 linee
  backend/app.py: ~400 linee
  docs/:          ~8,000 linee
  tests/:         ~200 linee
  scripts/:       ~300 linee
```

### Knowledge Base
```
Documenti: 298 totali
  • kali_kb: 140 (conoscenza generale)
  • exploits: 15 (exploit specifici)
  • cve: 143 (database CVE)
  • successes: 0 (success cases)
  • tools: 0 (manuali)

Fonti: 12+
  - CISA KEV
  - NVD API
  - GitHub
  - Exploit-DB
  - Packet Storm
  - Google Project Zero
  - Reddit
  - RSS feeds
```

---

## 🔗 Import Structure

### Prima (v2.0):
```python
from modules.tools import execute_step_by_step
from knowledge_enhancer import knowledge_enhancer
from security import security_check
```

### Dopo (v3.0):
```python
from backend.core.tools import execute_step_by_step
from knowledge import knowledge_enhancer
from tools.security import security_check
```

**Vantaggi**:
- ✅ Namespace puliti
- ✅ Nessuna ambiguità
- ✅ Standard Python package structure

---

## 🚀 Quick Start

```bash
# 1. Attiva ambiente
cd /home/ghostframe/HACK/kaliAI
source venv/bin/activate

# 2. Avvia sistema (metodo raccomandato)
./start.sh

# 3. Oppure avvia diretto
python run.py

# 4. Accedi UI
http://localhost:5000
```

---

## 🛠️ Development

### Aggiungere Nuovo Modulo Backend
```bash
# Crea file in backend/core/
touch backend/core/my_module.py

# Esporta da __init__.py
echo "from .my_module import *" >> backend/core/__init__.py
```

### Aggiungere Nuova API Route
```bash
# Crea file in backend/api/
touch backend/api/my_endpoint.py

# Registra in backend/app.py
```

### Aggiungere Fonte Knowledge
```bash
# Modifica knowledge/exploit_hunter.py
# Aggiungi metodo fetch_new_source()
# Registra in hunt_all()
```

---

## 📦 Package Structure

### Root Level Packages:
```python
kaliAI/
├── backend         # Backend package
├── frontend        # Frontend assets (no Python)
├── knowledge       # Knowledge package
├── tools           # Tools package
├── config          # Config package (future)
├── scripts         # Standalone scripts (no package)
├── tests           # Test package
└── docs            # Documentation (no package)
```

### Import Paths:
```python
from backend.core import tools
from backend.core.ghostbrain_autogen import start_autogen_chat
from knowledge import knowledge_enhancer, fetcher, exploit_hunter
from tools.security import SecurityValidator
from tools.memory_manager import load_chat_history
```

---

## 🔄 Migration da v2.0 a v3.0

### File Spostati:

| v2.0 Location | v3.0 Location |
|---------------|---------------|
| `modules/` | `backend/core/` |
| `app.py` | `backend/app.py` |
| `templates/` | `frontend/templates/` |
| `static/` | `frontend/static/` |
| `security.py` | `tools/security.py` |
| `memory_manager.py` | `tools/memory_manager.py` |
| `tool_manager.py` | `tools/tool_manager.py` |
| `*.md` | `docs/*.md` |
| Root scripts | `scripts/` |
| `config.json` | `config/config.json` |

### Import Changes:

```python
# v2.0
from modules.tools import execute_step_by_step
from security import security_check

# v3.0  
from backend.core.tools import execute_step_by_step
from tools.security import security_check
```

---

## ✅ Verifiche Post-Migration

```bash
# 1. Test import
python -c "from backend.app import app; print('✅ OK')"

# 2. Test knowledge
python -c "from knowledge import knowledge_enhancer; print(knowledge_enhancer.get_stats())"

# 3. Test avvio
python run.py
# Oppure
./start.sh

# 4. Test frontend
curl http://localhost:5000
```

---

## 🎯 Benefici Nuova Struttura

### 1. **Modularità Migliorata**
- Separazione chiara backend/frontend/knowledge
- Ogni package ha responsabilità definita
- Facile testing isolato

### 2. **Scalabilità**
- Pronto per microservizi (backend/api)
- Pronto per database layer separato
- Struttura per team development

### 3. **Manutenibilità**
- Path chiari e logici
- Import namespace puliti
- Documentazione centralizzata

### 4. **Professionalità**
- Standard Python package structure
- Seguono PEP 8 recommendations
- Production-ready

---

## 🔮 Roadmap Future

### Phase 1 (Completato) ✅
- ✅ Separazione backend/frontend
- ✅ Package knowledge standalone
- ✅ Tool utilities separati
- ✅ Documentazione centralizzata

### Phase 2 (In Progress)
- 🔄 API REST layer (backend/api/)
- 🔄 Database layer (backend/database/)
- 🔄 Test suite completa
- 🔄 CI/CD pipeline

### Phase 3 (Planned)
- ⏳ Docker containerization
- ⏳ Setup.py per installazione
- ⏳ Plugin system
- ⏳ Multi-model support

---

## 🎨 File Tree Completa

```
kaliAI/
├── backend/
│   ├── core/                        # 5 file, 2700 linee
│   ├── api/                         # Vuota (planned)
│   ├── database/                    # Vuota (planned)
│   └── app.py                       # 400 linee
│
├── frontend/
│   ├── templates/                   # 2 file HTML
│   └── static/                      # JS, CSS, JSON
│
├── knowledge/
│   ├── scripts/                     # 2 script bash
│   ├── docs/                        # 3 documenti MD
│   └── 4 moduli Python              # 1800 linee
│
├── tools/                           # 6 moduli utility
├── config/                          # 2 file configurazione
├── data/                            # 5 file KB + cache
├── docs/                            # 15+ documenti MD
├── scripts/                         # 3 script utility
├── tests/                           # Test suite
├── test_env/                        # Environment test
├── examples/                        # Esempi uso
│
├── run.py                           # Entry point
├── start.sh                         # Launcher
├── requirements.txt
├── .env
└── .env.example
```

---

## 📈 Metrics

- **Directories**: 22
- **Python files**: ~40
- **Documentation files**: ~20
- **Total lines of code**: ~20,000
- **Test coverage**: TBD
- **Knowledge documents**: 298

---

**Version**: 3.0.0  
**Data Restructure**: 3 Ottobre 2025  
**Status**: ✅ Production Ready

