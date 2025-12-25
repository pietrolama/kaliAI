# 🚀 Quick Start - Nuovi Miglioramenti KaliAI

## Installazione Dipendenze

```bash
cd /home/ghostframe/HACK/kaliAI
source venv/bin/activate
pip install -r requirements.txt
```

## Verifica Configurazione

```bash
python -c "from config import config; config.validate(); print('✅ Config OK')"
```

## Esegui Test Sicurezza

```bash
python -m pytest tests/test_security.py -v
```

## Esempio Completo

```bash
python examples/usage_example.py
```

## Integrazione nei Moduli Esistenti

### 1. Usa Configurazione Centralizzata

**Prima:**
```python
api_key = os.getenv('OPENAI_API_KEY')
base_url = os.getenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1/')
```

**Dopo:**
```python
from config import config

api_key = config.OPENAI_API_KEY
base_url = config.OPENAI_BASE_URL
```

### 2. Validazione Comandi

**Prima:**
```python
# Blocco manuale comandi pericolosi
if "rm -rf" in command or "sudo" in command:
    return "Comando bloccato"
```

**Dopo:**
```python
from security import SecurityValidator

is_valid, reason = SecurityValidator.validate_command(command)
if not is_valid:
    return f"Bloccato: {reason}"
```

### 3. Cache LLM

**Prima:**
```python
# Ogni volta chiama API (costoso)
response = client.chat.completions.create(...)
```

**Dopo:**
```python
from caching import response_cache

cached = response_cache.get(prompt, temperature)
if cached:
    return cached
    
response = client.chat.completions.create(...)
response_cache.set(prompt, response, temperature)
```

### 4. Monitoring

**Prima:**
```python
# Nessun tracking
result = call_llm(prompt)
```

**Dopo:**
```python
from monitoring import metrics_collector
import time

start = time.time()
result = call_llm(prompt)
duration = time.time() - start

metrics_collector.track_llm_call(duration, True, model_name)
```

### 5. Smart Memory Recall

**Prima:**
```python
# Recall semplice
results = collection.query(query_texts=[query], n_results=top_k)
```

**Dopo:**
```python
from memory_manager import memory_manager

# Recall con ranking intelligente (importanza + recentezza + rilevanza)
results = memory_manager.smart_recall(
    query=query,
    top_k=3,
    min_importance=5.0,
    recency_weight=0.3
)
```

## Metriche in Tempo Reale

```python
from monitoring import metrics_collector
from caching import get_cache_stats
from security import auditor

# Stampa statistiche
print("=== METRICHE ===")
print(metrics_collector.get_metrics())
print(get_cache_stats())
print(auditor.get_stats())
```

## Variabili Ambiente Consigliate

Aggiungi al `.env`:

```bash
# Performance
CACHE_ENABLED=true
CACHE_MAX_SIZE=1000
MAX_STEP_RETRIES=3
COMMAND_TIMEOUT=30
LLM_TIMEOUT=60

# Memory
MEMORY_TOP_K=3
```

## API Principali

### Config
```python
from config import config
config.validate()
config.OPENAI_API_KEY
config.get_llm_config()
```

### Security
```python
from security import SecurityValidator, auditor
is_valid, reason = SecurityValidator.validate_command(cmd)
stats = auditor.get_stats()
```

### Caching
```python
from caching import response_cache
response_cache.get(prompt, temp)
response_cache.set(prompt, result, temp)
```

### Monitoring
```python
from monitoring import metrics_collector
metrics_collector.track_llm_call(duration, success, model)
metrics_collector.get_metrics()
```

### Memory
```python
from memory_manager import memory_manager
memory_manager.add_memory(content, metadata, importance)
memory_manager.smart_recall(query, top_k=3)
```

### Error Handling
```python
from error_handling import safe_execute

@safe_execute("Errore", default_return=None)
def risky_function():
    # Codice che potrebbe fallire
    pass
```

## Troubleshooting

### ImportError: No module named 'psutil'
```bash
pip install psutil
```

### ConfigurationError: OPENAI_API_KEY mancante
```bash
echo "OPENAI_API_KEY=sk-xxxxx" >> .env
```

### SecurityError: Comando bloccato
Verifica che il comando non sia in blacklist:
```python
from security import SecurityValidator
print(SecurityValidator.BLOCKED_COMMANDS)
print(SecurityValidator.BLOCKED_PATTERNS)
```

## Performance Tips

1. **Cache abilitata**: Riduce chiamate API del 30-70%
2. **Min importance**: Filtra memorie non rilevanti
3. **Top_k limitato**: Usa 3-5 per velocità ottimale
4. **Cleanup memoria**: Esegui periodicamente cleanup memorie vecchie

```python
memory_manager.cleanup_old_memories(days=30, keep_important=True)
```

## Best Practices

1. ✅ Valida sempre comandi con `SecurityValidator`
2. ✅ Usa cache per prompt ripetuti
3. ✅ Traccia metriche per debugging
4. ✅ Salva memorie con importanza appropriata
5. ✅ Gestisci errori con decorators `@safe_execute`
6. ✅ Monitora statistiche periodicamente
7. ✅ Cleanup memorie vecchie mensilmente

## Prossimi Passi

1. Leggi `IMPROVEMENTS.md` per dettagli implementazione
2. Esplora `examples/usage_example.py` per esempi pratici
3. Esegui test: `pytest tests/ -v`
4. Integra gradualmente nei tuoi moduli
5. Monitora metriche e ottimizza

## Supporto

Documentazione completa: `IMPROVEMENTS.md`
Esempi: `examples/usage_example.py`
Test: `tests/test_security.py`

