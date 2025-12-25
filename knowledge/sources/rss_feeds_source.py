#!/usr/bin/env python3
"""
RSS Feeds Source - Integrazione multipli feed RSS di sicurezza
"""
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from .base import DataSource, SourceResult

class RSSFeedsSource(DataSource):
    """Source per multipli feed RSS di sicurezza"""
    
    FEEDS = {
        'hacker_news': {
            'url': 'https://feeds.feedburner.com/TheHackerNews',
            'name': 'The Hacker News'
        },
        'bleeping_computer': {
            'url': 'https://www.bleepingcomputer.com/feed/',
            'name': 'Bleeping Computer'
        },
        'krebs': {
            'url': 'http://krebsonsecurity.com/feed/',
            'name': 'Krebs on Security'
        },
        'threatpost': {
            'url': 'https://threatpost.com/feed/',
            'name': 'Threatpost'
        },
        'security_week': {
            'url': 'https://www.securityweek.com/feed',
            'name': 'Security Week'
        }
    }
    
    def __init__(self, enabled: bool = True):
        super().__init__('rss_feeds', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-RSS/1.0'
        })
    
    def fetch(self, days: int = 7, max_items_per_feed: int = 20) -> List[SourceResult]:
        """
        Fetcha articoli da multipli feed RSS.
        
        Args:
            days: Numero di giorni da cercare
            max_items_per_feed: Numero massimo di articoli per feed
        """
        if not self.enabled:
            return []
        
        results = []
        
        try:
            import feedparser
            
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for feed_id, feed_info in self.FEEDS.items():
                try:
                    print(f"[RSS Feeds] Fetching {feed_info['name']}...")
                    feed_results = self._fetch_feed(
                        feed_id,
                        feed_info,
                        cutoff_date,
                        max_items_per_feed
                    )
                    results.extend(feed_results)
                except Exception as e:
                    print(f"[RSS Feeds] Errore da {feed_info['name']}: {e}")
                    continue
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            print(f"[RSS Feeds] ✅ Processati {len(results)} articoli")
            
        except ImportError:
            print(f"[RSS Feeds] ⚠️ feedparser non installato. Installa con: pip install feedparser")
            self.error_count += 1
        except Exception as e:
            self.error_count += 1
            print(f"[RSS Feeds] Errore fetch: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def _fetch_feed(self, feed_id: str, feed_info: Dict, cutoff_date: datetime, max_items: int) -> List[SourceResult]:
        """Fetcha un singolo feed RSS"""
        results = []
        
        try:
            import feedparser
            
            feed = feedparser.parse(feed_info['url'])
            
            if feed.bozo:
                print(f"[RSS Feeds] ⚠️ Feed {feed_info['name']} ha errori di parsing")
                return results
            
            for entry in feed.entries[:max_items]:
                try:
                    # Estrai data
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6])
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6])
                    
                    if pub_date and pub_date < cutoff_date:
                        continue
                    
                    title = entry.get('title', 'No title')
                    summary = entry.get('summary', entry.get('description', ''))
                    link = entry.get('link', '')
                    
                    # Estrai CVE se presenti
                    cves = []
                    if 'CVE-' in title or 'CVE-' in summary:
                        import re
                        cves = re.findall(r'CVE-\d{4}-\d+', title + ' ' + summary)
                    
                    # Costruisci contenuto
                    content = f"""
Security News: {title}

SOURCE: {feed_info['name']}
PUBLISHED: {pub_date.isoformat() if pub_date else 'Unknown'}

SUMMARY:
{summary[:1000]}

{'CVEs MENTIONED: ' + ', '.join(set(cves)) if cves else ''}

LINK: {link}
"""
                    
                    relevance = 0.9 if cves else 0.75
                    
                    results.append(SourceResult(
                        title=title,
                        content=content.strip(),
                        source_type='news',
                        source_name='rss_feeds',
                        url=link,
                        metadata={
                            'feed': feed_id,
                            'feed_name': feed_info['name'],
                            'cves': list(set(cves)),
                            'published': pub_date.isoformat() if pub_date else None
                        },
                        timestamp=pub_date or datetime.now(),
                        relevance_score=relevance
                    ))
                    
                except Exception as e:
                    print(f"[RSS Feeds] Errore processando entry: {e}")
                    continue
        
        except Exception as e:
            print(f"[RSS Feeds] Errore fetch feed {feed_info['name']}: {e}")
        
        return results
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'rss_feeds',
            'url': 'Multiple RSS feeds',
            'description': 'Security news from multiple RSS feeds',
            'rate_limit': None,
            'requires_auth': False,
            'feeds': list(self.FEEDS.keys())
        }


