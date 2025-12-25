#!/usr/bin/env python3
"""
Rapid7 Source - Integrazione Rapid7 Blog e Research
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict
from datetime import datetime, timedelta
from .base import DataSource, SourceResult

class Rapid7Source(DataSource):
    """Source per Rapid7 Blog e Research"""
    
    BLOG_URL = 'https://www.rapid7.com/blog'
    RSS_URL = 'https://www.rapid7.com/blog/feed'
    
    def __init__(self, enabled: bool = True):
        super().__init__('rapid7', enabled)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-Rapid7/1.0'
        })
    
    def fetch(self, days: int = 30, max_items: int = 20) -> List[SourceResult]:
        """
        Fetcha articoli da Rapid7 Blog.
        
        Args:
            days: Numero di giorni da cercare
            max_items: Numero massimo di articoli
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
                elif hasattr(entry, 'published'):
                    try:
                        pub_date = datetime.fromisoformat(entry.published.replace('Z', '+00:00'))
                    except:
                        pass
                
                if pub_date and pub_date < cutoff_date:
                    continue
                
                title = entry.get('title', 'No title')
                summary = entry.get('summary', '')
                link = entry.get('link', '')
                
                # Estrai tags/categories
                tags = []
                if hasattr(entry, 'tags'):
                    tags = [tag.get('term', '') for tag in entry.tags]
                
                content = f"""
Rapid7 Research: {title}

SUMMARY:
{summary[:500]}

TAGS: {', '.join(tags[:5]) if tags else 'None'}

LINK: {link}
"""
                
                results.append(SourceResult(
                    title=title,
                    content=content.strip(),
                    source_type='blog_article',
                    source_name='rapid7',
                    url=link,
                    metadata={
                        'tags': tags,
                        'published': pub_date.isoformat() if pub_date else None
                    },
                    timestamp=pub_date or datetime.now(),
                    relevance_score=0.75
                ))
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            
        except Exception as e:
            self.error_count += 1
            print(f"[Rapid7] Errore fetch: {e}")
        
        return results
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        return {
            'name': self.name,
            'type': 'security_blog',
            'url': self.BLOG_URL,
            'description': 'Rapid7 Security Research Blog',
            'rate_limit': 'None',
            'requires_auth': False
        }

