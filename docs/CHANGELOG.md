# Changelog KaliAI

Tutte le modifiche notevoli al progetto saranno documentate in questo file.

## [2.0.0] - 2025-10-02

### 🎉 Rilascio Maggiore - Refactoring Completo

### ✨ Aggiunte

- **Gestione Configurazione con .env**: Migrazione completa da `config.json` a variabili ambiente
  - File `.env.example` per template configurazione
  - Supporto per `python-dotenv`
  - API keys non più hardcoded nel codice

- **Sistema di Catalogazione Output**: Organizzazione automatica risultati
  - Struttura gerarchica: `results/{tipo}/{anno}/{mese}/{giorno}/`
  - Timestamp completi nei filename
  - Prevenzione sovrascrittura file

- **Logging Strutturato**: Implementazione `logging` module Python
  - Log levels configurabili
  - Formato unificato `[MODULE] message`
  - Console output ridotto (rispetto preferenze utente)

- **Endpoint REST Mancanti**:
  - `DELETE /chat_history` per cancellare cronologia
  - Path traversal protection per `/download/<path:filename>`

- **Stili CSS Deep Steps Panel**: 
  - Pannello animato per visualizzazione step operativi
  - Design responsive con gradiente hacker-style
  - Effetti hover e transizioni fluide

- **Documentazione Completa**:
  - `README.md` con guida setup, architettura, troubleshooting
  - `CHANGELOG.md` per tracciamento versioni
  - Commenti JSDoc e docstring Python

- **File di Progetto Essenziali**:
  - `requirements.txt` con versioni specifiche dipendenze
  - `.gitignore` completo per Python/Flask/Chroma
  - Script `start.sh` migliorato con validazione `.env`

### 🔧 Modifiche

- **Refactor `ghostbrain_autogen.py`**:
  - Caricamento config da variabili ambiente
  - Logging strutturato al posto di `print()`
  - Gestione errori migliorata

- **Refactor `tools.py`**:
  - Fix dipendenza circolare in `generate_deep_steps()`
  - Import lazy per `start_autogen_chat`
  - Configurazione sandbox da env var

- **Refactor `app.py`**:
  - Endpoint `/api/model` legge da env
  - Funzione `get_catalogued_path()` per output organizzati
  - Fix chiamate doppie a `start_autogen_chat()` in deepsearch
  - Download file con supporto sottodirectory

### 🐛 Fix

- **Bug Critico**: Dipendenza circolare tra `tools.py` e `ghostbrain_autogen.py`
  - Risolto con import lazy nella funzione
  
- **Bug Sicurezza**: API key esposta in `config.json`
  - Migrata a `.env` (non tracciato da git)
  
- **Bug UX**: Codice JavaScript duplicato in `script.js`
  - Rimosso listener `searchBtn` duplicato (linee 322-345)
  
- **Bug CSS**: Stili duplicati in `memory.html`
  - Consolidati in blocco `<style>` unico

- **Bug Funzionale**: Chiamata multipla a `start_autogen_chat()` in deepsearch
  - Ora salva il risultato in variabile prima dell'uso

### 🔒 Sicurezza

- API keys migrate da file tracciato a `.env`
- `.env` aggiunto a `.gitignore`
- Path normalization per download file
- Validazione esistenza `.env` in `start.sh`

### 📝 Documentazione

- README completo con:
  - Quick start guide
  - Diagramma architettura
  - Tabella API endpoints
  - Troubleshooting comune
  - Best practices sicurezza

### ⚡ Performance

- Logging configurabile per ridurre output console
- Rimozione chiamate duplicate API
- Lazy import per evitare circular dependencies

### 🎨 UI/UX

- Pannello Deep Steps con animazioni fluide
- Stili consolidati e ottimizzati
- Responsive design migliorato

---

## [1.0.0] - 2025-06-29

### 🎉 Release Iniziale

- Sistema conversazionale AI con AutoGen
- RAG su knowledge base Kali Linux
- Memoria a lungo termine con ChromaDB
- Deep Search con DuckDuckGo
- Sandbox bash sicura
- Interface web Flask con Matrix theme
- Cronologia chat persistente
- Metriche Prometheus

---

**Formato basato su [Keep a Changelog](https://keepachangelog.com/)**

