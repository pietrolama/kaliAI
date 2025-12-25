#!/usr/bin/env python3
"""
GitHub Security Advisories Source - Integrazione GitHub Security Advisories API
"""
import requests
import os
from typing import List, Dict
from datetime import datetime, timedelta
from .base import DataSource, SourceResult

class GitHubAdvisoriesSource(DataSource):
    """Source per GitHub Security Advisories"""
    
    API_BASE = 'https://api.github.com'
    ADVISORIES_ENDPOINT = '/advisories'
    
    def __init__(self, enabled: bool = True):
        super().__init__('github_advisories', enabled)
        self.session = requests.Session()
        self.token = os.getenv('GITHUB_TOKEN')
        
        headers = {
            'User-Agent': 'KaliAI-GitHub-Advisories/1.0',
            'Accept': 'application/vnd.github+json'
        }
        
        if self.token:
            headers['Authorization'] = f'token {self.token}'
        
        self.session.headers.update(headers)
    
    def fetch(self, days: int = 7, severity: str = None) -> List[SourceResult]:
        """
        Fetcha security advisories da GitHub.
        
        Args:
            days: Numero di giorni da cercare
            severity: Filtra per severity (critical, high, moderate, low)
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            from datetime import timezone
            
            url = f"{self.API_BASE}{self.ADVISORIES_ENDPOINT}"
            params = {
                'per_page': 100,
                'sort': 'updated',
                'direction': 'desc'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            
            if response.status_code == 401:
                print("[GitHub Advisories] ⚠️  Token mancante o invalido. Usa GITHUB_TOKEN env var per rate limit più alto")
                return []
            
            response.raise_for_status()
            data = response.json()
            
            # Crea cutoff_date come aware
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            for advisory in data:
                # Filtra per data
                updated = advisory.get('updated_at', '')
                updated_date = None
                if updated:
                    try:
                        # Gestisci sia datetime aware che naive
                        if updated.endswith('Z'):
                            updated_date = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                        else:
                            updated_date = datetime.fromisoformat(updated)
                        
                        # Se è naive, rendilo aware
                        if updated_date.tzinfo is None:
                            from datetime import timezone
                            updated_date = updated_date.replace(tzinfo=timezone.utc)
                        
                        # Confronta con cutoff_date (rendilo aware se necessario)
                        if cutoff_date.tzinfo is None:
                            from datetime import timezone
                            cutoff_date = cutoff_date.replace(tzinfo=timezone.utc)
                        
                        if updated_date < cutoff_date:
                            continue
                    except Exception as e:
                        print(f"[GitHub Advisories] Errore parsing data: {e}")
                        continue
                
                # Filtra per severity
                if severity:
                    adv_severity = advisory.get('severity', '').lower()
                    if adv_severity != severity.lower():
                        continue
                
                ghsa_id = advisory.get('ghsa_id', '')
                summary = advisory.get('summary', 'No summary')
                description = advisory.get('description', '')
                cve_ids = advisory.get('cves', [])
                severity_adv = advisory.get('severity', 'UNKNOWN')
                
                content = f"""
GitHub Security Advisory: {ghsa_id}
Severity: {severity_adv}
Updated: {updated}

SUMMARY:
{summary}

DESCRIPTION:
{description[:500]}

CVEs:
{', '.join([cve.get('cve_id', '') for cve in cve_ids]) if cve_ids else 'None'}
"""
                
                relevance = 0.9 if severity_adv in ['CRITICAL', 'HIGH'] else 0.7
                
                results.append(SourceResult(
                    title=f"{ghsa_id} - {severity_adv}",
                    content=content.strip(),
                    source_type='security_advisory',
                    source_name='github_advisories',
                    url=advisory.get('html_url', ''),
                    metadata={
                        'ghsa_id': ghsa_id,
                        'severity': severity_adv,
                        'cves': [cve.get('cve_id', '') for cve in cve_ids],
                        'updated': updated
                    },
                    timestamp=updated_date if updated else datetime.now(),
                    relevance_score=relevance
                ))
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            
        except Exception as e:
            self.error_count += 1
            print(f"[GitHub Advisories] Errore fetch: {e}")
        
        return results
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'security_advisory',
            'url': 'https://github.com/advisories',
            'description': 'GitHub Security Advisories',
            'rate_limit': '5000/hour (con token), 60/hour (senza)',
            'requires_auth': False,
            'recommended_auth': True
        }

