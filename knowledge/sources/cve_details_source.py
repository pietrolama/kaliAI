#!/usr/bin/env python3
"""
CVE Details Source - Integrazione CVE Details API
"""
import requests
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from .base import DataSource, SourceResult

class CVEDetailsSource(DataSource):
    """Source per CVE Details (cvedetails.com)"""
    
    BASE_URL = 'https://www.cvedetails.com'
    API_BASE = 'https://www.cvedetails.com/api/v1'
    
    def __init__(self, enabled: bool = True):
        super().__init__('cve_details', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-CVEDetails/1.0'
        })
    
    def fetch(self, days: int = 7, severity: Optional[str] = None) -> List[SourceResult]:
        """
        Fetcha CVE recenti da CVE Details.
        
        Args:
            days: Numero di giorni da cercare (default 7)
            severity: Filtra per severity (critical, high, medium, low)
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # CVE Details non ha API pubblica, usiamo scraping limitato
            # Per ora ritorniamo struttura base
            # TODO: Implementare scraping o trovare API alternativa
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            
        except Exception as e:
            self.error_count += 1
            print(f"[CVE Details] Errore fetch: {e}")
        
        return results
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'cve_database',
            'url': self.BASE_URL,
            'description': 'CVE Details vulnerability database',
            'rate_limit': 'Unknown',
            'requires_auth': False,
            'note': 'API not publicly available, requires scraping'
        }

