#!/usr/bin/env python3
"""
OWASP Cheat Sheets Source - Integrazione OWASP Cheat Sheet Series
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from datetime import datetime
from .base import DataSource, SourceResult

class OWASPCheatSheetsSource(DataSource):
    """Source per OWASP Cheat Sheet Series"""
    
    BASE_URL = 'https://cheatsheetseries.owasp.org'
    INDEX_URL = 'https://cheatsheetseries.owasp.org/Index.html'
    
    def __init__(self, enabled: bool = True):
        super().__init__('owasp_cheatsheets', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-OWASP-CheatSheets/1.0'
        })
    
    def fetch(self, max_sheets: int = 50) -> List[SourceResult]:
        """
        Fetcha cheat sheets da OWASP.
        
        Args:
            max_sheets: Numero massimo di cheat sheets da processare
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # Ottieni lista di cheat sheets
            print(f"[OWASP Cheat Sheets] Fetching index...")
            sheet_urls = self._get_cheatsheet_urls(max_sheets)
            
            print(f"[OWASP Cheat Sheets] Trovate {len(sheet_urls)} cheat sheets")
            
            for url in sheet_urls:
                try:
                    sheet_result = self._fetch_cheatsheet(url)
                    if sheet_result:
                        results.append(sheet_result)
                    
                    # Rate limiting
                    import time
                    time.sleep(0.5)
                    
                except Exception as e:
                    print(f"[OWASP Cheat Sheets] Errore processando {url}: {e}")
                    continue
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            print(f"[OWASP Cheat Sheets] ✅ Processate {len(results)} cheat sheets")
            
        except Exception as e:
            self.error_count += 1
            print(f"[OWASP Cheat Sheets] Errore fetch: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def _get_cheatsheet_urls(self, max_urls: int) -> List[str]:
        """Ottiene lista di URL delle cheat sheets"""
        urls = []
        
        try:
            response = self.session.get(self.INDEX_URL, timeout=30)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Cerca link alle cheat sheets
                links = soup.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    if href and href.endswith('.html') and 'Index' not in href:
                        full_url = f"{self.BASE_URL}/{href}" if not href.startswith('http') else href
                        if full_url not in urls:
                            urls.append(full_url)
                            if len(urls) >= max_urls:
                                break
        except Exception as e:
            print(f"[OWASP Cheat Sheets] Errore fetching index: {e}")
            # Fallback: lista comune
            urls = self._get_common_sheets()[:max_urls]
        
        return urls
    
    def _get_common_sheets(self) -> List[str]:
        """Lista di cheat sheets comuni"""
        return [
            f"{self.BASE_URL}/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html",
            f"{self.BASE_URL}/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
            f"{self.BASE_URL}/cheatsheets/Insecure_Deserialization_Cheat_Sheet.html",
            f"{self.BASE_URL}/cheatsheets/Input_Validation_Cheat_Sheet.html",
            f"{self.BASE_URL}/cheatsheets/Cross_Site_Request_Forgery_Prevention_Cheat_Sheet.html",
            f"{self.BASE_URL}/cheatsheets/Authentication_Cheat_Sheet.html",
            f"{self.BASE_URL}/cheatsheets/Session_Management_Cheat_Sheet.html",
            f"{self.BASE_URL}/cheatsheets/Password_Storage_Cheat_Sheet.html",
        ]
    
    def _fetch_cheatsheet(self, url: str) -> Optional[SourceResult]:
        """Fetcha una singola cheat sheet"""
        try:
            response = self.session.get(url, timeout=30)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Estrai contenuto principale
            main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content')
            if not main_content:
                return None
            
            # Estrai titolo
            title_elem = soup.find('h1') or soup.find('title')
            title = title_elem.get_text(strip=True) if title_elem else url.split('/')[-1].replace('.html', '')
            
            # Estrai testo
            text = main_content.get_text(separator='\n', strip=True)
            
            # Estrai sezioni
            sections = self._extract_sections(main_content)
            
            # Estrai esempi di codice
            code_examples = self._extract_code_examples(main_content)
            
            # Costruisci contenuto
            content = f"""
# {title}

## Overview
{text[:500]}

## Sections

{chr(10).join(f"### {sec['title']}\n{sec['content'][:300]}" for sec in sections[:5])}

## Code Examples

{chr(10).join(f"- `{code}`" for code in code_examples[:10]) if code_examples else "No code examples"}
"""
            
            # Estrai categoria dal titolo/URL
            category = self._extract_category(title, url)
            
            return SourceResult(
                title=title,
                content=content.strip(),
                source_type='cheat_sheet',
                source_name='owasp_cheatsheets',
                url=url,
                metadata={
                    'category': category,
                    'section_count': len(sections),
                    'code_example_count': len(code_examples),
                    'source': 'owasp'
                },
                timestamp=datetime.now(),
                relevance_score=0.95
            )
            
        except Exception as e:
            print(f"[OWASP Cheat Sheets] Errore fetch sheet {url}: {e}")
            return None
    
    def _extract_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """Estrae sezioni da una cheat sheet"""
        sections = []
        
        headers = soup.find_all(['h2', 'h3', 'h4'])
        for header in headers:
            title = header.get_text(strip=True)
            # Ottieni contenuto fino al prossimo header
            content_parts = []
            next_elem = header.next_sibling
            while next_elem and next_elem.name not in ['h2', 'h3', 'h4']:
                if hasattr(next_elem, 'get_text'):
                    text = next_elem.get_text(strip=True)
                    if text:
                        content_parts.append(text)
                next_elem = next_elem.next_sibling
            
            if content_parts:
                sections.append({
                    'title': title,
                    'content': ' '.join(content_parts)
                })
        
        return sections[:10]
    
    def _extract_code_examples(self, soup: BeautifulSoup) -> List[str]:
        """Estrae esempi di codice"""
        code_examples = []
        
        code_blocks = soup.find_all(['code', 'pre'])
        for block in code_blocks:
            code = block.get_text(strip=True)
            if code and len(code) > 10:
                code_examples.append(code[:200])
        
        return list(set(code_examples))[:20]
    
    def _extract_category(self, title: str, url: str) -> str:
        """Estrae categoria dalla cheat sheet"""
        title_lower = title.lower()
        url_lower = url.lower()
        
        if 'xss' in title_lower or 'cross-site' in title_lower:
            return 'xss'
        if 'sql' in title_lower or 'injection' in title_lower:
            return 'sql_injection'
        if 'csrf' in title_lower or 'request forgery' in title_lower:
            return 'csrf'
        if 'authentication' in title_lower or 'auth' in title_lower:
            return 'authentication'
        if 'session' in title_lower:
            return 'session_management'
        if 'deserialization' in title_lower:
            return 'deserialization'
        
        return 'general'
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'cheat_sheet',
            'url': self.BASE_URL,
            'description': 'OWASP Cheat Sheet Series - Security best practices',
            'rate_limit': 'Respect robots.txt (0.5s delay)',
            'requires_auth': False
        }


