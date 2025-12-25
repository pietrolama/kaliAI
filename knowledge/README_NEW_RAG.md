# 🚀 Nuova RAG - Quick Start

## ✅ Cosa è Cambiato

La RAG è stata completamente riprogettata con architettura modulare.

### Nuove Funzionalità

1. **Sistema Modulare Fonti**
   - Aggiungi nuove fonti facilmente
   - Configurazione centralizzata
   - Auto-registrazione

2. **Nuove Fonti Integrate**
   - ✅ OWASP Top 10
   - ✅ NIST NVD completo
   - 🔄 CVE Details (struttura base)
   - 🔄 SecurityFocus (struttura base)

3. **Ricerca Migliorata**
   - Weighting collections
   - Filtering avanzato
   - Relevance scoring

## 🎯 Utilizzo Rapido

### Fetch da Nuove Fonti

```python
from knowledge.rag_manager import rag_manager

# Fetcha da tutti i sources abilitati
stats = rag_manager.fetch_all_sources()
```

### Ricerca con Weighting

```python
# Ricerca migliorata con weighting automatico
results = rag_manager.enhanced_search("SQL injection", top_k=5)
```

### Configurazione

Modifica `knowledge/rag_config.json` per:
- Abilitare/disabilitare fonti
- Configurare pesi collections
- Impostare parametri fetch

## 📚 Documentazione Completa

Vedi `docs/RAG_REDESIGN.md` per dettagli completi.

