import re
import logging
from typing import List, Tuple
from tools.error_handling import SecurityError

logger = logging.getLogger('Security')


class SecurityValidator:
    """Validazione sicurezza comandi bash."""
    
    # Pattern pericolosi (regex)
    BLOCKED_PATTERNS = [
        r"rm\s+-rf\s+/",           # rm -rf /
        r"mkfs",                    # Format filesystem
        r"dd\s+if=",               # Disk dump
        r"chmod\s+777",            # Permessi troppo aperti
        r"chown\s+root",           # Change owner to root
        r"passwd",                  # Change password
        r"visudo",                  # Edit sudoers
        r"adduser",                 # Add user
        r"useradd",                 # Add user
        r"^su\s+-",                # Switch user (solo all'inizio comando)
        r"\|\s*bash",              # Pipeline to bash
        r"\|\s*sh\s",              # Pipeline to sh
        r"wget.*\|",               # Download and pipe
        r"curl.*\|.*bash",         # Download and execute
        r"curl.*\|.*sh",           # Download and execute
        r">\s*/dev/sd[a-z]",       # Write to disk
        r":\s*\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;",  # Fork bomb
        r"rm\s+-f\s+/",            # Dangerous rm
        r"/etc/passwd",            # Manipulate passwd
        r"/etc/shadow",            # Manipulate shadow
    ]
    
    # Comandi bloccati (exact match della prima parola)
    BLOCKED_COMMANDS = [
        'sudo', 'su', 'passwd', 'visudo', 'adduser', 'useradd',
        'deluser', 'userdel', 'groupadd', 'groupdel', 'mkfs',
        'fdisk', 'parted', 'shutdown', 'reboot', 'init', 'systemctl'
    ]
    
    # Comandi permessi (whitelist per sicurezza extra)
    ALLOWED_COMMANDS = [
        'ls', 'cat', 'echo', 'grep', 'find', 'awk', 'sed', 'head', 'tail',
        'wc', 'sort', 'uniq', 'cut', 'tr', 'diff', 'comm', 'join',
        'nmap', 'curl', 'wget', 'ping', 'nc', 'telnet', 'ssh', 'scp',
        'git', 'python', 'python3', 'pip', 'node', 'npm',
        'docker', 'kubectl', 'helm',
        'ip', 'ifconfig', 'route', 'netstat', 'ss', 'tcpdump',
        'ps', 'top', 'htop', 'kill', 'killall',
        'touch', 'mkdir', 'cp', 'mv', 'rm', 'rmdir',
        'tar', 'gzip', 'gunzip', 'zip', 'unzip',
        'for', 'while', 'if', 'test', '[', 'cd', 'pwd', 'export'
    ]
    
    @classmethod
    def validate_command(cls, command: str, strict_mode: bool = False, bypass: bool = False,
                        security_profile: str = "LOCAL_READONLY") -> Tuple[bool, str]:
        """
        Valida un comando bash per sicurezza.
        
        Args:
            command: Comando da validare
            strict_mode: Modalità strict (default False)
            bypass: Legacy bypass flag (maps to UNRESTRICTED profile)
            security_profile: Security profile to use:
                - LOCAL_READONLY: Read operations only
                - LOCAL_SAFE: Basic local operations
                - RECON_ONLY: Network discovery only
                - ARENA_EXEC: Full execution in arena
                - UNRESTRICTED: All commands allowed (dangerous!)
            
        Returns:
            Tuple[bool, str]: (is_valid, reason)
        """
        # Map legacy bypass to UNRESTRICTED profile
        if bypass:
            security_profile = "UNRESTRICTED"
        
        # Log with profile name instead of "BYPASS"
        if security_profile == "UNRESTRICTED":
            logger.warning(f"⚠️ SECURITY PROFILE: UNRESTRICTED for: {command[:80]}")
            return True, f"Profile: {security_profile}"
        elif security_profile in ["LOCAL_SAFE", "ARENA_EXEC", "RECON_ONLY"]:
            logger.info(f"[SECURITY] PROFILE: {security_profile} for: {command[:60]}")
        
        if not command or len(command.strip()) == 0:
            return False, "Comando vuoto"
        
        command_lower = command.lower().strip()
        
        # 1. Check primo comando (prima parola)
        first_word = command_lower.split()[0] if command_lower.split() else ""
        
        # Rimuovi eventuali prefissi (export, for, while)
        if first_word in ['export', 'for', 'while', 'if']:
            parts = command_lower.split()
            if len(parts) > 1:
                first_word = parts[1]
        
        # Check comandi bloccati
        if first_word in cls.BLOCKED_COMMANDS:
            return False, f"Comando bloccato: {first_word}"
        
        # Strict mode: solo comandi in whitelist
        if strict_mode and first_word not in cls.ALLOWED_COMMANDS:
            return False, f"Comando non in whitelist: {first_word}"
        
        # 2. Check pattern pericolosi
        for pattern in cls.BLOCKED_PATTERNS:
            if re.search(pattern, command_lower):
                return False, f"Pattern pericoloso rilevato: {pattern}"
        
        # 3. Check lunghezza ragionevole
        if len(command) > 5000:
            return False, "Comando troppo lungo"
        
        # 4. Check caratteri sospetti multipli
        if command.count(';') > 10:
            return False, "Troppi separatori di comando"
        
        # 5. Check path traversal
        if '../' in command and 'cd ../' not in command_lower:
            # Permetti cd ../ ma blocca altri path traversal
            if not command_lower.startswith('cd ../'):
                return False, "Path traversal sospetto"
        
        return True, "OK"
    
    @classmethod
    def sanitize_command(cls, command: str) -> str:
        """
        Sanitizza un comando rimuovendo caratteri pericolosi.
        NON garantisce sicurezza completa - usare validate_command prima!
        """
        # Rimuovi caratteri null
        command = command.replace('\x00', '')
        
        # Rimuovi commenti bash inline (solo se non in stringa)
        # TODO: parsing più sofisticato per non rompere stringhe
        
        # Trim whitespace
        command = command.strip()
        
        return command
    
    @classmethod
    def extract_commands_from_text(cls, text: str) -> List[str]:
        """
        Estrae comandi bash da testo (backticks, code blocks).
        """
        commands = []
        
        # Pattern 1: Backticks singoli `comando`
        backtick_pattern = r'`([^`\n]{5,200})`'
        matches = re.findall(backtick_pattern, text)
        commands.extend(matches)
        
        # Pattern 2: Code blocks bash
        bash_block_pattern = r'```bash\s*\n(.*?)\n```'
        matches = re.findall(bash_block_pattern, text, re.DOTALL)
        for match in matches:
            # Split per linee e prendi comandi validi
            lines = [l.strip() for l in match.split('\n') if l.strip() and not l.strip().startswith('#')]
            commands.extend(lines)
        
        # Pattern 3: Prompt style ($ comando)
        prompt_pattern = r'^\$\s+([a-zA-Z][^\n]{4,200})$'
        matches = re.findall(prompt_pattern, text, re.MULTILINE)
        commands.extend(matches)
        
        return commands
    
    @classmethod
    def validate_and_filter_commands(cls, commands: List[str], strict_mode: bool = False) -> List[str]:
        """
        Valida una lista di comandi e ritorna solo quelli sicuri.
        """
        safe_commands = []
        
        for cmd in commands:
            cmd = cmd.strip()
            is_valid, reason = cls.validate_command(cmd, strict_mode)
            
            if is_valid:
                safe_commands.append(cmd)
            else:
                logger.warning(f"Comando bloccato: {cmd[:50]} - {reason}")
        
        return safe_commands


class SecurityAuditor:
    """Audit e logging operazioni di sicurezza."""
    
    def __init__(self):
        self.blocked_commands = []
        self.allowed_commands = []
    
    def log_blocked(self, command: str, reason: str):
        """Logga comando bloccato."""
        entry = {
            "command": command[:200],
            "reason": reason,
            "timestamp": self._get_timestamp()
        }
        self.blocked_commands.append(entry)
        logger.warning(f"[SECURITY] Bloccato: {command[:100]} - {reason}")
    
    def log_allowed(self, command: str):
        """Logga comando permesso."""
        entry = {
            "command": command[:200],
            "timestamp": self._get_timestamp()
        }
        self.allowed_commands.append(entry)
        logger.info(f"[SECURITY] Permesso: {command[:100]}")
    
    def get_stats(self):
        """Ritorna statistiche sicurezza."""
        return {
            "blocked_count": len(self.blocked_commands),
            "allowed_count": len(self.allowed_commands),
            "blocked_recent": self.blocked_commands[-10:],
            "allowed_recent": self.allowed_commands[-10:]
        }
    
    @staticmethod
    def _get_timestamp():
        from datetime import datetime
        return datetime.now().isoformat()


# Istanza globale auditor
auditor = SecurityAuditor()

