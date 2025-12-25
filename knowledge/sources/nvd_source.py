#!/usr/bin/env python3
"""
NVD Source - Integrazione NIST National Vulnerability Database
"""
import requests
import json
import zipfile
import io
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from .base import DataSource, SourceResult

class NVDSource(DataSource):
    """Source per NIST NVD (National Vulnerability Database)"""
    
    NVD_BASE = 'https://nvd.nist.gov'
    NVD_FEED = 'https://nvd.nist.gov/feeds/json/cve/1.1'
    
    def __init__(self, enabled: bool = True):
        super().__init__('nvd', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9'
        })
    
    def fetch(self, days: int = 7, severity: Optional[str] = None) -> List[SourceResult]:
        """
        Fetcha CVE recenti da NVD.
        
        Args:
            days: Numero di giorni da cercare
            severity: Filtra per CVSS severity (CRITICAL, HIGH, MEDIUM, LOW)
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # Download recent CVE feed
            url = f"{self.NVD_FEED}/nvdcve-1.1-recent.json.zip"
            
            response = self.session.get(url, timeout=60)
            response.raise_for_status()
            
            # Estrai ZIP
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                json_file = z.namelist()[0]
                data = json.loads(z.read(json_file))
            
            # Processa CVE
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for cve_item in data.get('CVE_Items', []):
                cve_id = cve_item.get('cve', {}).get('CVE_data_meta', {}).get('ID', '')
                published = cve_item.get('publishedDate', '')
                
                # Filtra per data
                if published:
                    pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
                    if pub_date < cutoff_date:
                        continue
                
                # Estrai descrizione
                descriptions = cve_item.get('cve', {}).get('description', {}).get('description_data', [])
                description = descriptions[0].get('value', 'No description') if descriptions else 'No description'
                
                # Estrai CVSS
                cvss = cve_item.get('impact', {}).get('baseMetricV3', {})
                if not cvss:
                    cvss = cve_item.get('impact', {}).get('baseMetricV2', {})
                
                severity = cvss.get('cvssV3', {}).get('baseSeverity', '') if 'cvssV3' in str(cvss) else cvss.get('severity', '')
                score = cvss.get('cvssV3', {}).get('baseScore', 0) if 'cvssV3' in str(cvss) else cvss.get('baseScore', 0)
                
                # Filtra per severity se richiesto
                if severity and severity.upper() != severity.upper():
                    continue
                
                content = f"""
CVE: {cve_id}
Published: {published}
Severity: {severity}
CVSS Score: {score}

DESCRIPTION:
{description}

REFERENCES:
"""
                # Aggiungi references
                references = cve_item.get('cve', {}).get('references', {}).get('reference_data', [])
                for ref in references[:5]:  # Max 5 references
                    content += f"- {ref.get('url', '')}\n"
                
                relevance = 0.9 if severity in ['CRITICAL', 'HIGH'] else 0.7
                
                results.append(SourceResult(
                    title=f"{cve_id} - {severity}",
                    content=content.strip(),
                    source_type='cve',
                    source_name='nvd',
                    url=f"{self.NVD_BASE}/vuln/detail/{cve_id}",
                    metadata={
                        'cve_id': cve_id,
                        'severity': severity,
                        'cvss_score': score,
                        'published': published
                    },
                    timestamp=datetime.fromisoformat(published.replace('Z', '+00:00')) if published else datetime.now(),
                    relevance_score=relevance
                ))
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            
        except Exception as e:
            self.error_count += 1
            print(f"[NVD] Errore fetch: {e}")
        
        return results
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'cve_database',
            'url': self.NVD_BASE,
            'description': 'NIST National Vulnerability Database',
            'rate_limit': 'None (public feed)',
            'requires_auth': False
        }

