#!/usr/bin/env python3
"""
Security Configuration - Regole di ingaggio per KaliAI
🔒 Scope Enforcement, Banned Commands, Validation Functions

Tre livelli di sicurezza:
- SAFE: Solo target in whitelist, no comandi offensivi
- LAB: Target in whitelist, comandi offensivi permessi
- UNRESTRICTED: Nessun limite (USE WITH CAUTION)
"""

import os
import re
import socket
import logging
import ipaddress
from enum import Enum
from typing import List, Tuple, Optional
from functools import lru_cache

logger = logging.getLogger('Security')

# ============================================================================
# SECURITY LEVEL
# ============================================================================

class SecurityLevel(Enum):
    """Livelli di sicurezza del sistema"""
    SAFE = "safe"              # Solo scan passivi, whitelist rigorosa
    LAB = "lab"                # Attacchi permessi, solo su whitelist
    UNRESTRICTED = "unrestricted"  # Nessun limite (pericoloso!)

# Default: SAFE (può essere cambiato via ENV)
CURRENT_SECURITY_LEVEL = SecurityLevel(
    os.getenv("KALIAI_SECURITY_LEVEL", "unrestricted").lower()
)

# ============================================================================
# SCOPE WHITELIST (CIDR Ranges)
# ============================================================================

# Reti private standard + localhost
SCOPE_WHITELIST: List[str] = [
    # Localhost
    "127.0.0.0/8",
    
    # Reti private RFC1918
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
    
    # Link-local
    "169.254.0.0/16",
    
    # Docker/Podman default networks
    "172.17.0.0/16",
    
    # WSL2 networks (common ranges)
    "172.28.0.0/16",
    "172.29.0.0/16",
    
    # Custom lab networks (add your ranges here)
    # "203.0.113.0/24",  # TEST-NET-3
]

# Parse delle CIDR per validazione veloce
_WHITELIST_NETWORKS = [ipaddress.ip_network(cidr, strict=False) for cidr in SCOPE_WHITELIST]

# ============================================================================
# BANNED COMMANDS & PATTERNS
# ============================================================================

# Comandi distruttivi (sempre bloccati in SAFE)
BANNED_DESTRUCTIVE_PATTERNS: List[str] = [
    # File system destruction
    "rm -rf /",
    "rm -rf /*",
    "rm -rf ~",
    "rm -rf .",
    "rm -rf *",
    "> /dev/sda",
    "dd if=/dev/zero",
    "dd if=/dev/random",
    "mkfs.",
    "shred",
    
    # Fork bomb
    ":(){ :|:& };:",
    ".LiNUX.",
    
    # System commands
    "shutdown",
    "reboot",
    "halt",
    "poweroff",
    "init 0",
    "init 6",
    
    # Credential theft from host
    "/etc/shadow",
    "/etc/passwd|base64",
    ".ssh/id_rsa",
    ".gnupg/",
    
    # Reverse shells (solo in SAFE, LAB le permette)
    # "nc -e",
    # "bash -i >& /dev/tcp",
    # "python -c 'import socket",
]

# Tool offensivi bloccati in modalità SAFE
BANNED_TOOLS_SAFE_MODE: List[str] = [
    "masscan",
    "hping3",
    "slowloris",
    "thc-ssl-dos",
    "ettercap",
    "bettercap",
    "responder",
    "mitmproxy",
    "arpspoof",
    "dnsspoof",
]

# ============================================================================
# PROTECTED PATHS (DENY-WINS: Accesso sempre bloccato in LAB/SAFE)
# ============================================================================

# Path protetti - NESSUN agente può leggere questi (tranne UNRESTRICTED)
PROTECTED_PATHS: List[str] = [
    # System configuration
    "/etc/",
    "/root/",
    
    # User secrets
    "/.ssh/",
    "/.gnupg/",
    "/.aws/",
    "/.kube/",
    "/.docker/",
    
    # System internals
    "/proc/",
    "/sys/",
    
    # Password files (pattern match)
    "/shadow",
    "/passwd",
    "/sudoers",
]

# Comandi che leggono file (usati per check path)
FILE_READ_COMMANDS: List[str] = [
    "cat", "head", "tail", "less", "more",
    "grep", "egrep", "fgrep", "rg",
    "sed", "awk", "cut",
    "strings", "xxd", "hexdump", "od",
    "nano", "vim", "vi", "emacs",
    "cp", "mv", "ln",
    "tar", "zip", "gzip",
    "base64", "openssl",
    "source", ".",  # Shell source commands
]

