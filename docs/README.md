# 🧠 GhostBrain KaliAI

Piattaforma conversazionale AI avanzata per sicurezza informatica e penetration testing, integrata con Kali Linux knowledge base.

![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## 📋 Caratteristiche

- **🤖 AI Multi-Agente**: Orchestrazione con AutoGen per conversazioni intelligenti
- **📚 RAG (Retrieval Augmented Generation)**: Knowledge base Kali Linux con ricerca semantica
- **🧠 Memoria a Lungo Termine**: Vector database persistente con ChromaDB
- **🔍 Deep Search**: Ricerca web profonda con sintesi AI
- **🐳 Sandbox Sicura**: Esecuzione comandi isolata (Docker/subprocess)
- **📊 Monitoraggio**: Metriche Prometheus integrate
- **💾 Catalogazione Automatica**: Output organizzati per data/tipo

---

## 🚀 Quick Start

### 1. Prerequisiti

- Python 3.13+
- Docker (opzionale, per sandbox isolata)
- 4GB RAM minimo

### 2. Installazione

```bash
# Clona il repository
git clone <your-repo-url>
cd kaliAI

# Crea ambiente virtuale
python3 -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate

# Installa dipendenze
pip install -r requirements.txt
```

### 3. Configurazione

Crea un file `.env` nella root del progetto:

```bash
cp .env.example .env
```

Modifica `.env` con i tuoi valori:

```env
# API Configuration
OPENAI_API_KEY=your_deepseek_api_key_here
OPENAI_BASE_URL=https://api.deepseek.com/v1/

# Model
MODEL_NAME=deepseek-chat

# Docker Sandbox
USE_DOCKER_SANDBOX=true

# Flask
FLASK_ENV=development
FLASK_DEBUG=true
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### 4. Avvio

**Metodo 1 - Script automatico:**
```bash
./start.sh
```

**Metodo 2 - Manuale:**
```bash
source venv/bin/activate
export FLASK_APP=app.py
flask run --host=0.0.0.0 --port=5000
```

Apri il browser su: **http://localhost:5000**

---

## 🏗️ Architettura

```
kaliAI/
├── app.py                     # Flask application principale
├── modules/
│   ├── ghostbrain_autogen.py  # Orchestratore AI multi-agente
│   └── tools.py               # Strumenti RAG, memoria, sandbox
├── templates/                 # Template HTML (Jinja2)
├── static/                    # CSS, JS, risultati
│   └── results/               # Output catalogati per data
├── data/                      # Knowledge base Kali Linux
├── chroma_db/                 # Vector database persistente
└── test_env/                  # Sandbox per esecuzione comandi
```

### Flusso Dati

```
Utente → Flask → GhostBrain Agent → LLM API
                      ↓
                   Tools:
                   • RAG Search (ChromaDB)
                   • Memoria LTM
                   • Bash Sandbox
                   • Web Search
                      ↓
                  Risposta + Memoria
```

---

## 🔧 Utilizzo

### Chat Standard

1. Digita la tua domanda nella textarea
2. Premi **Invio** o clicca **"Invia"**
3. L'AI cercherà nella knowledge base e risponderà

### Ricerca Profonda

1. Clicca **"Ricerca Profonda"** per attivarla
2. Inserisci la query
3. Il sistema:
   - Cerca sul web (DuckDuckGo)
   - Scarica e analizza le pagine
   - Sintetizza in Markdown
   - Salva in `static/results/deepsearch/YYYY/MM/DD/`

### Deep Step

1. Inserisci un obiettivo complesso
2. Clicca **"Deep Step 🧩"**
3. L'AI scompone l'obiettivo in step operativi numerati

### Gestione Memoria

Visita: **http://localhost:5000/memory_page**

- Visualizza tutti i ricordi salvati
- Elimina ricordi specifici
- Esplora metadati

---

## 📊 API Endpoints

| Endpoint | Metodo | Descrizione |
|----------|--------|-------------|
| `/` | GET | Homepage interfaccia |
| `/ask` | POST | Chat standard con AI |
| `/deepsearch` | POST | Ricerca web profonda |
| `/deepstep` | POST | Genera step operativi |
| `/memory` | GET | Lista memorie LTM |
| `/memory/<id>` | DELETE | Elimina memoria |
| `/chat_history` | GET | Cronologia conversazioni |
| `/chat_history` | DELETE | Cancella cronologia |
| `/download/<path>` | GET | Download file risultati |
| `/metrics` | GET | Metriche Prometheus |

---

## 🐳 Docker Sandbox

Per abilitare la sandbox Docker isolata:

1. Installa Docker:
```bash
sudo apt install docker.io
sudo systemctl start docker
sudo usermod -aG docker $USER
```

2. Verifica in `.env`:
```env
USE_DOCKER_SANDBOX=true
```

3. Riavvia l'applicazione

I comandi bash saranno eseguiti in container Alpine isolati con:
- Nessun accesso rete
- Limite memoria 128MB
- Limite CPU 50%
- Utente `nobody`

---

## 📦 Struttura Output

I risultati vengono catalogati automaticamente:

```
static/results/
└── deepsearch/
    └── 2025/
        └── 10/
            └── 02/
                ├── kaliAI_update_02_10_2025_1430.md
                └── kaliAI_update_02_10_2025_1615.md
```

Organizzazione per:
- **Tipo**: deepsearch, eureka, galileo, etc.
- **Anno/Mese/Giorno**: struttura gerarchica
- **Timestamp**: HH:MM nel filename

---

## 🔒 Sicurezza

### Best Practices Implementate

✅ API keys in variabili ambiente (`.env`)  
✅ Sandbox comandi bash con whitelist  
✅ Path traversal protection per download  
✅ Isolamento Docker opzionale  
✅ Nessuna esecuzione codice arbitrario  

### Comandi Bloccati

Per sicurezza, questi pattern sono bloccati nella sandbox:
- `cd ../`, `../` (path traversal)
- `rm -rf /` (cancellazione sistema)
- `shutdown`, `reboot` (controllo sistema)
- `|`, `;`, `>`, `<` (redirezioni pericolose)
- `wget`, `curl`, `nc -e` (download/reverse shell)
- `python -c` (code injection)

---

## 🧪 Testing

```bash
# Test connessione API
python -c "from modules.ghostbrain_autogen import start_autogen_chat; print(start_autogen_chat('test'))"

# Test RAG
python -c "from modules.tools import rag_search_tool; print(rag_search_tool('nmap'))"

# Visualizza memorie
python show_memories.py
```

---

## 📈 Monitoraggio

Metriche Prometheus disponibili su: **http://localhost:5000/metrics**

Metriche esposte:
- `kaliai_requests_total`: Totale richieste AI
- `kaliai_requests_failed`: Richieste fallite
- `kaliai_chat_latency_seconds`: Latenza risposte

---

## 🐛 Troubleshooting

### Errore: "OPENAI_API_KEY non trovata"
```bash
# Verifica che .env esista e contenga la chiave
cat .env | grep OPENAI_API_KEY
```

### Errore: "Database RAG non inizializzato"
```bash
# Verifica che il file knowledge base esista
ls -lh data/kaliAI.md
```

### Porta 5000 già in uso
```bash
# Termina processo esistente
lsof -ti:5000 | xargs kill -9

# Oppure usa porta diversa
flask run --port=5001
```

### Docker non accessibile
```bash
# Aggiungi utente al gruppo docker
sudo usermod -aG docker $USER
newgrp docker

# Oppure disabilita Docker sandbox in .env
USE_DOCKER_SANDBOX=false
```

---

## 🤝 Contribuire

1. Fork il repository
2. Crea branch feature (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri Pull Request

---

## 📝 TODO

- [ ] Implementare visualizzazione grafo memoria (D3.js/PyVis)
- [ ] Integrazione KaTeX per rendering LaTeX
- [ ] Export conversazioni in PDF
- [ ] Dashboard analytics interattiva
- [ ] Multi-lingua support
- [ ] Voice input/output

---

## 📄 Licenza

MIT License - vedi [LICENSE](LICENSE) per dettagli

---

## 👤 Autore

**GhostFrame**

- Progetto: KaliAI - Eureka Edition
- AI Model: DeepSeek Chat
- Framework: AutoGen + Flask

---

## 🙏 Riconoscimenti

- [AutoGen](https://github.com/microsoft/autogen) - Microsoft
- [ChromaDB](https://www.trychroma.com/) - Vector database
- [LangChain](https://www.langchain.com/) - RAG framework
- [DeepSeek](https://www.deepseek.com/) - LLM provider

---

**Made with 💚 for the Cybersecurity Community**

