#!/usr/bin/env python3
"""
Command Validator - Verifica che il comando sia appropriato per lo step.

Problema risolto: LLM genera sempre nmap anche quando serve curl/exploit.
Soluzione: Chiedi all'LLM se il comando è sensato per l'obiettivo.
"""
import logging
import json
import re
from typing import Dict, Optional, Callable

logger = logging.getLogger('CMD-VALIDATOR')

class CommandValidator:
    """Valida che il comando sia appropriato per lo step"""
    
    def __init__(self, llm_call_fn: Callable):
        self.llm_call = llm_call_fn
        self.command_history = []  # Traccia comandi già usati
        self.known_impossible_goals = [
            "shell su google home",
            "backdoor persistente su iot",
            "reverse shell su chromecast",
            "shell bash su dispositivi cast"
        ]
    
    def is_command_appropriate(
        self, 
        command: str, 
        step_description: str,
        previous_commands: list = None
    ) -> Dict:
        """
        Valida se il comando è appropriato per lo step.
        
        Returns:
            {
                "appropriate": bool,
                "reason": str,
                "suggestion": str (se non appropriate)
            }
        """
        
        # === REALITY CHECKS ===
        
        # 0. Comandi irrealistici/inesistenti
        cmd_lower = command.lower()
        
        # Script Python che non esistono
        if 'python' in cmd_lower and any(pattern in cmd_lower for pattern in ['exploit_', '_exploit.py', '_rce.py']):
            # Verifica se file esiste
            import os
            script_match = re.search(r'python3?\s+(\S+\.py)', command)
            if script_match:
                script_path = script_match.group(1)
                if not os.path.exists(script_path) and not script_path.startswith('/'):
                    return {
                        "appropriate": False,
                        "reason": f"Script {script_path} non esiste sul sistema",
                        "suggestion": "Usa comandi nativi (curl, nc, nmap --script) invece di script inesistenti"
                    }
        
        # Comandi che modificano sistema locale invece che target remoto
        local_modifications = ['systemctl', 'crontab -e', 'service ', 'useradd', 'groupadd']
        if any(mod in cmd_lower for mod in local_modifications):
            # OK solo se chiaramente per setup locale (listener, etc)
            if not any(safe in step_description.lower() for safe in ['listener', 'ricevi', 'prepara locale', 'setup attaccante']):
                return {
                    "appropriate": False,
                    "reason": "Comando modifica sistema locale invece di attaccare target remoto",
                    "suggestion": "Usa comandi di network exploitation (curl, nc) per interagire con target remoto"
                }
        
        # Quick checks senza LLM
        
        # 1. Se comando ripete esattamente uno già fatto
        if previous_commands and command in previous_commands:
            return {
                "appropriate": False,
                "reason": "Comando già eseguito in precedenza",
                "suggestion": "Usa approccio diverso o tool alternativo"
            }
        
        # 2. Validazione tool semantica (più permissiva)
        step_lower = step_description.lower()
        cmd_first = command.split()[0] if command.split() else ""
        
        # Mapping intento → tool ACCETTABILI (non obbligatori)
        # Permette alternative semanticamente valide
        acceptable_tools = {
            'scan/discovery': {
                'keywords': ['scansiona', 'identifica servizi', 'enumera porte', 'trova dispositivi'],
                'tools': ['nmap', 'masscan', 'nc', 'ping']
            },
            'http_request': {
                'keywords': ['richiesta http', 'endpoint', 'api call', 'get data', 'post data'],
                'tools': ['curl', 'wget', 'nc', 'python']
            },
            'exploit_db': {
                'keywords': ['cerca exploit', 'vulnerability database', 'exploit-db'],
                'tools': ['searchsploit', 'curl']
            },
            'connection': {
                'keywords': ['connessione tcp', 'porta udp', 'listener', 'netcat'],
                'tools': ['nc', 'ncat', 'socat', 'telnet']
            }
        }
        
        # Verifica solo se c'è un FORTE mismatch semantico
        # (es. step dice "connessione TCP" ma comando usa "searchsploit")
        step_intent = None
        for intent, config in acceptable_tools.items():
            if any(kw in step_lower for kw in config['keywords']):
                step_intent = intent
                # Se comando usa tool accettabile per questo intento, OK
                if cmd_first in config['tools'] or any(tool in command for tool in config['tools']):
                    break  # Tool appropriato trovato
                # Se non usa nessun tool dell'intent, potrebbe essere problematico
                # Ma solo se usa tool COMPLETAMENTE sbagliato
        else:
            # Nessun intent specifico o tool appropriato già trovato
            step_intent = None
        
        # Verifica mismatch GRAVI (es. searchsploit per fare scansione rete)
        scan_tools = ['nmap', 'masscan', 'ping', 'arping']
        exploit_tools = ['searchsploit', 'msfconsole']
        data_tools = ['curl', 'wget', 'python']
        
        # Riconosci step di ricerca exploit (NON è scansione!)
        is_exploit_step = any(kw in step_lower for kw in [
            'cerca exploit', 'analizza vulnerabilità', 'vulnerabilità', 'cve', 
            'exploit', 'searchsploit', 'metasploit'
        ])
        
        is_scan_step = any(kw in step_lower for kw in ['scansiona', 'enumera porte', 'identifica servizi', 'trova dispositivi'])
        is_data_step = any(kw in step_lower for kw in ['verifica servizi', 'raccogliere info', 'dati', 'informazioni'])
        
        # Se step è ricerca exploit, searchsploit è CORRETTO
        if is_exploit_step and cmd_first in exploit_tools:
            # searchsploit è appropriato per step di ricerca exploit
            pass  # Non bloccare
        # SOLO blocca se c'è CHIARO mismatch (scansione rete con exploit tool)
        elif is_scan_step and cmd_first in exploit_tools:
            return {
                "appropriate": False,
                "reason": f"Step di scansione/discovery ma comando usa {cmd_first}",
                "suggestion": f"Per scansioni usa: nmap, nc, ping"
            }
        elif is_data_step and cmd_first in exploit_tools and not is_exploit_step:
            return {
                "appropriate": False,
                "reason": f"Step richiede raccolta dati ma comando usa {cmd_first}",
                "suggestion": f"Per raccogliere dati usa: curl, wget, nc"
            }
        
        # 3. Se è lo stesso tool ripetuto 3+ volte (MA: se comando è diverso, permetti)
        cmd_tool = command.split()[0] if command.split() else ""
        if previous_commands:
            # ECCEZIONE: Se il comando è IDENTICO a uno già eseguito, rigetta
            if command in previous_commands:
                return {
                    "appropriate": False,
                    "reason": "Comando già eseguito in precedenza",
                    "suggestion": f"Genera comando diverso (varia argomenti o IP)"
                }
            # Se è lo stesso tool ma comando diverso, potrebbe essere necessario (es. adb connect a IP diversi)
            # Permetti se il comando è diverso
            same_tool_count = sum(1 for c in previous_commands if c.split()[0] == cmd_tool)
            if same_tool_count >= 2:  # 3° volta con stesso tool
                # Se comando è diverso, permetti (es. adb connect IP1, adb connect IP2)
                # Solo log warning, non bloccare
                logger.debug(f"[VALIDATOR] Tool '{cmd_tool}' usato {same_tool_count + 1} volte, ma comando è diverso - permesso")
        
        # 4. Validazione mismatch exploit vs scan (più permissiva)
        exploit_keywords = ['sfruttare', 'payload', 'rce', 'shell remota', 'backdoor']
        
        step_is_exploit = any(kw in step_lower for kw in exploit_keywords)
        
        cmd_is_scan = cmd_first in ['nmap', 'masscan', 'ping', 'traceroute']
        
        # Mismatch critico SOLO se step CHIARAMENTE richiede exploit
        # e comando fa SOLO scan senza nessun script exploit
        if step_is_exploit and cmd_is_scan:
            # Permetti nmap con --script (può eseguire exploit)
            if '--script' in command and any(ex in command for ex in ['vuln', 'exploit', 'shellshock']):
                pass  # nmap con script exploit è ok
            elif 'analizza' in step_lower or 'verifica' in step_lower:
                pass  # Step di analisi può usare scan
            else:
                return {
                    "appropriate": False,
                    "reason": f"Step richiede exploitation ma comando fa solo scan ({cmd_first})",
                    "suggestion": "Usa tool di exploitation: curl con payload, nc, python, o nmap --script exploit"
                }
        
        # === REALITY CHECK FINALE ===
        # Verifica se obiettivo è realistico con LLM
        reality_check = self._check_goal_reality(step_description, command)
        if not reality_check['realistic']:
            return {
                "appropriate": False,
                "reason": reality_check['reason'],
                "suggestion": reality_check.get('alternative', 'Usa obiettivo realistico per questo target')
            }
        
        # Se tutto OK
        return {
            "appropriate": True,
            "reason": "Comando appropriato per lo step"
        }
    
    def _check_goal_reality(self, step_description: str, command: str) -> Dict:
        """Verifica se obiettivo è realistico (es. shell su Google Home = impossibile)"""
        
        step_lower = step_description.lower()
        
        # Check obiettivi impossibili noti
        for impossible in self.known_impossible_goals:
            if impossible in step_lower:
                return {
                    "realistic": False,
                    "reason": f"Obiettivo impossibile: {impossible}",
                    "alternative": "Google Home non ha shell. Obiettivo realistico: controllo Cast protocol, info disclosure"
                }
        
        # Google Home specific
        if any(device in step_lower for device in ['google home', 'chromecast', 'nest mini', 'google mini']):
            if any(impossible in step_lower for impossible in ['shell', 'bash', 'backdoor', 'ssh', 'reverse shell', 'netcat shell', 'shell remota']):
                return {
                    "realistic": False,
                    "reason": "Dispositivi Google Cast/Home NON hanno shell accessibile - sono Android TV limitati",
                    "alternative": "Obiettivo realistico: Interroga API Cast su porta 8008 con curl http://IP:8008/setup/eureka_info"
                }
        
        # IoT devices in generale
        if 'iot' in step_lower or 'smart' in step_lower:
            if 'reverse shell' in step_lower or 'backdoor' in step_lower:
                return {
                    "realistic": False,
                    "reason": "Shell persistente su IoT consumer è irrealistico senza exploit 0-day",
                    "alternative": "Obiettivo realistico: DoS, information disclosure, command injection limitato"
                }
        
        return {"realistic": True}
    
    def suggest_better_command(
        self, 
        step_description: str,
        failed_command: str,
        context: str = "",
        previous_commands: list = None,
        mandatory_tool: str = None
    ) -> Optional[str]:
        """
        Chiede all'LLM di suggerire comando migliore.
        
        Usato quando comando è stato rigettato.
        """
        
        # Estrai dati dal contesto
        import re
        context_ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', context)
        unique_ips = list(set(context_ips))[:5]
        
        ip_hint = ""
        if unique_ips:
            ip_hint = f"\n🎯 IP DISPONIBILI NEL CONTESTO (USA QUESTI):\n   {', '.join(unique_ips)}\n"
        
        # Analizza lo step per suggerire tool appropriato
        step_lower = step_description.lower()
        tool_suggestion = ""
        
        # PRIORITÀ: Se c'è un tool obbligatorio, USA QUELLO
        if mandatory_tool:
            tool_suggestion = f"DEVI usare SOLO '{mandatory_tool}' - NON altri tool (nc, curl, host, etc)"
        elif any(kw in step_lower for kw in ['rtsp', 'stream', 'video', 'ffmpeg', 'vlc']):
            tool_suggestion = "Usa: ffplay, vlc, o ffmpeg per stream video"
        elif any(kw in step_lower for kw in ['http', 'api', 'endpoint', 'web', 'onvif', 'curl']):
            tool_suggestion = "Usa: curl con argomenti appropriati (es. curl -v http://IP:PORT/path)"
        elif any(kw in step_lower for kw in ['nslookup', 'dns', 'hostname', 'reverse']):
            tool_suggestion = "Usa: host, dig, o nslookup per DNS"
        elif any(kw in step_lower for kw in ['porta', 'connection', 'tcp', 'udp']) and not mandatory_tool:
            tool_suggestion = "Usa: nc (netcat) per connessioni dirette"
        elif any(kw in step_lower for kw in ['scan', 'nmap', 'porte']):
            tool_suggestion = "Usa: nmap con porte specifiche"
        elif any(kw in step_lower for kw in ['exploit', 'cve', 'vulnerability']):
            tool_suggestion = "Usa: searchsploit per cercare exploit"
        
        # Lista comandi già eseguiti da evitare
        previous_hint = ""
        if previous_commands:
            previous_hint = "\n🚫 COMANDI GIÀ ESEGUITI (NON RIPETERE):\n"
            for cmd in previous_commands[-5:]:  # Ultimi 5
                previous_hint += f"   ✗ {cmd}\n"
        
        mandatory_tool_hint = ""
        if mandatory_tool:
            mandatory_tool_hint = f"\n🚨 TOOL OBBLIGATORIO: {mandatory_tool.upper()}\n"
            mandatory_tool_hint += f"⚠️ DEVI usare SOLO '{mandatory_tool}' - NON 'nc', 'curl', 'host' o altri tool!\n"
            mandatory_tool_hint += f"ESEMPIO CORRETTO: {mandatory_tool} <argomenti>\n"
            mandatory_tool_hint += f"ESEMPIO SBAGLIATO: nc <argomenti> ❌\n"
            mandatory_tool_hint += f"ESEMPIO SBAGLIATO: curl <argomenti> ❌\n"
        
        prompt = f"""══════════════════════════════════════════════════
⚠️ COMANDO RIGETTATO - GENERA ALTERNATIVA VALIDA
══════════════════════════════════════════════════

OBIETTIVO DELLO STEP:
{step_description}

COMANDO RIGETTATO:
{failed_command}

PROBLEMA: Comando non appropriato per lo step.
{ip_hint}
{mandatory_tool_hint}
TOOL SUGGERITO:
{tool_suggestion}
{previous_hint}
══════════════════════════════════════════════════
REGOLE INVIOLABILI PER IL NUOVO COMANDO:
══════════════════════════════════════════════════
1. Genera ESATTAMENTE UN comando bash valido ed eseguibile
2. USA SOLO IP/dati reali dal contesto sopra
3. NO placeholder come <IP>, [indirizzo], IP_CAMERA
4. NO frasi italiane (es. 'Analizza', 'Verifica')
5. NO comandi già rigettati o simili a quello sopra
6. NO comandi già eseguiti (vedi lista sopra)
7. Comando MAX 200 caratteri
8. Deve essere DIVERSO dal comando rigettato
9. Formato: tool argomento1 argomento2 ...

ESEMPI VALIDI:
- curl -v http://192.168.1.6:80/onvif/device_service
- nmap -p 554,8554 -sV 192.168.1.6
- host 192.168.1.6
- nc -zv 192.168.1.6 554

GENERA SOLO IL COMANDO (NO SPIEGAZIONI):"""
        
        try:
            response = self.llm_call(prompt)
            
            # Estrai comando dalla risposta
            cmd = self._extract_clean_command(response)
            
            if cmd and cmd != failed_command:
                # Verifica che non sia già stato eseguito
                if previous_commands and cmd in previous_commands:
                    logger.warning(f"[VALIDATOR] Comando suggerito già eseguito: {cmd}")
                    return None
                
                # Verifica che rispetti tool obbligatorio
                if mandatory_tool:
                    cmd_tool = cmd.split()[0] if cmd.split() else ""
                    if cmd_tool.lower() != mandatory_tool.lower():
                        logger.warning(f"[VALIDATOR] Comando suggerito usa tool sbagliato '{cmd_tool}' invece di '{mandatory_tool}'")
                        return None
                
                logger.info(f"[VALIDATOR] Suggerito: {cmd}")
                return cmd
            else:
                logger.warning(f"[VALIDATOR] Comando suggerito identico o vuoto")
            
        except Exception as e:
            logger.warning(f"[VALIDATOR] Errore suggerimento: {e}")
        
        return None
    
    def _extract_clean_command(self, text: str) -> Optional[str]:
        """Estrae comando pulito da testo LLM - RIGOROSO"""
        
        # Lista estesa di comandi validi
        known_cmds = [
            'nmap', 'curl', 'wget', 'nc', 'ncat', 'echo', 'cat', 'grep', 'find', 'ping',
            'telnet', 'ssh', 'host', 'dig', 'nslookup',
            'searchsploit', 'python', 'python3',
            'ffmpeg', 'ffplay', 'vlc', 'cvlc'
        ]
        
        # Placeholder che indicano comando INCOMPLETO
        placeholder_patterns = [
            r'<[^>]+>',  # <IP>, <indirizzo>
            r'\[indirizzo', r'\[ip', r'\[porta',
            r'IP_CAMERA', r'TARGET_IP', r'HOST_IP',
        ]
        
        # Rimuovi markdown
        text = re.sub(r'```(?:bash)?\n?', '', text)
        text = re.sub(r'`', '', text)
        
        # Prendi prima linea che sembra comando VALIDO
        lines = [l.strip() for l in text.split('\n') if l.strip()]
        
        for line in lines:
            # Skippa commenti
            if line.startswith('#') or line.startswith('//'):
                continue
            
            first_word = line.split()[0] if line.split() else ""
            
            # Deve essere comando noto
            if first_word not in known_cmds:
                continue
            
            # Deve avere almeno 2 parole
            if len(line.split()) < 2:
                continue
            
            # Non deve avere placeholder
            has_placeholder = False
            for pattern in placeholder_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    has_placeholder = True
                    break
            
            if not has_placeholder:
                logger.debug(f"[VALIDATOR] Comando estratto: {line}")
                return line
        
        # Fallback: cerca pattern "tool arg" nel testo
        for known_cmd in known_cmds[:10]:
            pattern = rf'\b{re.escape(known_cmd)}\s+[^\n<\[]+?(?:\n|$)'
            match = re.search(pattern, text)
            if match:
                cmd = match.group(0).strip()
                # Verifica no placeholder
                has_placeholder = any(re.search(p, cmd, re.IGNORECASE) for p in placeholder_patterns)
                if not has_placeholder and len(cmd.split()) >= 2:
                    logger.debug(f"[VALIDATOR] Comando estratto da pattern: {cmd}")
                    return cmd
        
        logger.warning(f"[VALIDATOR] Nessun comando valido in: {text[:100]}")
        return None