# Comandi che enumerano/rivelano metadata (dimensione, permessi, esistenza)
ENUMERATION_COMMANDS: List[str] = [
    "ls", "dir", "ll",
    "find", "locate", "which", "whereis",
    "stat", "file", "readlink",
    "tree", "du", "wc",
    "realpath", "dirname", "basename",
    "test", "[",  # Shell test commands
]

# Tutti i comandi sensibili (read + enumeration)
ALL_SENSITIVE_COMMANDS = set(FILE_READ_COMMANDS + ENUMERATION_COMMANDS)

def _extract_command_name(segment: str) -> str:
    """Estrae il nome del comando da un segmento di pipeline."""
    segment = segment.strip()
    if not segment:
        return ""
    
    # Rimuovi prefissi comuni (sudo, env, timeout, etc.)
    prefixes = ["sudo", "env", "timeout", "time", "nice", "nohup", "strace"]
    words = segment.split()
    
    for i, word in enumerate(words):
        # Salta assegnazioni variabili (VAR=value)
        if "=" in word and not word.startswith("-"):
            continue
        # Salta prefissi
        if word in prefixes:
            continue
        # Questo è il comando
        cmd = word.split("/")[-1]  # Rimuovi path (/usr/bin/cat -> cat)
        return cmd.lower()
    
    return words[0].lower() if words else ""

def _extract_paths_from_segment(segment: str) -> List[str]:
    """Estrae tutti i path da un segmento di comando."""
    paths = []
    
    # Pattern per path assoluti, relativi e con ~
    path_patterns = [
        re.compile(r'(/[^\s|><&;]+)'),        # Path assoluti
        re.compile(r'(\./[^\s|><&;]+)'),      # Path relativi ./
        re.compile(r'(~/[^\s|><&;]+)'),       # Home paths ~/
    ]
    
    for pattern in path_patterns:
        matches = pattern.findall(segment)
        paths.extend(matches)
    
    return paths

