#!/usr/bin/env python3
"""
Metasploit Harvester - Indicizza i moduli locali di Metasploit nel Knowledge System.
Legge direttamente i file .rb per velocità e indipendenza dal servizio MSF.
"""

import os
import re
import logging
import sys
from pathlib import Path
from typing import Dict, Optional, List

# Setup path per importare knowledge
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge.knowledge_enhancer import knowledge_enhancer

# Configurazione Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MetasploitHarvester')

MSF_MODULES_PATH = "/usr/share/metasploit-framework/modules/"

class MetasploitParser:
    """Parser leggero basato su regex per estrarre info dai moduli Ruby di MSF."""
    
    def __init__(self):
        # Regex patterns ottimizzati
        self.rx_name = re.compile(r"'Name'\s*=>\s*['\"](.+?)['\"]", re.IGNORECASE)
        self.rx_desc = re.compile(r"'Description'\s*=>\s*%q\{(.+?)\}", re.DOTALL | re.IGNORECASE)
        self.rx_desc_alt = re.compile(r"'Description'\s*=>\s*['\"](.+?)['\"]", re.DOTALL | re.IGNORECASE)
        self.rx_cve = re.compile(r"'CVE',\s*'(.+?)'", re.IGNORECASE)
        self.rx_ref = re.compile(r"\['URL',\s*'(.+?)'\]", re.IGNORECASE)
        self.rx_rank = re.compile(r"'Rank'\s*=>\s*(\w+)", re.IGNORECASE)
        self.rx_platform = re.compile(r"'Platform'\s*=>\s*\['(.+?)'\]", re.IGNORECASE)

    def parse_file(self, file_path: str) -> Optional[Dict]:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Estrazione Dati
            name_match = self.rx_name.search(content)
            if not name_match: 
                return None # Se non ha un nome standard, probabilmente è un mixin o file base
            
            name = name_match.group(1)
            
            # Descrizione (gestisce formati %q{} e stringhe normali)
            desc_match = self.rx_desc.search(content)
            if desc_match:
                desc = desc_match.group(1)
            else:
                desc_match_alt = self.rx_desc_alt.search(content)
                desc = desc_match_alt.group(1) if desc_match_alt else "No description available."
            
            # Pulizia descrizione (rimuove spazi eccessivi e newline strani)
            desc = " ".join(desc.split())
            
            # Metadati
            cves = self.rx_cve.findall(content)
            urls = self.rx_ref.findall(content)
            rank_match = self.rx_rank.search(content)
            rank = rank_match.group(1) if rank_match else "Normal"
            platform_match = self.rx_platform.search(content)
            platform = platform_match.group(1) if platform_match else "Unknown"
            
            # Calcola path relativo come categoria (es. exploit/windows/smb/...)
            rel_path = os.path.relpath(file_path, MSF_MODULES_PATH)
            module_path = os.path.splitext(rel_path)[0] # Rimuove .rb
            category = module_path.split('/')[0] # exploit, auxiliary, post
            
            return {
                'title': f"Metasploit: {name}",
                'module_name': module_path, # es. exploit/windows/smb/ms17_010_eternalblue
                'description': desc,
                'cves': cves,
                'urls': urls,
                'rank': rank,
                'platform': platform,
                'category': category,
                'full_path': file_path
            }
            
        except Exception as e:
            logger.debug(f"Errore parsing {file_path}: {e}")
            return None

def harvest_metasploit():
    parser = MetasploitParser()
    logger.info(f"Inizio scansione Metasploit modules in: {MSF_MODULES_PATH}")
    
    count = 0
    errors = 0
    
    if not os.path.exists(MSF_MODULES_PATH):
        logger.error(f"Path Metasploit non trovato: {MSF_MODULES_PATH}")
        return

    for root, dirs, files in os.walk(MSF_MODULES_PATH):
        for file in files:
            if file.endswith('.rb'):
                full_path = os.path.join(root, file)
                
                module_data = parser.parse_file(full_path)
                
                if module_data:
                    try:
                        # Formattazione documento per RAG
                        doc_content = f"""
TOOL: Metasploit Framework
MODULE: {module_data['module_name']}
NAME: {module_data['title']}
CATEGORY: {module_data['category']}
PLATFORM: {module_data['platform']}
RANK: {module_data['rank']}

DESCRIPTION:
{module_data['description']}

CVES: {', '.join(module_data['cves'])}
REFERENCES:
{chr(10).join(module_data['urls'])}

USAGE:
use {module_data['module_name']}
"""
                        # Aggiunta a ChromaDB via KnowledgeEnhancer
                        # Usiamo exploits_collection o kb_collection (unificata in kb_collection)
                        knowledge_enhancer.kb_collection.add(
                            documents=[doc_content],
                            metadatas=[{
                                'type': 'metasploit_module',
                                'module': module_data['module_name'],
                                'platform': module_data['platform'],
                                'rank': module_data['rank'],
                                'cve': ','.join(module_data['cves'])[:100] # Limit length for metadata
                            }],
                            ids=[f"msf_{module_data['module_name']}"]
                        )
                        
                        count += 1
                        if count % 100 == 0:
                            print(f"Indicizzati {count} moduli...", end='\r')
                            
                    except Exception as e:
                        logger.error(f"Errore inserimento DB {module_data['module_name']}: {e}")
                        errors += 1

    print(f"\n✅ Completato! Indicizzati {count} moduli Metasploit.")
    
    # Ricostruzione indice BM25 alla fine
    print("⏳ Aggiornamento indice di ricerca ibrida...")
    knowledge_enhancer.rebuild_search_index()

if __name__ == "__main__":
    harvest_metasploit()

