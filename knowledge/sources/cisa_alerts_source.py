#!/usr/bin/env python3
"""
CISA Alerts Source - Integrazione CISA Security Alerts
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime, timedelta
from .base import DataSource, SourceResult

class CISAAlertsSource(DataSource):
    """Source per CISA Security Alerts"""
    
    BASE_URL = 'https://www.cisa.gov'
    ALERTS_URL = 'https://www.cisa.gov/news-events/cybersecurity-advisories'
    RSS_URL = 'https://www.cisa.gov/news-events/cybersecurity-advisories/rss.xml'
    
    def __init__(self, enabled: bool = True):
        super().__init__('cisa_alerts', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-CISA/1.0'
        })
    
    def fetch(self, days: int = 30, max_items: int = 20) -> List[SourceResult]:
        """
        Fetcha security alerts da CISA.
        
        Args:
            days: Numero di giorni da cercare
            max_items: Numero massimo di alert
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            import feedparser
            
            feed = feedparser.parse(self.RSS_URL)
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for entry in feed.entries[:max_items]:
                # Estrai data
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6])
                
                if pub_date and pub_date < cutoff_date:
                    continue
                
                title = entry.get('title', 'No title')
                summary = entry.get('summary', '')
                link = entry.get('link', '')
                
                # Estrai CVE se presenti
                cves = []
                if 'CVE-' in title or 'CVE-' in summary:
                    import re
                    cves = re.findall(r'CVE-\d{4}-\d+', title + ' ' + summary)
                
                content = f"""
CISA Security Alert: {title}

SUMMARY:
{summary[:500]}

CVEs: {', '.join(set(cves)) if cves else 'None'}

LINK: {link}
"""
                
                relevance = 0.95 if cves else 0.8
                
                results.append(SourceResult(
                    title=title,
                    content=content.strip(),
                    source_type='security_alert',
                    source_name='cisa_alerts',
                    url=link,
                    metadata={
                        'cves': list(set(cves)),
                        'published': pub_date.isoformat() if pub_date else None
                    },
                    timestamp=pub_date or datetime.now(),
                    relevance_score=relevance
                ))
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            
        except Exception as e:
            self.error_count += 1
            print(f"[CISA Alerts] Errore fetch: {e}")
        
        return results
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'security_alert',
            'url': self.ALERTS_URL,
            'description': 'CISA Cybersecurity Advisories',
            'rate_limit': 'None',
            'requires_auth': False
        }