# Helper per uso facile
def validate_and_improve_command(
    command: str,
    step_description: str,
    previous_commands: list,
    llm_call_fn: Callable,
    context: str = ""
) -> Dict:
    """
    Valida comando e suggerisce miglioramento se necessario.
    
    Returns:
        {
            "valid": bool,
            "command": str,  # Comando originale o suggerito
            "validation": Dict
        }
    """
    
    validator = CommandValidator(llm_call_fn)
    
    # Valida
    validation = validator.is_command_appropriate(
        command, 
        step_description,
        previous_commands
    )
    
    # Se appropriato, ritorna comando originale
    if validation['appropriate']:
        return {
            "valid": True,
            "command": command,
            "validation": validation
        }
    
    # Non appropriato - suggerisci alternativa
    logger.warning(f"[VALIDATOR] ❌ {validation['reason']}")
    
    # Estrai tool obbligatorio dallo step (se presente)
    step_lower = step_description.lower()
    mandatory_tool = None
    priority_keywords = {
        'adb': ['connessione adb', 'android debug bridge', 'adb connect', 'tentare connessione adb', 
                'tenta connessione adb', 'connessione adb su porta', 'comandi adb', 'enumerazione dati'],
        'nmap': ['scansione nmap', 'scansiona con nmap', 'esegui scansione nmap'],
        'curl': ['interroga servizi web', 'testare servizi web', 'verifica servizi', 'identifica interfacce']
    }
    for tool, keywords in priority_keywords.items():
        if any(kw in step_lower for kw in keywords):
            mandatory_tool = tool
            break
    
    better_cmd = validator.suggest_better_command(
        step_description,
        command,
        context,
        previous_commands=previous_commands,
        mandatory_tool=mandatory_tool
    )
    
    if better_cmd:
        # Ri-valida il nuovo comando
        new_validation = validator.is_command_appropriate(
            better_cmd,
            step_description,
            previous_commands
        )
        
        return {
            "valid": new_validation['appropriate'],
            "command": better_cmd,
            "validation": new_validation,
            "original_rejected": command
        }
    
    # Nessuna alternativa trovata
    return {
        "valid": False,
        "command": command,
        "validation": validation
    }

