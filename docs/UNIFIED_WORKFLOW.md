# 🔄 Unified Workflow - Step + Chat Integrati

## 🎯 Problema Risolto

### PRIMA (Separato)
```
1. User: "hacka la telecamera"
2. Sistema: [Esegue step] → FINE
3. User deve ricominciare da zero per domande ❌
```

### DOPO (Unificato)
```
1. User: "hacka la telecamera"
2. Sistema: [Esegue step automatici]
3. Sistema: [Switch automatico a Chat Mode]
4. Sistema: "✅ Step completati. Hai domande?"
5. User: "Perché step 3 è fallito?" ✅
6. AI: [Risponde con contesto completo degli step]
```

## 🚀 Come Funziona

### Flow Automatico

```
┌─────────────────────────────────────────────┐
│  USER: "obiettivo complesso"                │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  STEP MODE: Esecuzione automatica           │
│  1. Target extraction                        │
│  2. Step generation                          │
│  3. Execution con retry                      │
│  4. Monitoring + security                    │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  TRANSITION: Switch automatico               │
│  - Genera summary risultati                  │
│  - Costruisce contesto completo              │
│  - Passa a Chat Mode                         │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────┐
│  CHAT MODE: Follow-up interattivo            │
│  AI ha TUTTO il contesto degli step          │
│  User può fare domande specifiche            │
│  AI suggerisce prossimi passi                │
└───────────────────────────────────────────────┘
```

## 💡 Esempio Pratico

### Esecuzione

**1. User invia (Deep Step):**
```
"analizza http://192.168.1.6:8000 e trova credenziali"
```

**2. Sistema esegue automaticamente:**
```
[STEP 1/5] ✅ nmap scan → porta 8000 aperta
[STEP 2/5] ⚠️ curl → connessione chiusa
[STEP 3/5] ❌ hydra brute force → timeout
[STEP 4/5] ❌ directory busting → tool mancante
[STEP 5/5] ⚠️ manual access → impossibile
```

**3. Sistema passa a Chat Mode:**
```
┌───────────────────────────────────────┐
│ ✅ 2/5 step completati                │
│                                        │
│ 💬 CHAT MODE ATTIVA                   │
│ Hai domande sui risultati?            │
└───────────────────────────────────────┘
```

**4. User chiede (Chat):**
```
"Perché step 2 è fallito? Dammi comandi alternativi"
```

**5. AI risponde con contesto:**
```
Lo step 2 (curl) è fallito perché la telecamera chiude
attivamente le connessioni HTTP.

Comandi alternativi:
1. Usa telnet raw: printf "GET / HTTP/1.1\r\n..." | nc 192.168.1.6 8000
2. Prova porta 9010 (streaming): curl http://192.168.1.6:9010
3. Browser diretto: firefox http://192.168.1.6:8000
```

**6. User continua (Chat):**
```
"Esegui il comando telnet per me"
```

**7. AI esegue:**
```
[Esegue comando] → Risultato
```

## 📊 Contesto Disponibile in Chat

Quando passi in Chat Mode dopo gli step, l'AI ha:

- ✅ Obiettivo originale
- ✅ Tutti gli step eseguiti (successi + fallimenti)
- ✅ Comandi eseguiti
- ✅ Output completi
- ✅ Errori incontrati
- ✅ Target identificato
- ✅ Tool usati

## 🎮 User Experience

### Interfaccia

**Durante Step Mode:**
```
[Terminal] 
  ━━━ STEP 1 ━━━ Scanning target...
  [OK] Step 1 completed
  
  ━━━ STEP 2 ━━━ Testing authentication...
  [ERROR] Connection refused
```

**Dopo Switch:**
```
[Chat Area]
  ╔════════════════════════════════════╗
  ║ ✅ 3/5 step completati            ║
  ╚════════════════════════════════════╝
  
  💬 Chat Mode Attiva
  
  Esempi domande:
  • Perché step X fallito?
  • Come completo Y?
  • Suggerisci prossimi passi
  
  [Input field in focus, pronto per domande]
```

## 🔧 Implementazione Tecnica

### Backend (app.py)

```python
# Dopo completamento step
unified_workflow._build_chat_context(
    objective=prompt,
    step_results=step_results,
    completed=completed
)

# Emetti evento
emit({
    "type": "chat_ready",
    "context": chat_context,
    "summary": "3/5 step completati",
    "message": "Chat attiva per follow-up"
})
```

### Frontend (script.js)

```javascript
case "chat_ready":
    // Switch automatico a chat mode
    switchToMode("chat");
    
    // Mostra invito
    addMessage(event.message, "bot");
    
    // Salva contesto
    window.lastStepContext = {...};
    
    // Focus input
    input.focus();
```

### Chat con Contesto (/ask)

```python
# Se use_step_context=True
user_input = unified_workflow.format_for_chat_prompt(user_input)

# Include automaticamente:
# - Step completati
# - Errori incontrati  
# - Output importanti
```

## ✅ Vantaggi

**1. Continuità**
- Non perdi il contesto degli step
- Follow-up naturale
- No ripetizioni

**2. Debugging Assistito**
- "Perché fallito?" → AI spiega con contesto
- "Come fisso?" → AI suggerisce alternative
- "Cosa fare dopo?" → AI continua il ragionamento

**3. Flessibilità**
- Step automatici per task complessi
- Chat interattiva per troubleshooting
- Best of both worlds

**4. Efficienza**
- Un solo workflow invece di due separati
- Contesto condiviso
- No duplicazioni

## 🎯 Use Cases

### 1. Pentest Complesso

```
Deep Step: "fai pentest completo su target.com"
→ [5 step automatici, 3 completati, 2 falliti]
→ Chat Mode: "Perché SQL injection fallita?"
→ AI: "WAF rilevato. Prova con sqlmap --tamper..."
```

### 2. IoT Hacking

```
Deep Step: "trova e hacka dispositivi IoT"
→ [Trova WiZ, la hacka]
→ Chat Mode: "Come cambio colore?"
→ AI: "Usa: echo '{"r":255...}' | nc -u ..."
```

### 3. Network Analysis

```
Deep Step: "analizza rete 192.168.1.0/24"
→ [15 device trovati]
→ Chat Mode: "Quale è più vulnerabile?"
→ AI: "Il device X ha porta Y aperta..."
```

## 🚀 Test

Riavvia e prova:

```bash
./start.sh
```

**Nell'UI:**
1. Clicca "Deep Step"
2. Input: `"analizza http://192.168.1.6:8000"`
3. Aspetta completamento step
4. **Sistema passa automaticamente in Chat Mode** 🎯
5. Chiedi: `"perché la connessione si chiude?"`
6. AI risponde con contesto completo!

## 📝 Note Implementazione

- ✅ Contesto salvato in `window.lastStepContext`
- ✅ Usato solo per la **prima** domanda follow-up
- ✅ Poi pulito per evitare confusione
- ✅ Terminal + Chat sincronizzati
- ✅ Auto-switch UI automatico

**Il sistema ora è VERAMENTE intelligente e conversazionale!** 🧠💬

