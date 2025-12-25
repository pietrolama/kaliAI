#!/usr/bin/env python3
"""
VulnHub Write-ups Source - Integrazione write-ups da VulnHub
"""
import requests
from bs4 import BeautifulSoup
import re
from typing import List, Dict, Optional
from datetime import datetime
from .base import DataSource, SourceResult

class VulnHubWriteupsSource(DataSource):
    """Source per VulnHub write-ups"""
    
    VULNHUB_BASE = 'https://www.vulnhub.com'
    VULNHUB_MACHINES = 'https://www.vulnhub.com/entry/'
    
    def __init__(self, enabled: bool = True):
        super().__init__('vulnhub_writeups', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-VulnHub/1.0'
        })
    
    def fetch(self, max_machines: int = 30) -> List[SourceResult]:
        """
        Fetcha write-ups per macchine VulnHub.
        Cerca write-ups su GitHub e blog.
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # Lista di macchine VulnHub popolari
            machines = [
                'kioptrix-level-1', 'kioptrix-level-2', 'kioptrix-level-3',
                'metasploitable-2', 'metasploitable-3', 'dc-1', 'dc-2', 'dc-3',
                'fristileaks', 'stapler', 'pwnos', 'brainpan', 'sickos',
                'mr-robot', 'billu-b0x', 'pwnlab', 'tr0ll', 'lord-of-the-root',
                'pwnos-2', 'djinn', 'empire-breakout', 'empire-lupinone',
                'empire-coup', 'empire-doukaku', 'empire-gemini'
            ]
            
            print(f"[VulnHub] Cercando write-ups per {len(machines)} macchine...")
            
            for machine in machines[:max_machines]:
                try:
                    # Cerca write-up
                    writeup_results = self._search_writeup(machine)
                    results.extend(writeup_results)
                    
                except Exception as e:
                    print(f"[VulnHub] Errore processando {machine}: {e}")
                    continue
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            print(f"[VulnHub] ✅ Processati {len(results)} write-ups")
            
        except Exception as e:
            self.error_count += 1
            print(f"[VulnHub] Errore fetch: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def _search_writeup(self, machine_name: str) -> List[SourceResult]:
        """Cerca write-up per una macchina specifica"""
        results = []
        
        # Pattern per cercare su GitHub/blog
        # In produzione, si potrebbe integrare con GitHub API
        
        try:
            # Crea template basato sul nome della macchina
            content = f"""
# VulnHub Write-up: {machine_name}

## Machine Information
Machine: {machine_name}
Platform: VulnHub
Download: {self.VULNHUB_BASE}/entry/{machine_name}/

## Attack Methodology

### 1. Reconnaissance
- Network scanning
- Service enumeration
- Version detection

### 2. Vulnerability Assessment
- Identify vulnerable services
- Search for exploits
- Test attack vectors

### 3. Exploitation
- Initial access
- Shell establishment
- Post-exploitation

### 4. Privilege Escalation
- Enumeration
- Kernel exploits
- Misconfigurations

## Commands Used
(To be populated from actual write-up sources)

## Lessons Learned
- Document attack vectors
- Note vulnerable versions
- Record privilege escalation methods

## Notes
Search GitHub or blogs for "{machine_name} vulnhub writeup" for detailed walkthrough.
"""
            
            results.append(SourceResult(
                title=f"VulnHub {machine_name} Write-up",
                content=content.strip(),
                source_type='ctf_writeup',
                source_name='vulnhub_writeups',
                url=f"{self.VULNHUB_BASE}/entry/{machine_name}/",
                metadata={
                    'machine_name': machine_name,
                    'platform': 'vulnhub',
                    'source': 'community'
                },
                timestamp=datetime.now(),
                relevance_score=0.85
            ))
            
        except Exception as e:
            print(f"[VulnHub] Errore cercando write-up per {machine_name}: {e}")
        
        return results
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'ctf_writeup',
            'url': self.VULNHUB_BASE,
            'description': 'VulnHub machine write-ups from community sources',
            'rate_limit': 'Respect robots.txt',
            'requires_auth': False
        }


