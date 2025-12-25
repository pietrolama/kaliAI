# Sistema Intelligente - KaliAI V2

## Problema Risolto

**Prima**: LLM ripeteva sempre `nmap` anche quando serviva `curl`, `nc`, o exploit.

**Causa**: Nessun controllo sulla qualità dei comandi generati.

**Ora**: Sistema valida e corregge i comandi prima di eseguirli.

---

## Flusso di Esecuzione

### 1. Smart Context Building (PRIMA di generare step)

```python
Prompt: "attacca google home mini sulla rete"

↓ Pre-scan rete (5 sec)
"192.168.1.9 (Chromecast - Google)
 192.168.1.12 (Google-Home-Mini - Google)
 192.168.1.14 (wiz_05feaa - WiZ IoT)"

↓ Analisi obiettivo LLM
{
  "target_description": "Google Home Mini smart speaker",
  "target_hints": ["hostname contains 'Google'", "ports 8008/8009"],
  "key_requirements": ["identify IP", "find CVE", "get shell"],
  "approach": "discovery → vulnerability scan → exploit"
}

↓ Contesto completo per step generation
"OBIETTIVO: attacca google home mini
 RETE: 192.168.1.12 (Google-Home-Mini)
 TARGET: Google Home Mini smart speaker
 STRATEGIA: discovery → vulnerability scan → exploit"
```

### 2. Step Generation (con contesto ricco)

LLM genera 5 step CON IP REALI già nel contesto:

```
1. Scansiona porta 8009 su 192.168.1.12 (ha già l'IP!)
2. Verifica API /setup/eureka_info con curl (sa che serve curl!)
3. Cerca CVE con searchsploit
4. Exploit con payload
5. Verifica shell
```

### 3. Command Validation (prima di eseguire)

Per ogni step, quando LLM genera comando:

```python
STEP: "Verifica API /setup/eureka_info"
LLM genera: "nmap -p 8008 192.168.1.12"

↓ Command Validator
❌ Inappropriato! Step chiede API (curl), comando usa scan (nmap)

↓ Chiedi comando alternativo a LLM
"Step richiede API check, nmap non appropriato.
 Suggerisci comando con curl per endpoint /setup/eureka_info"

↓ LLM corregge
✅ "curl -s http://192.168.1.12:8008/setup/eureka_info"

↓ Ri-valida
✅ Appropriato! Esegui.
```

### 4. Tool Diversity Forcing

```python
Step 1: nmap ✅
Step 2: nmap ✅
Step 3: nmap ❌ "ATTENZIONE: nmap già usato 2 volte! USA curl, nc, python"

↓ LLM forzato a cambiare
Step 3: curl ✅
```

---

## Componenti

### `smart_context_builder.py`
**Cosa fa**: Pre-scansiona rete e analizza obiettivo  
**Input**: Prompt utente  
**Output**: Contesto ricco con IP, analisi target, strategia  
**Beneficio**: LLM vede dati reali da subito → comandi corretti  

### `command_validator.py`
**Cosa fa**: Valida comando vs step description  
**Checks**:
- Tool appropriato? (API → curl, non nmap)
- Tool ripetuto? (nmap x3 → forza cambio)
- Comando già tentato? (skip duplicati)

**Azione**: Rigetta + chiede alternativa all'LLM

### `step_executor_improved.py`
**Cosa fa**: Esegue step con validazione e retry  
**Features**:
- Integrato Command Validator
- Tool diversity forcing
- Prompt hints ("Tool suggerito: curl")
- Retry con approcci diversi

---

## Esempio Completo

**Input**: "attacca google home mini, trova CVE e ottieni shell"

### Fase 1: Context Building (5 sec)
```
Pre-scan → Trova 192.168.1.12 (Google-Home-Mini)
LLM analizza → "Target: Google Home Mini, Hints: port 8008/8009, Strategy: scan→CVE→exploit"
```

### Fase 2: Step Generation
```
LLM genera (con contesto ricco):
1. nmap -p 8008,8009 192.168.1.12         ← già usa IP corretto!
2. curl http://192.168.1.12:8008/setup... ← sa che serve curl!
3. searchsploit google cast               ← tool giusto per CVE!
4. python exploit.py --target 192.168.1.12
5. nc 192.168.1.12 4444
```

### Fase 3: Execution con Validation

**Step 1**: 
- Comando: `nmap -p 8008,8009 192.168.1.12` 
- Validator: ✅ Appropriato (scan per discovery)
- Esegui → Success

**Step 2**:
- LLM genera: `nmap -p 8008 192.168.1.12` (ERRORE!)
- Validator: ❌ Step chiede API/curl, comando usa nmap
- Chiedi alternativa LLM → `curl http://192.168.1.12:8008/setup/eureka_info`
- Validator: ✅ Appropriato
- Esegui → Success

**Step 3**:
- LLM genera: `nmap -sV 192.168.1.12` (ERRORE DI NUOVO!)
- Validator: ❌ nmap già usato 2 volte + step chiede exploit/CVE
- Prompt forzato: "USA searchsploit, NON nmap"
- LLM genera: `searchsploit google cast`
- Validator: ✅ Appropriato
- Esegui → Success

---

## Metriche Performance

**Prima**:
- ❌ Loop infinito nmap (5/5 step usavano nmap)
- ❌ Comandi generici senza dati reali
- ❌ 0 exploit riusciti

**Ora**:
- ✅ Tool diversity (nmap, curl, searchsploit, nc, python)
- ✅ Comandi con IP reali dal pre-scan
- ✅ Correzione automatica comandi sbagliati
- ✅ Esecuzione appropriata per ogni step

---

## Conclusione

Il sistema ora **pensa bene E agisce bene**:

1. **Context-First**: Dati reali PRIMA di generare step
2. **Validation**: Ogni comando controllato vs obiettivo
3. **Self-Correction**: LLM corregge se stesso quando sbaglia
4. **Tool Diversity**: Proibisce loop dello stesso comando
5. **Smart Retry**: Cambia strategia, non ripete errori

**Nessun hard-coding**, tutto guidato da contesto e validazione intelligente.

