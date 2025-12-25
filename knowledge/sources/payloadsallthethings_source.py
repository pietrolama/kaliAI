#!/usr/bin/env python3
"""
PayloadsAllTheThings Source - Integrazione repository GitHub PayloadsAllTheThings
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from .base import DataSource, SourceResult

class PayloadsAllTheThingsSource(DataSource):
    """Source per PayloadsAllTheThings repository"""
    
    REPO_URL = 'https://github.com/swisskyrepo/PayloadsAllTheThings.git'
    REPO_NAME = 'PayloadsAllTheThings'
    
    def __init__(self, enabled: bool = True, repo_path: Optional[str] = None):
        super().__init__('payloadsallthethings', enabled)
        self.repo_path = repo_path or Path(__file__).parent.parent.parent / 'data' / 'PayloadsAllTheThings'
        self.repo_path = Path(self.repo_path)
    
    def fetch(self, update_repo: bool = True, max_files: Optional[int] = None):
        """
        Fetcha payload da PayloadsAllTheThings repository.
        
        Args:
            update_repo: Se True, aggiorna il repository con git pull
            max_files: Numero massimo di file da processare (None = tutti)
            
        Yields:
            SourceResult
        """
        if not self.enabled:
            return
        
        count = 0
        
        try:
            # Clona o aggiorna repository
            if not self.repo_path.exists() or update_repo:
                self._ensure_repo()
            
            if not self.repo_path.exists():
                print(f"[PayloadsAllTheThings] Repository non trovato: {self.repo_path}")
                return
            
            # Processa tutti i file .md
            md_files = list(self.repo_path.rglob('*.md'))
            
            if max_files:
                md_files = md_files[:max_files]
            
            print(f"[PayloadsAllTheThings] Trovati {len(md_files)} file Markdown")
            
            for md_file in md_files:
                try:
                    # Salta file README generici
                    if md_file.name.lower() == 'readme.md' and md_file.parent.name.lower() != 'payloadsallthethings':
                        continue
                    
                    # Leggi e processa file
                    content = md_file.read_text(encoding='utf-8', errors='ignore')
                    
                    # Estrai metadati dal path
                    relative_path = md_file.relative_to(self.repo_path)
                    path_parts = relative_path.parts
                    
                    # Categoria principale (prima directory dopo root)
                    category = path_parts[0] if len(path_parts) > 1 else 'general'
                    
                    # Subcategory (seconda directory se esiste)
                    subcategory = path_parts[1] if len(path_parts) > 2 else None
                    
                    # Nome tecnica (nome file senza estensione)
                    technique = md_file.stem
                    
                    # Pulisci contenuto (rimuovi code blocks troppo lunghi)
                    cleaned_content = self._clean_markdown(content)
                    
                    if not cleaned_content or len(cleaned_content) < 50:
                        continue
                    
                    # Crea titolo descrittivo
                    title = f"{category}"
                    if subcategory:
                        title += f" - {subcategory}"
                    title += f" - {technique}"
                    
                    # Estrai payload e comandi
                    payloads = self._extract_payloads(content)
                    commands = self._extract_commands(content)
                    
                    # Costruisci contenuto completo
                    full_content = f"""
{title}

CATEGORY: {category}
{'SUBCATEGORY: ' + subcategory if subcategory else ''}
TECHNIQUE: {technique}

DESCRIPTION:
{cleaned_content[:1000]}

{'PAYLOADS:' if payloads else ''}
{chr(10).join(payloads[:5]) if payloads else ''}

{'COMMANDS:' if commands else ''}
{chr(10).join(commands[:5]) if commands else ''}

