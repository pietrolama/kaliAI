#!/usr/bin/env python3
"""
Tool Manager - Gestione automatica installazione tool di pentesting.
Installa automaticamente tool mancanti quando richiesti.
"""

import subprocess
import logging
import os
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger('ToolManager')


class ToolManager:
    """Gestisce installazione e verifica tool di pentesting."""
    
    # Database tool comuni di pentesting
    TOOLS = {
        # Base system tools (sempre presenti)
        'nmap': {
            'package': 'nmap',
            'check_cmd': 'which nmap',
            'description': 'Network scanner'
        },
        'curl': {
            'package': 'curl',
            'check_cmd': 'which curl',
            'description': 'HTTP client'
        },
        'wget': {
            'package': 'wget',
            'check_cmd': 'which wget',
            'description': 'File downloader'
        },
        'nc': {
            'package': 'netcat-traditional',
            'check_cmd': 'which nc',
            'description': 'Netcat'
        },
        
        # Web scanning
        'dirb': {
            'package': 'dirb',
            'check_cmd': 'which dirb',
            'description': 'Directory bruteforcer web'
        },
        'gobuster': {
            'package': 'gobuster',
            'check_cmd': 'which gobuster',
            'description': 'Directory/DNS bruteforcer veloce'
        },
        'whatweb': {
            'package': 'whatweb',
            'check_cmd': 'which whatweb',
            'description': 'Web technology identifier'
        },
        'nikto': {
            'package': 'nikto',
            'check_cmd': 'which nikto',
            'description': 'Web server scanner'
        },
        
        # SQL Injection
        'sqlmap': {
            'package': 'sqlmap',
            'check_cmd': 'which sqlmap',
            'description': 'Automatic SQL injection tool'
        },
        
        # Network
        'masscan': {
            'package': 'masscan',
            'check_cmd': 'which masscan',
            'description': 'Fast port scanner'
        },
        'netcat': {
            'package': 'netcat-traditional',
            'check_cmd': 'which nc',
            'description': 'Network Swiss Army knife'
        },
        
        # Password
        'hydra': {
            'package': 'hydra',
            'check_cmd': 'which hydra',
            'description': 'Password cracker'
        },
        'john': {
            'package': 'john',
            'check_cmd': 'which john',
            'description': 'John the Ripper password cracker'
        },
        
        # Wireless
        'aircrack-ng': {
            'package': 'aircrack-ng',
            'check_cmd': 'which aircrack-ng',
            'description': 'WiFi security auditing'
        },
        
        # Exploitation
        'metasploit-framework': {
            'package': 'metasploit-framework',
            'check_cmd': 'which msfconsole',
            'description': 'Penetration testing framework'
        },
        
        # Web proxies
        'burpsuite': {
            'package': 'burpsuite',
            'check_cmd': 'which burpsuite',
            'description': 'Web security testing (community edition)',
            'optional': True  # Non critico
        },
        
        # Fuzzing
        'wfuzz': {
            'package': 'wfuzz',
            'check_cmd': 'which wfuzz',
            'description': 'Web application fuzzer'
        },
        
        # SSL/TLS
        'sslscan': {
            'package': 'sslscan',
            'check_cmd': 'which sslscan',
            'description': 'SSL/TLS scanner'
        },
        'testssl': {
            'package': 'testssl.sh',
            'check_cmd': 'which testssl',
            'description': 'SSL/TLS testing tool',
            'optional': True
        },
        
        # DNS
        'dnsrecon': {
            'package': 'dnsrecon',
            'check_cmd': 'which dnsrecon',
            'description': 'DNS enumeration tool'
        },
        'dnsenum': {
            'package': 'dnsenum',
            'check_cmd': 'which dnsenum',
            'description': 'DNS enumeration tool'
        },
        
        # Misc
        'ffmpeg': {
            'package': 'ffmpeg',
            'check_cmd': 'which ffmpeg',
            'description': 'Multimedia framework (per streaming)'
        },
        'exiftool': {
            'package': 'libimage-exiftool-perl',
            'check_cmd': 'which exiftool',
            'description': 'Metadata extraction'
        }
    }
    
    def __init__(self):
        self.installed_cache = {}
    
    def is_tool_installed(self, tool_name: str) -> bool:
        """Verifica se un tool è installato."""
        # Check cache
        if tool_name in self.installed_cache:
            return self.installed_cache[tool_name]
        
        if tool_name not in self.TOOLS:
            logger.warning(f"Tool '{tool_name}' non nel database")
            return False
        
        check_cmd = self.TOOLS[tool_name]['check_cmd']
        
        try:
            result = subprocess.run(
                check_cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5
            )
            installed = result.returncode == 0
            self.installed_cache[tool_name] = installed
            return installed
        except Exception as e:
            logger.error(f"Errore check tool {tool_name}: {e}")
            return False
    
    def install_tool(self, tool_name: str, auto_yes: bool = True) -> Tuple[bool, str]:
        """
        Installa un tool.
        
        Args:
            tool_name: Nome del tool da installare
            auto_yes: Se True, usa -y per installazione automatica
            
        Returns:
            Tuple[success, message]
        """
        if tool_name not in self.TOOLS:
            return False, f"Tool '{tool_name}' non supportato"
        
        # Check se già installato
        if self.is_tool_installed(tool_name):
            return True, f"{tool_name} già installato"
        
        tool_info = self.TOOLS[tool_name]
        package = tool_info['package']
        
        logger.info(f"Installazione {tool_name} ({package}) in corso...")
        
        # Usa apt-get (Debian/Kali)
        cmd = f"apt-get update && apt-get install {'-y' if auto_yes else ''} {package}"
        
        try:
            # NOTA: Richiede sudo in produzione
            # Per ora usiamo senza sudo (assume ambiente già privilegiato o pre-installato)
            result = subprocess.run(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=300,  # 5 minuti max
                text=True
            )
            
            if result.returncode == 0:
                # Verifica installazione
                if self.is_tool_installed(tool_name):
                    logger.info(f"✅ {tool_name} installato con successo")
                    return True, f"{tool_name} installato correttamente"
                else:
                    return False, f"Installazione completata ma {tool_name} non trovato"
            else:
                error = result.stderr[:500]
                logger.error(f"Installazione {tool_name} fallita: {error}")
                return False, f"Errore installazione: {error}"
                
        except subprocess.TimeoutExpired:
            return False, f"Timeout installazione {tool_name} (>5 min)"
        except Exception as e:
            return False, f"Errore: {str(e)}"
    
    def auto_install_if_missing(self, tool_name: str) -> bool:
        """
        Installa automaticamente se mancante.
        
        Returns:
            True se tool disponibile (già installato o appena installato)
        """
        if self.is_tool_installed(tool_name):
            return True
        
        # Tool opzionali non vengono auto-installati
        if self.TOOLS.get(tool_name, {}).get('optional', False):
            logger.info(f"{tool_name} è opzionale, skip auto-install")
            return False
        
        logger.warning(f"Tool {tool_name} mancante, tentativo auto-install...")
        success, message = self.install_tool(tool_name)
        
        if success:
            logger.info(f"✅ {tool_name} installato automaticamente")
        else:
            logger.error(f"❌ Auto-install {tool_name} fallito: {message}")
        
        return success
    
    def get_missing_tools(self, tool_list: List[str]) -> List[str]:
        """Ritorna lista tool mancanti."""
        return [tool for tool in tool_list if not self.is_tool_installed(tool)]
    
    def install_pentest_suite(self) -> Dict[str, bool]:
        """Installa suite completa tool di pentesting."""
        essential_tools = [
            'dirb', 'gobuster', 'whatweb', 'nikto', 'sqlmap',
            'masscan', 'netcat', 'hydra', 'wfuzz', 'sslscan',
            'dnsrecon', 'ffmpeg'
        ]
        
        results = {}
        for tool in essential_tools:
            if self.is_tool_installed(tool):
                results[tool] = True
                logger.info(f"✅ {tool} già installato")
            else:
                success, _ = self.install_tool(tool)
                results[tool] = success
        
        return results
    
    def get_tool_stats(self) -> Dict[str, any]:
        """Ritorna statistiche tool installati."""
        total = len(self.TOOLS)
        installed = sum(1 for tool in self.TOOLS.keys() if self.is_tool_installed(tool))
        optional = sum(1 for t in self.TOOLS.values() if t.get('optional', False))
        
        return {
            'total_tools': total,
            'installed': installed,
            'missing': total - installed,
            'optional_tools': optional,
            'coverage': f"{installed/total*100:.1f}%"
        }
    
    def list_missing_tools(self) -> List[Dict[str, str]]:
        """Lista tool mancanti con descrizione."""
        missing = []
        for tool_name, info in self.TOOLS.items():
            if not self.is_tool_installed(tool_name):
                missing.append({
                    'name': tool_name,
                    'package': info['package'],
                    'description': info['description'],
                    'optional': info.get('optional', False)
                })
        return missing


# Istanza globale
tool_manager = ToolManager()


def ensure_tool_available(tool_name: str) -> bool:
    """
    Helper function per garantire che un tool sia disponibile.
    Installa automaticamente se mancante.
    
    Usage:
        if ensure_tool_available('dirb'):
            os.system('dirb http://target.com')
    """
    return tool_manager.auto_install_if_missing(tool_name)


if __name__ == "__main__":
    # Test
    logging.basicConfig(level=logging.INFO)
    
    print("=== TOOL MANAGER TEST ===\n")
    
    # Stats
    stats = tool_manager.get_tool_stats()
    print(f"Tool totali: {stats['total_tools']}")
    print(f"Installati: {stats['installed']}")
    print(f"Mancanti: {stats['missing']}")
    print(f"Coverage: {stats['coverage']}\n")
    
    # Missing
    missing = tool_manager.list_missing_tools()
    if missing:
        print(f"Tool mancanti ({len(missing)}):")
        for tool in missing[:10]:
            opt = " (opzionale)" if tool['optional'] else ""
            print(f"  - {tool['name']}: {tool['description']}{opt}")

