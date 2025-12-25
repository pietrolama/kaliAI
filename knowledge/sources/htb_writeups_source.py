#!/usr/bin/env python3
"""
Hack The Box Write-ups Source - Integrazione write-ups da HTB
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from datetime import datetime
from .base import DataSource, SourceResult

class HTBWriteupsSource(DataSource):
    """Source per Hack The Box write-ups"""
    
    OXDF_BASE = 'https://0xdf.gitlab.io'
    OXDF_SITEMAP = 'https://0xdf.gitlab.io/sitemap.xml'
    
    def __init__(self, enabled: bool = True):
        super().__init__('htb_writeups', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-HTB-Writeups/1.0'
        })
    
    def fetch(self, max_pages: int = 50, retired_only: bool = True) -> List[SourceResult]:
        """
        Fetcha write-ups da 0xdf e altre fonti.
        
        Args:
            max_pages: Numero massimo di pagine da processare
            retired_only: Se True, processa solo macchine ritirate
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # Fetch da 0xdf.gitlab.io
            print(f"[HTB Write-ups] Fetching da 0xdf.gitlab.io...")
            oxdf_results = self._fetch_oxdf(max_pages, retired_only)
            results.extend(oxdf_results)
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            print(f"[HTB Write-ups] ✅ Processati {len(results)} write-ups")
            
        except Exception as e:
            self.error_count += 1
            print(f"[HTB Write-ups] Errore fetch: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def _fetch_oxdf(self, max_pages: int, retired_only: bool) -> List[SourceResult]:
        """Fetcha write-ups da 0xdf.gitlab.io"""
        results = []
        
        try:
            # Ottieni sitemap o lista pagine
            # Per semplicità, usiamo una lista di macchine comuni
            # In produzione, si potrebbe fare scraping del sitemap
            
            # Lista di macchine HTB ritirate popolari
            machines = [
                'lame', 'legacy', 'blue', 'devel', 'optimum', 'bastard',
                'grandpa', 'granny', 'beep', 'tartarsauce', 'valentine',
                'poison', 'shocker', 'bashed', 'nibbles', 'cronos',
                'nineveh', 'sense', 'solidstate', 'node', 'sunday',
                'tally', 'arctic', 'bank', 'irked', 'friendzone'
            ]
            
            for machine in machines[:max_pages]:
                try:
                    url = f"{self.OXDF_BASE}/{machine}"
                    response = self.session.get(url, timeout=30)
                    
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    # Estrai contenuto principale
                    main_content = soup.find('main') or soup.find('article') or soup.find('body')
                    if not main_content:
                        continue
                    
                    # Estrai testo
                    text = main_content.get_text(separator='\n', strip=True)
                    
                    # Estrai comandi
                    commands = self._extract_commands(text, main_content)
                    
                    # Estrai fasi dell'attacco
                    phases = self._extract_phases(text)
                    
                    # Estrai vulnerabilità trovate
                    vulnerabilities = self._extract_vulnerabilities(text)
                    
                    # Costruisci case file
                    case_file = self._build_case_file(
                        machine_name=machine,
                        url=url,
                        text=text,
                        commands=commands,
                        phases=phases,
                        vulnerabilities=vulnerabilities
                    )
                    
                    # Estrai titolo
                    title_elem = soup.find('h1') or soup.find('title')
                    title = title_elem.get_text(strip=True) if title_elem else f"HTB {machine} Write-up"
                    
                    results.append(SourceResult(
                        title=title,
                        content=case_file,
                        source_type='ctf_writeup',
                        source_name='htb_writeups',
                        url=url,
                        metadata={
                            'machine_name': machine,
                            'platform': 'hack_the_box',
                            'command_count': len(commands),
                            'phase_count': len(phases),
                            'vulnerability_count': len(vulnerabilities),
                            'source': '0xdf'
                        },
                        timestamp=datetime.now(),
                        relevance_score=0.95
                    ))
                    
                except Exception as e:
                    print(f"[HTB Write-ups] Errore processando {machine}: {e}")
                    continue
        
        except Exception as e:
            print(f"[HTB Write-ups] Errore fetch oxdf: {e}")
        
        return results
    
    def _extract_commands(self, text: str, soup: Optional[BeautifulSoup] = None) -> List[Dict]:
        """Estrae comandi dal write-up"""
        commands = []
        
        # Pattern per comandi comuni
        command_patterns = [
            r'(?:^|\n)\$?\s*([a-z]+(?:-[a-z]+)*\s+[^\n]+)',  # Comandi shell
            r'```(?:bash|sh|shell)?\n([^`]+)```',  # Code blocks
            r'`([^`]+)`',  # Inline code
        ]
        
        for pattern in command_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                cmd = match.group(1).strip()
                # Filtra comandi validi
                if self._is_valid_command(cmd):
                    commands.append({
                        'command': cmd,
                        'context': self._get_command_context(text, match.start())
                    })
        
        # Estrai anche da code blocks HTML
        if soup:
            code_blocks = soup.find_all(['code', 'pre'])
            for block in code_blocks:
                cmd_text = block.get_text(strip=True)
                if self._is_valid_command(cmd_text):
                    commands.append({
                        'command': cmd_text,
                        'context': 'code_block'
                    })
        
        # Rimuovi duplicati
        seen = set()
        unique_commands = []
        for cmd in commands:
            cmd_str = cmd['command']
            if cmd_str not in seen:
                seen.add(cmd_str)
                unique_commands.append(cmd)
        
        return unique_commands[:50]  # Limita a 50 comandi
    
    def _is_valid_command(self, cmd: str) -> bool:
        """Verifica se è un comando valido"""
        if not cmd or len(cmd) < 3:
            return False
        
        # Rimuovi prompt
        cmd = re.sub(r'^\$?\s*', '', cmd)
        
        # Comandi comuni in pentesting
        valid_prefixes = [
            'nmap', 'nc ', 'netcat', 'curl', 'wget', 'python', 'python3',
            'bash', 'sh', 'sqlmap', 'hydra', 'john', 'hashcat', 'msfconsole',
            'msfvenom', 'searchsploit', 'gobuster', 'dirb', 'nikto', 'enum4linux',
            'smbclient', 'smbmap', 'rpcclient', 'impacket', 'psexec', 'winexe',
            'ssh', 'scp', 'ftp', 'telnet', 'mysql', 'psql', 'mongo', 'redis-cli',
            'sudo', 'su', 'id', 'whoami', 'uname', 'cat', 'less', 'more',
            'grep', 'find', 'locate', 'which', 'whereis', 'ls', 'pwd', 'cd',
            'chmod', 'chown', 'tar', 'zip', 'unzip', 'base64', 'xxd', 'hexdump',
            'strings', 'file', 'readelf', 'objdump', 'gdb', 'strace', 'ltrace'
        ]
        
        return any(cmd.lower().startswith(prefix) for prefix in valid_prefixes)
    
    def _get_command_context(self, text: str, position: int) -> str:
        """Ottiene contesto intorno a un comando"""
        start = max(0, position - 100)
        end = min(len(text), position + 200)
        context = text[start:end]
        return context[:150] + '...' if len(context) > 150 else context
    
    def _extract_phases(self, text: str) -> List[Dict]:
        """Estrae fasi dell'attacco (ricognizione, sfruttamento, ecc.)"""
        phases = []
        
        # Pattern per fasi comuni
        phase_patterns = [
            (r'(?:^|\n)(?:#+\s*)?(?:recon|reconnaissance|nmap|scanning)', 'reconnaissance'),
            (r'(?:^|\n)(?:#+\s*)?(?:exploit|exploitation|vulnerability)', 'exploitation'),
            (r'(?:^|\n)(?:#+\s*)?(?:privilege|privesc|escalation)', 'privilege_escalation'),
            (r'(?:^|\n)(?:#+\s*)?(?:root|flag|proof)', 'root_access'),
        ]
        
        for pattern, phase_name in phase_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE | re.IGNORECASE)
            for match in matches:
                # Estrai contenuto della fase
                start = match.start()
                end = min(len(text), start + 500)
                phase_content = text[start:end]
                
                phases.append({
                    'phase': phase_name,
                    'content': phase_content[:300]
                })
        
        return phases
    
    def _extract_vulnerabilities(self, text: str) -> List[str]:
        """Estrae vulnerabilità menzionate"""
        vulnerabilities = []
        
        # Pattern per vulnerabilità
        vuln_patterns = [
            r'CVE-\d{4}-\d+',
            r'(?:vulnerable|vulnerability|exploit|CVE|RCE|LFI|RFI|SQLi|XSS|CSRF)',
            r'(?:version|v\.?)\s*[\d.]+',
        ]
        
        for pattern in vuln_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                vuln = match.group(0)
                if vuln not in vulnerabilities:
                    vulnerabilities.append(vuln)
        
        return vulnerabilities[:20]
    
    def _build_case_file(self, machine_name: str, url: str, text: str,
                        commands: List[Dict], phases: List[Dict],
                        vulnerabilities: List[str]) -> str:
        """Costruisce case file strutturato"""
        
        case_file = f"""
# HTB Write-up Case File: {machine_name}

## Obiettivo
Ottenere accesso root sulla macchina '{machine_name}' di Hack The Box.

## Source
{url}

## Fasi dell'Attacco

"""
        
        # Aggiungi fasi
        for phase in phases:
            case_file += f"### {phase['phase'].replace('_', ' ').title()}\n"
            case_file += f"{phase['content']}\n\n"
        
        # Aggiungi comandi chiave
        case_file += "## Comandi Chiave\n\n"
        for i, cmd in enumerate(commands[:20], 1):
            case_file += f"{i}. `{cmd['command']}`\n"
            if cmd.get('context'):
                case_file += f"   Context: {cmd['context'][:100]}...\n"
        
        # Aggiungi vulnerabilità
        if vulnerabilities:
            case_file += "\n## Vulnerabilità Identificate\n\n"
            for vuln in vulnerabilities:
                case_file += f"- {vuln}\n"
        
        # Aggiungi lezioni apprese
        case_file += "\n## Lezioni Apprese\n\n"
        case_file += self._extract_lessons(text, commands, vulnerabilities)
        
        # Aggiungi contenuto completo
        case_file += f"\n## Contenuto Completo\n\n{text[:2000]}...\n"
        
        return case_file.strip()
    
    def _extract_lessons(self, text: str, commands: List[Dict], vulnerabilities: List[str]) -> str:
        """Estrae lezioni apprese dal write-up"""
        lessons = []
        
        # Pattern per lezioni comuni
        lesson_patterns = [
            r'(?:lesson|learned|takeaway|note|tip|important)',
            r'(?:always|remember|check|verify|test)',
        ]
        
        # Cerca sezioni con lezioni
        for pattern in lesson_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                start = match.start()
                end = min(len(text), start + 200)
                lesson_text = text[start:end]
                if lesson_text not in lessons:
                    lessons.append(lesson_text[:150])
        
        # Se non trovi lezioni esplicite, genera da vulnerabilità
        if not lessons and vulnerabilities:
            lessons.append(f"Identificate {len(vulnerabilities)} vulnerabilità. Verificare sempre versioni software e cercare exploit noti.")
        
        if not lessons and commands:
            lessons.append(f"Utilizzati {len(commands)} comandi durante l'attacco. Documentare sequenza per riferimento futuro.")
        
        return '\n'.join(f"- {lesson}" for lesson in lessons[:5])
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'ctf_writeup',
            'url': self.OXDF_BASE,
            'description': 'Hack The Box write-ups from 0xdf and other sources',
            'rate_limit': 'Respect robots.txt',
            'requires_auth': False
        }


