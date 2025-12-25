#!/usr/bin/env python3
"""
OWASP Data Source - Integrazione OWASP Top 10 e altre risorse
"""
import requests
from typing import List, Dict
from datetime import datetime
from .base import DataSource, SourceResult

class OWASPSource(DataSource):
    """Source per OWASP Top 10 e risorse OWASP"""
    
    OWASP_URLS = {
        'top10': 'https://owasp.org/www-project-top-ten/',
        'api_security': 'https://owasp.org/www-project-api-security/',
        'mobile': 'https://owasp.org/www-project-mobile-top-10/',
        'iot': 'https://owasp.org/www-project-internet-of-things/',
    }
    
    def __init__(self, enabled: bool = True):
        super().__init__('owasp', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-OWASP-Source/1.0'
        })
    
    def fetch(self, include_top10: bool = True, include_iot: bool = True) -> List[SourceResult]:
        """Fetcha risorse OWASP"""
        if not self.enabled:
            return []
        
        results = []
        
        try:
            # OWASP Top 10
            if include_top10:
                top10_results = self._fetch_top10()
                results.extend(top10_results)
            
            # OWASP IoT
            if include_iot:
                iot_results = self._fetch_iot_top10()
                results.extend(iot_results)
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            
        except Exception as e:
            self.error_count += 1
            print(f"[OWASP] Errore fetch: {e}")
        
        return results
    
    def _fetch_top10(self) -> List[SourceResult]:
        """Fetcha OWASP Top 10"""
        results = []
        
        # OWASP Top 10 2021
        top10_items = [
            {
                'id': 'A01',
                'title': 'A01:2021 – Broken Access Control',
                'description': 'Access control enforces policy such that users cannot act outside of their intended permissions.'
            },
            {
                'id': 'A02',
                'title': 'A02:2021 – Cryptographic Failures',
                'description': 'Previously known as "Sensitive Data Exposure". Focuses on failures related to cryptography.'
            },
            {
                'id': 'A03',
                'title': 'A03:2021 – Injection',
                'description': 'SQL, NoSQL, OS command, LDAP injection vulnerabilities occur when untrusted data is sent to an interpreter.'
            },
            {
                'id': 'A04',
                'title': 'A04:2021 – Insecure Design',
                'description': 'Focuses on risks related to design and architectural flaws.'
            },
            {
                'id': 'A05',
                'title': 'A05:2021 – Security Misconfiguration',
                'description': 'Security misconfiguration is the most commonly seen issue.'
            },
            {
                'id': 'A06',
                'title': 'A06:2021 – Vulnerable and Outdated Components',
                'description': 'Using components with known vulnerabilities.'
            },
            {
                'id': 'A07',
                'title': 'A07:2021 – Identification and Authentication Failures',
                'description': 'Previously "Broken Authentication". Focuses on authentication weaknesses.'
            },
            {
                'id': 'A08',
                'title': 'A08:2021 – Software and Data Integrity Failures',
                'description': 'Focuses on software updates, critical data, and CI/CD pipelines without integrity verification.'
            },
            {
                'id': 'A09',
                'title': 'A09:2021 – Security Logging and Monitoring Failures',
                'description': 'Insufficient logging and monitoring, plus ineffective integration with incident response.'
            },
            {
                'id': 'A10',
                'title': 'A10:2021 – Server-Side Request Forgery (SSRF)',
                'description': 'SSRF flaws occur when a web application fetches a remote resource without validating the user-supplied URL.'
            },
        ]
        
        for item in top10_items:
            content = f"""
OWASP Top 10 2021 - {item['id']}

{item['title']}

DESCRIPTION:
{item['description']}

MITIGATION:
- Implement proper access control checks
- Use parameterized queries to prevent injection
- Keep dependencies updated
- Implement security logging and monitoring
"""
            
            results.append(SourceResult(
                title=item['title'],
                content=content.strip(),
                source_type='vulnerability_category',
                source_name='owasp',
                url=self.OWASP_URLS['top10'],
                metadata={'owasp_id': item['id'], 'category': 'top10_2021'},
                timestamp=datetime.now(),
                relevance_score=0.9
            ))
        
        return results
    
    def _fetch_iot_top10(self) -> List[SourceResult]:
        """Fetcha OWASP IoT Top 10"""
        results = []
        
        iot_items = [
            {
                'id': 'I01',
                'title': 'I01:2024 – Weak, Guessable, or Hardcoded Passwords',
                'description': 'Use of easily bruteforced, publicly available, or unchangeable credentials.'
            },
            {
                'id': 'I02',
                'title': 'I02:2024 – Insecure Network Services',
                'description': 'Unneeded or insecure network services running on the device itself.'
            },
            {
                'id': 'I03',
                'title': 'I03:2024 – Insecure Ecosystem Interfaces',
                'description': 'Insecure web, backend API, cloud, or mobile interfaces in the ecosystem.'
            },
        ]
        
        for item in iot_items:
            content = f"""
OWASP IoT Top 10 2024 - {item['id']}

{item['title']}

DESCRIPTION:
{item['description']}

MITIGATION:
- Use strong, unique passwords
- Disable unnecessary network services
- Secure all ecosystem interfaces
"""
            
            results.append(SourceResult(
                title=item['title'],
                content=content.strip(),
                source_type='iot_vulnerability',
                source_name='owasp',
                url=self.OWASP_URLS['iot'],
                metadata={'owasp_id': item['id'], 'category': 'iot_top10_2024'},
                timestamp=datetime.now(),
                relevance_score=0.85
            ))
        
        return results
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'curated',
            'url': 'https://owasp.org',
            'description': 'OWASP Top 10 and security resources',
            'rate_limit': None,
            'requires_auth': False
        }