SOURCE: {relative_path}
"""
                    
                    # Calcola relevance score basato su contenuto
                    relevance = self._calculate_relevance(content, payloads, commands)
                    
                    yield SourceResult(
                        title=title,
                        content=full_content.strip(),
                        source_type='payload',
                        source_name='payloadsallthethings',
                        url=f"{self.REPO_URL.replace('.git', '')}/blob/master/{relative_path}",
                        metadata={
                            'category': category,
                            'subcategory': subcategory,
                            'technique': technique,
                            'file_path': str(relative_path),
                            'has_payloads': len(payloads) > 0,
                            'has_commands': len(commands) > 0,
                            'payload_count': len(payloads),
                            'command_count': len(commands)
                        },
                        timestamp=datetime.fromtimestamp(md_file.stat().st_mtime),
                        relevance_score=relevance
                    )
                    count += 1
                    
                except Exception as e:
                    print(f"[PayloadsAllTheThings] Errore processando {md_file}: {e}")
                    continue
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            print(f"[PayloadsAllTheThings] ✅ Processati {count} documenti")
            
        except Exception as e:
            self.error_count += 1
            print(f"[PayloadsAllTheThings] Errore fetch: {e}")
            import traceback
            traceback.print_exc()
    
    def _ensure_repo(self):
        """Assicura che il repository sia clonato/aggiornato"""
        import subprocess
        
        if self.repo_path.exists():
            # Repository esiste, fai pull
            try:
                print(f"[PayloadsAllTheThings] Aggiornamento repository...")
                subprocess.run(
                    ['git', 'pull'],
                    cwd=self.repo_path,
                    check=True,
                    capture_output=True,
                    timeout=300
                )
                print(f"[PayloadsAllTheThings] ✅ Repository aggiornato")
            except subprocess.TimeoutExpired:
                print(f"[PayloadsAllTheThings] ⚠️ Timeout durante git pull")
            except subprocess.CalledProcessError as e:
                print(f"[PayloadsAllTheThings] ⚠️ Errore git pull: {e}")
        else:
            # Clona repository
            try:
                print(f"[PayloadsAllTheThings] Clonazione repository...")
                self.repo_path.parent.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ['git', 'clone', self.REPO_URL, str(self.repo_path)],
                    check=True,
                    capture_output=True,
                    timeout=600
                )
                print(f"[PayloadsAllTheThings] ✅ Repository clonato")
            except subprocess.TimeoutExpired:
                print(f"[PayloadsAllTheThings] ⚠️ Timeout durante git clone")
            except subprocess.CalledProcessError as e:
                print(f"[PayloadsAllTheThings] ⚠️ Errore git clone: {e}")
    
    def _clean_markdown(self, content: str) -> str:
        """Pulisce markdown rimuovendo code blocks troppo lunghi"""
        # Rimuovi code blocks molto lunghi (> 50 righe)
        lines = content.split('\n')
        cleaned_lines = []
        in_code_block = False
        code_block_lines = 0
        
        for line in lines:
            if line.strip().startswith('```'):
                if in_code_block:
                    # Fine code block
                    if code_block_lines <= 50:
                        cleaned_lines.append(line)
                    in_code_block = False
                    code_block_lines = 0
                else:
                    # Inizio code block
                    cleaned_lines.append(line)
                    in_code_block = True
            elif in_code_block:
                code_block_lines += 1
                if code_block_lines <= 50:
                    cleaned_lines.append(line)
            else:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    def _extract_payloads(self, content: str) -> List[str]:
        """Estrae payload da code blocks"""
        payloads = []
        
        # Pattern per code blocks
        code_block_pattern = r'```[\w]*\n(.*?)```'
        matches = re.findall(code_block_pattern, content, re.DOTALL)
        
        for match in matches:
            payload = match.strip()
            # Filtra payload troppo lunghi o corti
            if 10 <= len(payload) <= 500:
                payloads.append(payload)
        
        return payloads[:20]  # Limita a 20 payload
    
    def _extract_commands(self, content: str) -> List[str]:
        """Estrae comandi shell/script"""
        commands = []
        
        # Pattern per comandi comuni
        command_patterns = [
            r'`([^`]+)`',  # Inline code
            r'\$ (.+)',    # Comandi shell
            r'# (.+)',     # Comandi commentati
        ]
        
        for pattern in command_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                cmd = match.strip()
                # Filtra comandi validi
                if cmd and len(cmd) > 5 and any(cmd.startswith(prefix) for prefix in ['curl', 'wget', 'nc ', 'python', 'bash', 'sqlmap', 'nmap', 'msf']):
                    commands.append(cmd)
        
        return list(set(commands))[:20]  # Rimuovi duplicati, limita a 20
    
    def _calculate_relevance(self, content: str, payloads: List[str], commands: List[str]) -> float:
        """Calcola relevance score"""
        score = 0.5  # Base
        
        # Bonus per payload
        if payloads:
            score += 0.2
        
        # Bonus per comandi
        if commands:
            score += 0.2
        
        # Bonus per contenuto dettagliato
        if len(content) > 500:
            score += 0.1
        
        return min(score, 1.0)
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'payload_repository',
            'url': self.REPO_URL.replace('.git', ''),
            'description': 'PayloadsAllTheThings - Comprehensive payload collection',
            'rate_limit': None,
            'requires_auth': False,
            'repo_path': str(self.repo_path)
        }


