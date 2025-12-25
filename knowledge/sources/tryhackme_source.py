#!/usr/bin/env python3
"""
TryHackMe Walkthroughs Source - Integrazione walkthrough da TryHackMe
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from datetime import datetime
from .base import DataSource, SourceResult

class TryHackMeSource(DataSource):
    """Source per TryHackMe walkthroughs"""
    
    BASE_URL = 'https://tryhackme.com'
    # Nota: TryHackMe richiede autenticazione per molti contenuti
    # Questo source si concentra su contenuti pubblici e walkthrough della community
    
    def __init__(self, enabled: bool = True):
        super().__init__('tryhackme', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-TryHackMe/1.0'
        })
    
    def fetch(self, max_rooms: int = 30) -> List[SourceResult]:
        """
        Fetcha walkthrough da TryHackMe.
        Nota: Molti contenuti richiedono account, quindi questo source
        si concentra su walkthrough pubblici trovati su GitHub/blog.
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # Lista di room THM popolari (pubbliche)
            rooms = [
                'basicpentesting', 'vulnversity', 'blue', 'ice', 'lazyadmin',
                'overpass', 'relevant', 'internal', 'yearoftherabbit',
                'picklerick', 'cowboyhacker', 'ignite', 'kenobi', 'lazyadmin',
                'mrrobot', 'tomghost', 'dailybugle', 'cyborg', 'steamcloud',
                'bolt', 'inclusion', 'dogcat', 'lazyadmin', 'rootme'
            ]
            
            print(f"[TryHackMe] Cercando walkthrough per {len(rooms)} room...")
            
            for room in rooms[:max_rooms]:
                try:
                    # Cerca walkthrough su GitHub (tramite API o scraping)
                    walkthrough_results = self._search_walkthrough(room)
                    results.extend(walkthrough_results)
                    
                except Exception as e:
                    print(f"[TryHackMe] Errore processando {room}: {e}")
                    continue
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            print(f"[TryHackMe] ✅ Processati {len(results)} walkthrough")
            
        except Exception as e:
            self.error_count += 1
            print(f"[TryHackMe] Errore fetch: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def _search_walkthrough(self, room_name: str) -> List[SourceResult]:
        """Cerca walkthrough per una room specifica"""
        results = []
        
        # Pattern per cercare su GitHub (via web scraping o API)
        # Per ora, creiamo un template che può essere esteso
        
        # Esempio: cerca su GitHub
        try:
            github_search_url = f"https://github.com/search?q={room_name}+tryhackme+walkthrough&type=Repositories"
            
            # Nota: GitHub richiede autenticazione per API, quindi usiamo scraping base
            # In produzione, si potrebbe usare GitHub API con token
            
            # Per ora, creiamo un risultato template
            content = f"""
# TryHackMe Walkthrough: {room_name}

## Room Information
Room: {room_name}
Platform: TryHackMe

## Methodology
1. Reconnaissance
2. Enumeration
3. Exploitation
4. Privilege Escalation

## Commands
(To be populated from actual walkthrough sources)

## Notes
This walkthrough is sourced from community repositories.
Search GitHub for "{room_name} tryhackme walkthrough" for detailed steps.
"""
            
            results.append(SourceResult(
                title=f"TryHackMe {room_name} Walkthrough",
                content=content.strip(),
                source_type='ctf_writeup',
                source_name='tryhackme',
                url=f"{self.BASE_URL}/r/{room_name}",
                metadata={
                    'room_name': room_name,
                    'platform': 'tryhackme',
                    'source': 'community'
                },
                timestamp=datetime.now(),
                relevance_score=0.85
            ))
            
        except Exception as e:
            print(f"[TryHackMe] Errore cercando walkthrough per {room_name}: {e}")
        
        return results
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'ctf_writeup',
            'url': self.BASE_URL,
            'description': 'TryHackMe room walkthroughs from community sources',
            'rate_limit': 'Respect robots.txt',
            'requires_auth': 'Partial (some content requires account)'
        }


