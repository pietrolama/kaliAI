#!/usr/bin/env python3
"""
IoT Credentials Harvester - Scarica e indicizza default credentials per IoT.
Fonte: SecLists (Daniel Miessler)
"""

import os
import sys
import requests
import logging
from pathlib import Path

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from knowledge.knowledge_enhancer import knowledge_enhancer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('IoTHarvester')

# URL Raw di SecLists (file consolidati)
SOURCES = [
    {
        "name": "SecLists Top Defaults",
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Default-Credentials/default-passwords.csv",
        "format": "csv_colon" # format user:pass
    },
    {
        "name": "Scada Default Creds",
        "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Default-Credentials/scada-passwords.csv",
        "format": "csv_colon"
    }
]

def harvest_iot_creds():
    count = 0
    
    for source in SOURCES:
        logger.info(f"Scaricamento {source['name']}...")
        try:
            response = requests.get(source['url'])
            if response.status_code != 200:
                logger.error(f"Errore download {source['url']}")
                continue
                
            lines = response.text.splitlines()
            
            # Raggruppa in documenti per evitare 1 doc per 1 password (troppo overhead)
            # Creiamo documenti per "Vendor" o gruppi di 50
            
            current_batch = []
            batch_size = 50
            
            for line in lines:
                line = line.strip()
                if not line or line.startswith('#'): continue
                
                # Pulisci e formatta
                # SecLists CSV format varia, assumiamo tentativi di estrazione intelligente
                parts = line.replace('"', '').replace(',', ':').split(':')
                if len(parts) >= 2:
                    cred = f"User: {parts[0]} | Pass: {parts[1]}"
                    if len(parts) > 2:
                        cred += f" | Info: {' '.join(parts[2:])}"
                    current_batch.append(cred)
                
                if len(current_batch) >= batch_size:
                    doc_text = f"""
TYPE: IoT/Device Default Credentials
SOURCE: {source['name']}

CREDENTIALS LIST:
{chr(10).join(current_batch)}
"""
                    knowledge_enhancer.kb_collection.add(
                        documents=[doc_text],
                        metadatas=[{'type': 'iot_creds', 'source': source['name']}],
                        ids=[f"iot_creds_{count}"]
                    )
                    count += 1
                    current_batch = []
            
            # Ultimo batch
            if current_batch:
                doc_text = f"""
TYPE: IoT/Device Default Credentials
SOURCE: {source['name']}

CREDENTIALS LIST:
{chr(10).join(current_batch)}
"""
                knowledge_enhancer.kb_collection.add(
                    documents=[doc_text],
                    metadatas=[{'type': 'iot_creds', 'source': source['name']}],
                    ids=[f"iot_creds_{count}"]
                )
                count += 1
                
        except Exception as e:
            logger.error(f"Errore processando {source['name']}: {e}")

    print(f"✅ IoT Credentials Harvest completato. Indicizzati {count} blocchi di credenziali.")
    
    print("⏳ Aggiornamento indice di ricerca ibrida...")
    knowledge_enhancer.rebuild_search_index()

if __name__ == "__main__":
    harvest_iot_creds()

