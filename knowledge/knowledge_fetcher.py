#!/usr/bin/env python3
"""
Knowledge Fetcher - Scarica e indicizza conoscenza da fonti esterne.

Fonti supportate:
- CVE/NVD databases
- CISA Known Exploited Vulnerabilities
- RSS feeds security
- GitHub repositories
- MITRE ATT&CK
- OWASP
"""

import os
import sys
import json
import logging
import requests
import feedparser
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
import zipfile
import io

# Aggiungi parent directory al path per import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from knowledge.knowledge_enhancer import knowledge_enhancer

logger = logging.getLogger('KnowledgeFetcher')


class KnowledgeFetcher:
    """Scarica e indicizza conoscenza da fonti esterne."""
    
    # URL fonti
    SOURCES = {
        # CVE/Vulnerability databases
        'cve_recent': 'https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.zip',
        'cisa_kev': 'https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json',
        
        # RSS Feeds
        'us_cert': 'https://www.us-cert.gov/ncas/current-activity.xml',
        'packetstorm': 'https://rss.packetstormsecurity.com/',
        'bleeping': 'https://www.bleepingcomputer.com/feed/',
        
        # Reddit
        'reddit_netsec': 'https://www.reddit.com/r/netsec/new/.rss',
        'reddit_reverseeng': 'https://www.reddit.com/r/ReverseEngineering/.rss',
        'reddit_cybersec': 'https://www.reddit.com/r/cybersecurity/.rss',
        
        # Blogs
        'krebs': 'https://krebsonsecurity.com/feed/',
        'schneier': 'https://feeds.feedburner.com/SchneierSecurity',
        
        # MITRE ATT&CK
        'mitre_attack': 'https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json'
    }
    
    def __init__(self, cache_dir: str = "data/knowledge_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'KaliAI-KnowledgeFetcher/1.0'
        })
    
    def fetch_cisa_kev(self) -> int:
        """
        Scarica CISA Known Exploited Vulnerabilities.
        
        Returns:
            Numero di CVE aggiunte
        """
        logger.info("Downloading CISA KEV catalog...")
        
        try:
            response = self.session.get(self.SOURCES['cisa_kev'], timeout=30)
            response.raise_for_status()
            
            data = response.json()
            vulnerabilities = data.get('vulnerabilities', [])
            
            logger.info(f"CISA KEV: {len(vulnerabilities)} vulnerabilità trovate")
            
            # Aggiungi solo CVE recenti (ultimi 180 giorni)
            recent_count = 0
            cutoff_date = datetime.now() - timedelta(days=180)
            
            for vuln in vulnerabilities:
                try:
                    date_added = datetime.strptime(vuln.get('dateAdded', '2000-01-01'), '%Y-%m-%d')
                    
                    if date_added >= cutoff_date:
                        knowledge_enhancer.add_cve_info(
                            cve_id=vuln.get('cveID', 'N/A'),
                            description=vuln.get('vulnerabilityName', '') + '. ' + vuln.get('shortDescription', ''),
                            affected=vuln.get('product', 'Unknown')
                        )
                        recent_count += 1
                except Exception as e:
                    logger.warning(f"Errore parsing CVE: {e}")
                    continue
            
            logger.info(f"CISA KEV: {recent_count} CVE recenti aggiunte")
            return recent_count
            
        except Exception as e:
            logger.error(f"Errore download CISA KEV: {e}")
            return 0
    
    def fetch_rss_feed(self, feed_url: str, feed_name: str, max_items: int = 20) -> int:
        """
        Scarica e indicizza feed RSS.
        
        Returns:
            Numero di item aggiunti
        """
        logger.info(f"Fetching RSS: {feed_name}...")
        
        try:
            feed = feedparser.parse(feed_url)
            
            if not feed.entries:
                logger.warning(f"Nessun entry in {feed_name}")
                return 0
            
            count = 0
            for entry in feed.entries[:max_items]:
                try:
                    title = entry.get('title', 'No title')
                    link = entry.get('link', '')
                    summary = entry.get('summary', entry.get('description', ''))
                    published = entry.get('published', datetime.now().isoformat())
                    
                    # Crea documento
                    doc_text = f"""
SOURCE: {feed_name}
TITLE: {title}
LINK: {link}
DATE: {published}

CONTENT:
{summary[:500]}
"""
                    
                    # Aggiungi a knowledge base generale
                    knowledge_enhancer.kb_collection.add(
                        documents=[doc_text],
                        metadatas=[{
                            'source': feed_name,
                            'type': 'rss',
                            'url': link,
                            'date': published
                        }],
                        ids=[f"rss_{feed_name}_{hash(link)}"]
                    )
                    
                    count += 1
                except Exception as e:
                    logger.warning(f"Errore parsing RSS entry: {e}")
                    continue
            
            logger.info(f"RSS {feed_name}: {count} items aggiunti")
            return count
            
        except Exception as e:
            logger.error(f"Errore fetch RSS {feed_name}: {e}")
            return 0
    
    def fetch_mitre_attack(self) -> int:
        """
        Scarica MITRE ATT&CK framework.
        
        Returns:
            Numero di tecniche aggiunte
        """
        logger.info("Downloading MITRE ATT&CK...")
        
        try:
            response = self.session.get(self.SOURCES['mitre_attack'], timeout=60)
            response.raise_for_status()
            
            data = response.json()
            objects = data.get('objects', [])
            
            # Filtra solo tecniche
            techniques = [obj for obj in objects if obj.get('type') == 'attack-pattern']
            
            logger.info(f"MITRE ATT&CK: {len(techniques)} tecniche trovate")
            
            count = 0
            for tech in techniques[:100]:  # Limita a 100 per non sovraccaricare
                try:
                    name = tech.get('name', 'Unknown')
                    description = tech.get('description', '')
                    tech_id = tech.get('external_references', [{}])[0].get('external_id', 'N/A')
                    
                    doc_text = f"""
MITRE ATT&CK TECHNIQUE: {name}
ID: {tech_id}

DESCRIPTION:
{description[:800]}
"""
                    
                    knowledge_enhancer.kb_collection.add(
                        documents=[doc_text],
                        metadatas=[{
                            'source': 'mitre_attack',
                            'type': 'technique',
                            'tech_id': tech_id
                        }],
                        ids=[f"mitre_{tech_id}"]
                    )
                    
                    count += 1
                except Exception as e:
                    logger.warning(f"Errore parsing technique: {e}")
                    continue
            
            logger.info(f"MITRE ATT&CK: {count} tecniche aggiunte")
            return count
            
        except Exception as e:
            logger.error(f"Errore download MITRE ATT&CK: {e}")
            return 0
    
    def fetch_all_feeds(self, max_items_per_feed: int = 10):
        """Scarica tutti i feed RSS configurati."""
        rss_feeds = {
            'US-CERT': self.SOURCES['us_cert'],
            'PacketStorm': self.SOURCES['packetstorm'],
            'BleepingComputer': self.SOURCES['bleeping'],
            'Reddit-NetSec': self.SOURCES['reddit_netsec'],
            'Reddit-ReverseEng': self.SOURCES['reddit_reverseeng'],
            'Krebs': self.SOURCES['krebs'],
            'Schneier': self.SOURCES['schneier']
        }
        
        total = 0
        for name, url in rss_feeds.items():
            count = self.fetch_rss_feed(url, name, max_items_per_feed)
            total += count
        
        return total
    
    def update_all(self, include_heavy: bool = False):
        """
        Aggiorna tutta la knowledge base.
        
        Args:
            include_heavy: Se True, include anche download pesanti (CVE completo)
        """
        logger.info("🚀 Aggiornamento knowledge base completo...")
        
        stats = {
            'cisa_kev': 0,
            'rss_feeds': 0,
            'mitre': 0
        }
        
        # 1. CISA KEV (leggero, importante)
        stats['cisa_kev'] = self.fetch_cisa_kev()
        
        # 2. Feed RSS (leggero, aggiornamenti giornalieri)
        stats['rss_feeds'] = self.fetch_all_feeds(max_items_per_feed=10)
        
        # 3. MITRE ATT&CK (medio peso, importante)
        if include_heavy:
            stats['mitre'] = self.fetch_mitre_attack()
        
        logger.info("✅ Aggiornamento completato!")
        return stats


# Istanza globale
fetcher = KnowledgeFetcher()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
    
    print("=" * 60)
    print("KNOWLEDGE FETCHER - Download Fonti Esterne")
    print("=" * 60)
    print()
    
    # Stats iniziali
    stats_before = knowledge_enhancer.get_stats()
    print("📊 Knowledge Base - Prima:")
    print(f"  Total: {stats_before['total']} documenti\n")
    
    # Download
    print("🌐 Download in corso...")
    print("  (Questo può richiedere qualche minuto)\n")
    
    include_heavy = '--full' in sys.argv
    
    update_stats = fetcher.update_all(include_heavy=include_heavy)
    
    # Stats finali
    print()
    stats_after = knowledge_enhancer.get_stats()
    print("📊 Knowledge Base - Dopo:")
    print(f"  Total: {stats_after['total']} documenti (+{stats_after['total'] - stats_before['total']})\n")
    
    print("📈 Dettagli aggiornamento:")
    for key, value in update_stats.items():
        print(f"  {key}: +{value}")
    
    print()
    print("=" * 60)
    print("✅ Knowledge base aggiornata con successo!")
    print("=" * 60)
    print("\nPer includere MITRE ATT&CK (pesante):")
    print("  python knowledge_fetcher.py --full")

