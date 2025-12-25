#!/usr/bin/env python3
"""
HackTricks Source - Integrazione HackTricks (book.hacktricks.xyz)
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from datetime import datetime
from .base import DataSource, SourceResult

class HackTricksSource(DataSource):
    """Source per HackTricks"""
    
    BASE_URL = 'https://book.hacktricks.xyz'
    SITEMAP_URL = 'https://book.hacktricks.xyz/sitemap.xml'
    
    def __init__(self, enabled: bool = True):
        super().__init__('hacktricks', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-HackTricks/1.0'
        })
    
    def fetch(self, max_pages: int = 100) -> List[SourceResult]:
        """
        Fetcha contenuti da HackTricks.
        
        Args:
            max_pages: Numero massimo di pagine da processare
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # Ottieni sitemap
            print(f"[HackTricks] Fetching sitemap...")
            urls = self._get_sitemap_urls(max_pages)
            
            print(f"[HackTricks] Trovate {len(urls)} pagine")
            
            for url in urls:
                try:
                    page_result = self._fetch_page(url)
                    if page_result:
                        results.append(page_result)
                    
                    # Rate limiting
                    import time
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"[HackTricks] Errore processando {url}: {e}")
                    continue
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            print(f"[HackTricks] ✅ Processate {len(results)} pagine")
            
        except Exception as e:
            self.error_count += 1
            print(f"[HackTricks] Errore fetch: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def _get_sitemap_urls(self, max_urls: int) -> List[str]:
        """Ottiene lista URL dal sitemap"""
        urls = []
        
        try:
            response = self.session.get(self.SITEMAP_URL, timeout=30)
            if response.status_code == 200:
                # Parse XML sitemap
                from xml.etree import ElementTree as ET
                root = ET.fromstring(response.content)
                
                # Namespace
                ns = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
                
                for url_elem in root.findall('.//sitemap:loc', ns)[:max_urls]:
                    url = url_elem.text
                    if url and self.BASE_URL in url:
                        urls.append(url)
        except Exception as e:
            print(f"[HackTricks] Errore parsing sitemap: {e}")
            # Fallback: usa lista di pagine comuni
            urls = self._get_common_pages()[:max_urls]
        
        return urls
    
    def _get_common_pages(self) -> List[str]:
        """Lista di pagine comuni HackTricks"""
        return [
            f"{self.BASE_URL}/welcome/readme",
            f"{self.BASE_URL}/pentesting/pentesting-methodology",
            f"{self.BASE_URL}/pentesting-web",
            f"{self.BASE_URL}/pentesting/pentesting-linux",
            f"{self.BASE_URL}/pentesting/pentesting-windows",
            f"{self.BASE_URL}/cloud-security",
            f"{self.BASE_URL}/network-services-pentesting",
            f"{self.BASE_URL}/mobile-pentesting",
        ]
    
    def _fetch_page(self, url: str) -> Optional[SourceResult]:
        """Fetcha una singola pagina"""
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Estrai contenuto principale
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
            if not main_content:
                return None
            
            # Estrai titolo
            title_elem = soup.find('h1') or soup.find('title')
            title = title_elem.get_text(strip=True) if title_elem else url.split('/')[-1]
            
            # Estrai testo
            text = main_content.get_text(separator='\n', strip=True)
            
            # Estrai comandi e code blocks
            commands = self._extract_commands(main_content)
            
            # Pulisci testo (rimuovi navigazione, footer, ecc.)
            cleaned_text = self._clean_content(text)
            
            # Costruisci contenuto
            content = f"""
# {title}

{cleaned_text[:2000]}

## Commands and Code Snippets

{chr(10).join(f"- `{cmd}`" for cmd in commands[:20]) if commands else "No commands found"}
"""
            
            # Estrai categoria dal path
            path_parts = url.replace(self.BASE_URL, '').strip('/').split('/')
            category = path_parts[0] if path_parts else 'general'
            
            return SourceResult(
                title=title,
                content=content.strip(),
                source_type='knowledge_base',
                source_name='hacktricks',
                url=url,
                metadata={
                    'category': category,
                    'command_count': len(commands),
                    'source': 'hacktricks'
                },
                timestamp=datetime.now(),
                relevance_score=0.9
            )
            
        except Exception as e:
            print(f"[HackTricks] Errore fetch page {url}: {e}")
            return None
    
    def _extract_commands(self, soup: BeautifulSoup) -> List[str]:
        """Estrae comandi da una pagina"""
        commands = []
        
        # Cerca code blocks
        code_blocks = soup.find_all(['code', 'pre'])
        for block in code_blocks:
            cmd = block.get_text(strip=True)
            if cmd and len(cmd) > 5:
                # Filtra comandi validi
                if any(cmd.startswith(prefix) for prefix in ['nmap', 'nc ', 'curl', 'wget', 'python', 'bash', 'sqlmap', 'hydra', 'john']):
                    commands.append(cmd)
        
        return list(set(commands))[:30]
    
    def _clean_content(self, text: str) -> str:
        """Pulisce contenuto rimuovendo elementi non utili"""
        lines = text.split('\n')
        cleaned = []
        
        skip_patterns = [
            'navigation', 'menu', 'footer', 'sidebar', 'cookie',
            'privacy', 'terms', 'subscribe', 'newsletter'
        ]
        
        for line in lines:
            line_lower = line.lower()
            if not any(pattern in line_lower for pattern in skip_patterns):
                if line.strip():
                    cleaned.append(line)
        
        return '\n'.join(cleaned)
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'knowledge_base',
            'url': self.BASE_URL,
            'description': 'HackTricks - Comprehensive hacking techniques',
            'rate_limit': 'Respect robots.txt (0.5s delay)',
            'requires_auth': False
        }


