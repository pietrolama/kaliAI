#!/usr/bin/env python3
"""
CISA KEV Source - Integrazione CISA Known Exploited Vulnerabilities Catalog
"""
import requests
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .base import DataSource, SourceResult

class CISAKEVSource(DataSource):
    """Source per CISA Known Exploited Vulnerabilities"""
    
    KEV_URL = 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json'
    BASE_URL = 'https://www.cisa.gov/known-exploited-vulnerabilities-catalog'
    
    def __init__(self, enabled: bool = True):
        super().__init__('cisa_kev', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-CISA-KEV/1.0'
        })
    
    def fetch(self, update_daily: bool = True) -> List[SourceResult]:
        """
        Fetcha CISA Known Exploited Vulnerabilities.
        
        Args:
            update_daily: Se True, scarica il file JSON ogni volta
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # Scarica file JSON
            print(f"[CISA KEV] Download catalog...")
            response = self.session.get(self.KEV_URL, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            vulnerabilities = data.get('vulnerabilities', [])
            
            print(f"[CISA KEV] Trovate {len(vulnerabilities)} vulnerabilità")
            
            for vuln in vulnerabilities:
                try:
                    cve_id = vuln.get('cveID', '')
                    vendor = vuln.get('vendorProject', '')
                    product = vuln.get('product', '')
                    vulnerability_name = vuln.get('vulnerabilityName', '')
                    date_added = vuln.get('dateAdded', '')
                    short_description = vuln.get('shortDescription', '')
                    required_action = vuln.get('requiredAction', '')
                    due_date = vuln.get('dueDate', '')
                    notes = vuln.get('notes', '')
                    
                    # Costruisci contenuto
                    content = f"""
CISA Known Exploited Vulnerability: {cve_id}

VENDOR: {vendor}
PRODUCT: {product}
VULNERABILITY NAME: {vulnerability_name}

DESCRIPTION:
{short_description}

REQUIRED ACTION:
{required_action}

DATE ADDED TO CATALOG: {date_added}
DUE DATE: {due_date}

NOTES:
{notes}

⚠️ CRITICAL: This vulnerability is actively exploited in the wild according to CISA.
"""
                    
                    # Parse date per timestamp
                    timestamp = datetime.now()
                    try:
                        if date_added:
                            timestamp = datetime.strptime(date_added, '%Y-%m-%d')
                    except:
                        pass
                    
                    # Relevance molto alta (priorità massima)
                    relevance = 1.0
                    
                    results.append(SourceResult(
                        title=f"{cve_id} - {vulnerability_name}",
                        content=content.strip(),
                        source_type='cve',
                        source_name='cisa_kev',
                        url=f"{self.BASE_URL}#{cve_id}",
                        metadata={
                            'cve_id': cve_id,
                            'vendor': vendor,
                            'product': product,
                            'vulnerability_name': vulnerability_name,
                            'date_added': date_added,
                            'due_date': due_date,
                            'is_actively_exploited': True,
                            'priority': 'critical'
                        },
                        timestamp=timestamp,
                        relevance_score=relevance
                    ))
                    
                except Exception as e:
                    print(f"[CISA KEV] Errore processando vulnerabilità: {e}")
                    continue
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            print(f"[CISA KEV] ✅ Processate {len(results)} vulnerabilità")
            
        except Exception as e:
            self.error_count += 1
            print(f"[CISA KEV] Errore fetch: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'vulnerability_catalog',
            'url': self.BASE_URL,
            'description': 'CISA Known Exploited Vulnerabilities - Actively exploited CVEs',
            'rate_limit': None,
            'requires_auth': False,
            'priority': 'critical'
        }


