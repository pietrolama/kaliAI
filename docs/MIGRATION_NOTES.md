# 📋 Note di Migrazione - KaliAI v2.0

## ⚠️ IMPORTANTE: Azioni Richieste

### 1. Installazione Dipendenze
```bash
pip install -r requirements.txt
```

Nuove dipendenze aggiunte:
- `python-dotenv==1.0.1` (gestione variabili ambiente)

### 2. Configurazione .env

Il file `config.json` **NON è più utilizzato**. Configurazione spostata in `.env`:

```bash
# Se non esiste già
cp .env.example .env

# Verifica che contenga la tua API key
cat .env | grep OPENAI_API_KEY
```

⚠️ **Backup della vecchia chiave API**: 
```
Old location: config.json (api_key)
New location: .env (OPENAI_API_KEY)
Value: sk-6473748545d34e2796fb04725443b367
```

### 3. Verifica Permessi
```bash
chmod +x start.sh
```

---

## 🔄 Breaking Changes

### Configurazione
- ❌ `config.json` deprecato
- ✅ `.env` ora obbligatorio
- ✅ Variabili ambiente richieste:
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `MODEL_NAME`

### API Endpoints
- ✅ Nuovo: `DELETE /chat_history`
- ⚠️ Modificato: `/download/<path:filename>` supporta sottodirectory

### Struttura Output
**Prima:**
```
static/results/
├── kaliAI_update_02_10_2025.md
└── kaliAI_update_02_10_2025.md  ← Sovrascrive!
```

**Dopo:**
```
static/results/deepsearch/
└── 2025/
    └── 10/
        └── 02/
            ├── kaliAI_update_02_10_2025_1430.md
            └── kaliAI_update_02_10_2025_1615.md  ← No sovrascritture
```

---

## ✅ Compatibilità

### File Non Modificati
Questi file mantengono compatibilità totale:
- `templates/index.html`
- `static/script.js` (rimosso solo duplicato)
- `static/style.css` (aggiunti solo nuovi stili)
- `data/kaliAI.md`
- `chroma_db/` (database vettoriale)

### Funzionalità Retrocompatibili
- ✅ Chat standard
- ✅ RAG search
- ✅ Memoria a lungo termine
- ✅ Cronologia chat
- ✅ Deep search
- ✅ Metriche Prometheus

---

## 🐛 Bug Risolti

### Critici
1. **Dipendenza Circolare**: `tools.py` ↔ `ghostbrain_autogen.py`
   - Fix: Import lazy in `generate_deep_steps()`

2. **API Key Esposta**: Presente in `config.json` tracciato da git
   - Fix: Migrata a `.env` (escluso da git)

3. **Chiamata Doppia API**: `start_autogen_chat()` chiamato 3 volte in deepsearch
   - Fix: Risultato salvato in variabile

### Minori
1. **Codice JavaScript Duplicato**: Listener `searchBtn` x2
2. **Stili CSS Duplicati**: `memory.html` con 2 blocchi `<style>`
3. **Mancanza Stili**: `#deep-steps-panel` non stilizzato
4. **Endpoint Mancante**: `DELETE /chat_history` chiamato ma non esistente

---

## 🔒 Sicurezza

### Migliorate
- ✅ API keys in `.env` (non tracciato)
- ✅ `.gitignore` completo
- ✅ Path traversal protection migliorato
- ✅ Logging configurabile (no info sensibili)

### Da Implementare (Future)
- [ ] Rate limiting su endpoints API
- [ ] JWT authentication per API
- [ ] HTTPS obbligatorio in production
- [ ] Audit log per azioni critiche

---

## 📦 Nuovi File

### Obbligatori
- `.env` - Configurazione ambiente (da creare!)
- `requirements.txt` - Dipendenze Python

### Documentazione
- `README.md` - Guida completa
- `CHANGELOG.md` - Storico versioni
- `MIGRATION_NOTES.md` - Questo file

### Template
- `.env.example` - Template configurazione
- `.gitignore` - File da escludere da git

---

## 🚀 Testing Post-Migrazione

### 1. Test Base
```bash
# Attiva venv
source venv/bin/activate

# Verifica .env
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key:', os.getenv('OPENAI_API_KEY')[:10] + '...')"

# Avvia app
./start.sh
```

### 2. Test Funzionalità
- [ ] Chat standard funziona
- [ ] Deep search salva file in `results/deepsearch/YYYY/MM/DD/`
- [ ] Deep step genera lista numerata
- [ ] Cronologia chat carica
- [ ] Memoria LTM accessibile
- [ ] Delete cronologia funziona
- [ ] Download file funziona

### 3. Test Logging
```bash
# Verifica output console ridotto
# Dovrebbe mostrare solo [APP], [GhostBrain], [TOOLS], non "[APP] ..." ripetuto
```

### 4. Test API
```bash
# Model info
curl http://localhost:5000/api/model

# Metriche
curl http://localhost:5000/metrics

# Chat
curl -X POST http://localhost:5000/ask \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}'
```

---

## 🔄 Rollback (Se Necessario)

Se riscontri problemi:

### Opzione 1: Ripristina config.json
```bash
# In ghostbrain_autogen.py, sostituisci load_llm_config_from_env() con:
def load_raw_config():
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        if not isinstance(config, list):
            config = [config]
        return config
    except Exception as e:
        log_info(f"[ERRORE] Caricamento config.json: {e}")
        return []
```

### Opzione 2: Usa backup
```bash
git stash  # Salva modifiche locali
git checkout HEAD~1  # Torna a versione precedente
```

---

## 📞 Supporto

In caso di problemi:

1. Verifica `.env` esista e sia valido
2. Controlla log console per errori
3. Verifica dipendenze: `pip list | grep -E "(dotenv|autogen|chromadb)"`
4. Testa connessione API: `curl https://api.deepseek.com/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"`

---

**Data Migrazione**: 2 Ottobre 2025  
**Versione Target**: 2.0.0  
**Python Version**: 3.13+

