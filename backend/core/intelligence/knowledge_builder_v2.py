import logging
import json
import os
import requests
from typing import List, Dict

logger = logging.getLogger('TheScholar')

class KnowledgeBuilder:
    """
    Il 'Bibliotecario' (The Scholar).
    Popola il RAG con dati verificati da fonti ufficiali (CISA, Vulners).
    Evita allucinazioni basandosi su CVE reali.
    """
    def __init__(self):
        self.cisa_kev_url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
        self.data_path = "data/knowledge/verified_feeds"
        os.makedirs(self.data_path, exist_ok=True)

    def update_cisa_kev(self) -> int:
        """Scarica l'ultimo feed CISA Known Exploited Vulnerabilities."""
        try:
            logger.info("Scaricamento CISA KEV feed...")
            resp = requests.get(self.cisa_kev_url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                filepath = os.path.join(self.data_path, "cisa_kev.json")
                with open(filepath, "w") as f:
                    json.dump(data, f, indent=2)
                
                count = len(data.get('vulnerabilities', []))
                logger.info(f"CISA KEV aggiornato: {count} vulnerabilità a catalogo.")
                return count
            else:
                logger.error(f"Errore download CISA: {resp.status_code}")
                return 0
        except Exception as e:
            logger.error(f"Eccezione CISA update: {e}")
            return 0

    def query_local_intel(self, product: str, version: str) -> List[Dict]:
        """
        Cerca nella knowledge base locale se esistono CVE note per prodotto/versione.
        Logica: String matching semplice sul catalogo CISA (o Vulners cache).
        """
        # Load CISA KEV
        filepath = os.path.join(self.data_path, "cisa_kev.json")
        hits = []
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                data = json.load(f)
                for vul in data.get('vulnerabilities', []):
                    # Match molto grezzo per ora
                    if product.lower() in vul.get('product', '').lower():
                         hits.append({
                             "cve": vul.get('cveID'),
                             "name": vul.get('vulnerabilityName'),
                             "description": vul.get('shortDescription'),
                             "source": "CISA_KEV"
                         })
        return hits

# Singleton
_scholar = KnowledgeBuilder()
def get_scholar():
    return _scholar