def _resolve_path(path: str) -> str:
    """Risolve un path espandendo ~ e symlink."""
    import subprocess
    
    # Espandi ~
    expanded = os.path.expanduser(path)
    
    # Normalizza path traversal (/../)
    try:
        normalized = os.path.normpath(expanded)
    except:
        normalized = expanded
    
    # Risolvi symlink con realpath
    try:
        result = subprocess.run(
            ['realpath', '-m', normalized],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    return normalized

def _is_protected_path(path: str) -> Tuple[bool, str]:
    """Verifica se un path è in una zona protetta."""
    real_path = _resolve_path(path)
    
    for protected in PROTECTED_PATHS:
        # Match esatto o prefisso
        if protected in real_path or real_path.startswith(protected.rstrip('/')):
            return (True, protected)
    
    return (False, "")

def check_protected_path_access(command: str) -> Tuple[bool, str]:
    """
    Verifica se un comando tenta di accedere a path protetti.
    
    FEATURES:
    - Pipeline-aware: analizza TUTTI i segmenti (cmd1 | cmd2 | cmd3)
    - Blocca sia lettura che enumerazione
    - Risolve symlink e path traversal
    - DENY-WINS: se qualsiasi segmento tocca path protetto → DENY
    
    Returns:
        Tuple (is_allowed, reason)
        Se is_allowed=False, il comando DEVE essere bloccato.
    """
    # In UNRESTRICTED, permetti tutto (con warning)
    if CURRENT_SECURITY_LEVEL == SecurityLevel.UNRESTRICTED:
        return (True, "UNRESTRICTED mode - path check skipped")
    
    # Dividi in segmenti di pipeline (|, &&, ||, ;)
    # Regex per separare mantenendo la logica
    pipeline_separators = re.compile(r'\s*(?:\|{1,2}|&&|;)\s*')
    segments = pipeline_separators.split(command)
    
    for segment in segments:
        segment = segment.strip()
        if not segment:
            continue
        
        # Estrai nome comando
        cmd_name = _extract_command_name(segment)
        
        # Se non è un comando sensibile, skip questo segmento
        if cmd_name not in ALL_SENSITIVE_COMMANDS:
            continue
        
        # Determina il tipo di accesso
        is_read_cmd = cmd_name in FILE_READ_COMMANDS
        is_enum_cmd = cmd_name in ENUMERATION_COMMANDS
        
        # Estrai path dal segmento
        paths = _extract_paths_from_segment(segment)
        
        for path in paths:
            is_protected, protected_zone = _is_protected_path(path)
            
            if is_protected:
                if is_read_cmd:
                    return (
                        False,
                        f"PROTECTED PATH READ DENIED: '{path}' in zone '{protected_zone}'"
                    )
                elif is_enum_cmd:
                    return (
                        False,
                        f"PROTECTED PATH ENUMERATION DENIED: '{path}' in zone '{protected_zone}'"
                    )
    
    return (True, "Path check passed (pipeline analyzed)")

# Pattern regex per estrarre IP e domini dai comandi
IP_PATTERN = re.compile(
    r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
    r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'
)

DOMAIN_PATTERN = re.compile(
    r'\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b'
)

# Domini sempre permessi (per lookup, non attacco)
ALLOWED_DOMAINS: List[str] = [
    "localhost",
    "127.0.0.1",
    "host.docker.internal",
    "host.containers.internal",
]

# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

@lru_cache(maxsize=256)
def validate_ip(ip: str) -> bool:
    """
    Verifica se un IP è nella whitelist.
    
    Args:
        ip: Indirizzo IP da validare
        
    Returns:
        True se l'IP è permesso, False altrimenti
    """
    try:
        ip_obj = ipaddress.ip_address(ip)
        
        for network in _WHITELIST_NETWORKS:
            if ip_obj in network:
                return True
        
        return False
    except ValueError:
        # IP non valido = bloccato
        logger.warning(f"[SECURITY] IP non valido: {ip}")
        return False

def resolve_hostname(hostname: str) -> Optional[str]:
    """
    Risolve un hostname in IP.
    
    Args:
        hostname: Nome host da risolvere
        
    Returns:
        IP risolto o None se fallisce
    """
    # Domini sempre permessi
    if hostname.lower() in ALLOWED_DOMAINS:
        return "127.0.0.1"
    
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        logger.warning(f"[SECURITY] Impossibile risolvere: {hostname}")
        return None

def validate_target(target: str) -> Tuple[bool, str]:
    """
    Valida un target (IP o hostname) contro la whitelist.
    
    Args:
        target: IP o hostname da validare
        
    Returns:
        Tuple (is_valid, reason)
    """
    # Se UNRESTRICTED, permetti tutto (con warning)
    if CURRENT_SECURITY_LEVEL == SecurityLevel.UNRESTRICTED:
        logger.warning(f"[SECURITY] ⚠️ UNRESTRICTED MODE: {target} permitted without validation")
        return (True, "UNRESTRICTED mode - all targets allowed")
    
    # Prova come IP
    try:
        ipaddress.ip_address(target)
        if validate_ip(target):
            return (True, f"IP {target} in whitelist")
        else:
            return (False, f"IP {target} NOT in whitelist - BLOCKED")
    except ValueError:
        pass
    
    # È un hostname, prova a risolverlo
    resolved_ip = resolve_hostname(target)
    
    if resolved_ip is None:
        return (False, f"Cannot resolve hostname {target} - BLOCKED")
    
    if validate_ip(resolved_ip):
        return (True, f"Hostname {target} resolved to {resolved_ip} (in whitelist)")
    else:
        return (False, f"Hostname {target} resolved to {resolved_ip} - NOT in whitelist - BLOCKED")

def validate_command(command: str) -> Tuple[bool, str]:
    """
    Valida un comando per pattern proibiti.
    
    Args:
        command: Comando bash da validare
        
    Returns:
        Tuple (is_valid, reason)
    """
    command_lower = command.lower()
    
    # Se UNRESTRICTED, permetti tutto
    if CURRENT_SECURITY_LEVEL == SecurityLevel.UNRESTRICTED:
        return (True, "UNRESTRICTED mode - all commands allowed")
    
    # Check pattern distruttivi (sempre bloccati)
    for pattern in BANNED_DESTRUCTIVE_PATTERNS:
        if pattern.lower() in command_lower:
            return (False, f"Destructive pattern detected: {pattern}")
    
    # In modalità SAFE, blocca anche tool offensivi
    if CURRENT_SECURITY_LEVEL == SecurityLevel.SAFE:
        first_word = command.strip().split()[0] if command.strip() else ""
        if first_word in BANNED_TOOLS_SAFE_MODE:
            return (False, f"Tool {first_word} blocked in SAFE mode")
    
    return (True, "Command validated")

def extract_targets_from_command(command: str) -> List[str]:
    """
    Estrae tutti gli IP e domini da un comando.
    
    Args:
        command: Comando da analizzare
        
    Returns:
        Lista di target (IP e domini) trovati
    """
    targets = []
    
    # Estrai IP
    ips = IP_PATTERN.findall(command)
    targets.extend(ips)
    
    # Estensioni file da ignorare (non sono domini!)
    IGNORED_EXTENSIONS = (
        # Config files
        '.conf', '.cfg', '.ini', '.yaml', '.yml', '.toml', '.env',
        # Code files
        '.txt', '.log', '.py', '.sh', '.bash', '.zsh', '.fish',
        '.json', '.xml', '.html', '.css', '.js', '.ts', '.jsx', '.tsx',
        '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs', '.rb', '.php',
        # Data files
        '.csv', '.tsv', '.sql', '.db', '.sqlite', '.bak',
        # Archive files
        '.tar', '.zip', '.gz', '.bz2', '.xz', '.rar', '.7z',
        # Binary files
        '.bin', '.exe', '.dll', '.so', '.dylib', '.o', '.a',
        # Document files
        '.pdf', '.doc', '.docx', '.md', '.rst', '.tex',
        # Image files
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.bmp',
        # System files
        '.pid', '.sock', '.lock', '.tmp', '.cache', '.swp',
        # Keys and certs
        '.pem', '.key', '.crt', '.cer', '.pub', '.gpg',
    )
    
    # Estrai domini (escludi estensioni file comuni)
    domains = DOMAIN_PATTERN.findall(command)
    for domain in domains:
        # Ignora se termina con un'estensione file conosciuta
        domain_lower = domain.lower()
        if not any(domain_lower.endswith(ext) for ext in IGNORED_EXTENSIONS):
            targets.append(domain)
    
    return list(set(targets))  # Rimuovi duplicati

def full_security_check(command: str) -> Tuple[bool, str]:
    """
    Esegue il check di sicurezza completo su un comando.
    
    DENY-WINS POLICY:
    - Se QUALSIASI check fallisce → DENY
    - ALLOW solo se TUTTI i check passano
    
    Args:
        command: Comando da validare
        
    Returns:
        Tuple (is_safe, reason)
    """
    # === STEP 0: Protected Path Check (DENY-WINS - checked FIRST) ===
    path_allowed, path_reason = check_protected_path_access(command)
    if not path_allowed:
        return (False, path_reason)
    
    # === STEP 1: Valida il comando stesso ===
    cmd_valid, cmd_reason = validate_command(command)
    if not cmd_valid:
        return (False, cmd_reason)
    
    # === STEP 2: Estrai e valida tutti i target (IP/Domini) ===
    targets = extract_targets_from_command(command)
    
    for target in targets:
        target_valid, target_reason = validate_target(target)
        if not target_valid:
            return (False, target_reason)
    
    return (True, f"Command validated ({len(targets)} targets, paths OK)")

# ============================================================================
# AUDIT LOGGING
# ============================================================================

def log_security_event(event_type: str, command: str, reason: str, blocked: bool = False):
    """
    Logga un evento di sicurezza nel file di audit.
    
    Args:
        event_type: Tipo di evento (COMMAND, TARGET, VIOLATION)
        command: Comando analizzato
        reason: Motivo del log
        blocked: True se l'azione è stata bloccata
    """
    import datetime
    
    log_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'security_audit.log')
    
    timestamp = datetime.datetime.now().isoformat()
    status = "BLOCKED" if blocked else "ALLOWED"
    
    log_line = f"[{timestamp}] [{status}] [{event_type}] {reason} | CMD: {command[:100]}\n"
    
    try:
        with open(log_file, 'a') as f:
            f.write(log_line)
    except Exception as e:
        logger.error(f"Failed to write security audit: {e}")

# ============================================================================
# INITIALIZATION
# ============================================================================

def get_security_status() -> dict:
    """Restituisce lo stato corrente della sicurezza."""
    return {
        "level": CURRENT_SECURITY_LEVEL.value,
        "whitelist_networks": len(_WHITELIST_NETWORKS),
        "banned_patterns": len(BANNED_DESTRUCTIVE_PATTERNS),
        "banned_tools_safe": len(BANNED_TOOLS_SAFE_MODE),
    }

# Log inizializzazione
logger.info(f"[SECURITY] Initialized with level: {CURRENT_SECURITY_LEVEL.value}")
logger.info(f"[SECURITY] Whitelist networks: {len(_WHITELIST_NETWORKS)}")
