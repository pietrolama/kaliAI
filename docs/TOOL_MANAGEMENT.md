# 🛠️ Tool Management System

Sistema automatico di gestione e installazione tool di pentesting.

## 🎯 Funzionalità

### Auto-Install Automatico
Il sistema **installa automaticamente** i tool mancanti quando vengono richiesti:

```python
# Nel codice, quando esegui un comando:
os.system("dirb http://target.com")  
# ↓
# Sistema rileva che dirb manca
# ↓  
# Installa dirb automaticamente
# ↓
# Esegue il comando
```

### Tool Supportati (19 tool)

**Web Scanning:**
- `dirb` - Directory bruteforcer
- `gobuster` - Fast directory/DNS bruteforcer  
- `whatweb` - Web technology identifier
- `nikto` - Web server scanner
- `wfuzz` - Web application fuzzer

**Exploitation:**
- `sqlmap` - SQL injection tool
- `metasploit-framework` - Penetration testing framework
- `hydra` - Password cracker

**Network:**
- `masscan` - Ultra-fast port scanner
- `netcat` - Network Swiss Army knife
- `sslscan` - SSL/TLS scanner
- `dnsrecon` - DNS enumeration
- `dnsenum` - DNS enumeration

**Utilities:**
- `ffmpeg` - Multimedia framework (streaming video)
- `exiftool` - Metadata extraction
- `john` - John the Ripper password cracker
- `aircrack-ng` - WiFi security auditing

## 📊 Verifica Stato Tool

```bash
python tool_manager.py
```

Output:
```
Tool totali: 19
Installati: 18
Mancanti: 1
Coverage: 94.7%
```

## 🚀 Installazione Manuale Tool

### Singolo Tool

```python
from tool_manager import tool_manager

# Installa dirb
success, message = tool_manager.install_tool('dirb')
print(message)
```

### Suite Completa

```bash
# Installazione interattiva
python install_pentest_tools.py

# Installazione automatica (no conferma)
python install_pentest_tools.py --yes
```

## 🔧 Integrazione Step-by-Step

Il sistema **step-by-step automatico** ora:

1. ✅ Analizza il comando da eseguire
2. ✅ Rileva tool richiesto (es: `dirb`, `sqlmap`)
3. ✅ Verifica se installato
4. ✅ Se mancante → **installa automaticamente**
5. ✅ Esegue il comando

### Esempio Pratico

**Prompt utente:**
```
fai directory busting su http://target.com
```

**Sistema:**
```
[STEP-BY-STEP] Generato comando: dirb http://target.com
[TOOL-MANAGER] dirb mancante, installazione automatica...
[TOOL-MANAGER] ✅ dirb installato con successo
[SUBPROCESS] Esecuzione: dirb http://target.com
```

## 📝 Aggiungere Nuovi Tool

Modifica `tool_manager.py`:

```python
TOOLS = {
    'nuovo-tool': {
        'package': 'nome-pacchetto-apt',
        'check_cmd': 'which nuovo-tool',
        'description': 'Descrizione tool',
        'optional': False  # o True se opzionale
    }
}
```

## 🎯 API Python

### Check Tool

```python
from tool_manager import ensure_tool_available

if ensure_tool_available('sqlmap'):
    os.system('sqlmap -u http://target.com')
else:
    print("sqlmap non disponibile")
```

### Batch Check

```python
from tool_manager import tool_manager

missing = tool_manager.get_missing_tools(['dirb', 'nikto', 'sqlmap'])
print(f"Tool mancanti: {missing}")
```

### Stats

```python
stats = tool_manager.get_tool_stats()
print(f"Coverage: {stats['coverage']}")
```

## ⚠️ Limitazioni

- ✅ Funziona solo su **Debian/Kali Linux** (usa apt)
- ⚠️ Richiede **permessi sudo** per installazione (gestito automaticamente se già root)
- ⚠️ Tool opzionali **non** vengono auto-installati
- ⚠️ Timeout installazione: **5 minuti** max per tool

## 🔐 Sicurezza

Il sistema:
- ✅ Installa **SOLO** tool dal database predefinito
- ✅ Verifica installazione prima di eseguire
- ✅ Log completo di tutte le operazioni
- ✅ Non installa tool opzionali senza conferma

## 📈 Roadmap

- [ ] Supporto altri package manager (yum, pacman)
- [ ] Cache locale package per installazioni offline
- [ ] Auto-update tool obsoleti
- [ ] Rilevamento automatico tool custom da PATH
- [ ] UI web per gestione tool

## 🐛 Troubleshooting

**Tool non si installa:**
```bash
# Verifica manualmente
sudo apt-get update
sudo apt-get install <tool-name>
```

**Permission denied:**
```bash
# Assicurati di avere sudo
sudo python install_pentest_tools.py --yes
```

**Cache tool non aggiornata:**
```python
# Reset cache
tool_manager.installed_cache.clear()
```

## 📚 Esempi

### Script Pentest Automatico

```python
from tool_manager import ensure_tool_available
import os

target = "http://target.com"

# Assicura tool disponibili
for tool in ['nmap', 'dirb', 'nikto', 'sqlmap']:
    ensure_tool_available(tool)

# Esegui scansioni
os.system(f"nmap -sV {target}")
os.system(f"dirb {target}")
os.system(f"nikto -h {target}")
```

### Check Coverage Prima di Pentest

```python
from tool_manager import tool_manager

required = ['nmap', 'dirb', 'sqlmap', 'nikto', 'whatweb']
missing = tool_manager.get_missing_tools(required)

if missing:
    print(f"Tool mancanti: {missing}")
    print("Installazione automatica...")
    for tool in missing:
        tool_manager.auto_install_if_missing(tool)
else:
    print("✅ Tutti i tool pronti!")
```

