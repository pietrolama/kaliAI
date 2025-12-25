#!/usr/bin/env python3
"""
GitHub Knowledge Harvester - Scarica e indicizza repository chiave per l'hacking.
Target: HackTricks, PayloadsAllTheThings, GTFOBins, etc.
"""

import os
import sys
import logging
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict

# Setup path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
TEMP_DIR = PROJECT_ROOT / "data" / "temp_repos"

from knowledge.knowledge_enhancer import knowledge_enhancer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('GitHubHarvester')

# Repository ad alto valore
TARGET_REPOS = [
    {
        "name": "GTFOBins",
        "url": "https://github.com/GTFOBins/GTFOBins.github.io.git",
        "path_filter": "_gtfobins", # Cartella specifica
        "type": "privesc_unix"
    },
    {
        "name": "LOLBAS",
        "url": "https://github.com/LOLBAS-Project/LOLBAS.git",
        "path_filter": "yml", 
        "type": "privesc_windows"
    },
    {
        "name": "PayloadsAllTheThings",
        "url": "https://github.com/swisskyrepo/PayloadsAllTheThings.git",
        "path_filter": "", # Tutto
        "type": "cheatsheet"
    }
    # HackTricks è troppo grande da clonare tutto in una volta spesso (book), 
    # meglio gestirlo separatamente o solo sezioni specifiche.
]

def clone_repo(repo_url: str, target_dir: Path):
    if target_dir.exists():
        logger.info(f"Aggiornamento repo {target_dir.name}...")
        subprocess.run(["git", "-C", str(target_dir), "pull"], check=False)
    else:
        logger.info(f"Clonazione repo {target_dir.name}...")
        subprocess.run(["git", "clone", "--depth", "1", repo_url, str(target_dir)], check=True)

def process_gtfobins(repo_dir: Path):
    """Processa file YAML/MD di GTFOBins"""
    bins_dir = repo_dir / "_gtfobins"
    count = 0
    if not bins_dir.exists(): return 0
    
    for file_path in bins_dir.glob("*.md"):
        try:
            content = file_path.read_text(errors='ignore')
            binary_name = file_path.stem
            
            doc_text = f"""
TOOL: {binary_name} (GTFOBins)
TYPE: Unix Privilege Escalation
SOURCE: GTFOBins

CONTENT:
{content}
"""
            knowledge_enhancer.kb_collection.add(
                documents=[doc_text],
                metadatas=[{'type': 'gtfobins', 'binary': binary_name}],
                ids=[f"gtfobins_{binary_name}"]
            )
            count += 1
        except Exception as e:
            logger.error(f"Err {file_path}: {e}")
            
    return count

def process_lolbas(repo_dir: Path):
    """Processa file YAML di LOLBAS"""
    count = 0
    for file_path in repo_dir.rglob("*.yml"):
        try:
            content = file_path.read_text(errors='ignore')
            binary_name = file_path.stem
            
            doc_text = f"""
TOOL: {binary_name} (LOLBAS)
TYPE: Windows Privilege Escalation
SOURCE: LOLBAS

CONTENT:
{content}
"""
            knowledge_enhancer.kb_collection.add(
                documents=[doc_text],
                metadatas=[{'type': 'lolbas', 'binary': binary_name}],
                ids=[f"lolbas_{binary_name}"]
            )
            count += 1
        except Exception:
            pass
    return count

def process_generic_markdown(repo_dir: Path, source_name: str):
    """Processa file Markdown generici"""
    count = 0
    for file_path in repo_dir.rglob("*.md"):
        if ".github" in str(file_path) or "README" in file_path.name: continue
        
        try:
            content = file_path.read_text(errors='ignore')
            if len(content) < 100: continue
            
            # Chunking semplice per file grandi
            chunks = knowledge_enhancer._chunk_text(content, chunk_size=1500)
            
            for i, chunk in enumerate(chunks):
                doc_id = f"{source_name}_{file_path.stem}_{i}"
                doc_text = f"""
SOURCE: {source_name}
FILE: {file_path.relative_to(repo_dir)}

{chunk}
"""
                knowledge_enhancer.kb_collection.add(
                    documents=[doc_text],
                    metadatas=[{'type': 'cheatsheet', 'source': source_name, 'file': file_path.name}],
                    ids=[doc_id]
                )
                count += 1
        except Exception:
            pass
    return count

def harvest_github():
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    total_indexed = 0
    
    for repo in TARGET_REPOS:
        repo_dir = TEMP_DIR / repo["name"]
        try:
            clone_repo(repo["url"], repo_dir)
            
            logger.info(f"Indicizzazione {repo['name']}...")
            if repo["name"] == "GTFOBins":
                n = process_gtfobins(repo_dir)
            elif repo["name"] == "LOLBAS":
                n = process_lolbas(repo_dir)
            else:
                n = process_generic_markdown(repo_dir, repo["name"])
                
            logger.info(f"Indicizzati {n} documenti da {repo['name']}")
            total_indexed += n
            
        except Exception as e:
            logger.error(f"Errore processando {repo['name']}: {e}")
            
    print(f"✅ Harvest completato. Totale documenti: {total_indexed}")
    
    # Cleanup opzionale (commentato per evitare riscaricamenti continui)
    # shutil.rmtree(TEMP_DIR)
    
    print("⏳ Aggiornamento indice di ricerca ibrida...")
    knowledge_enhancer.rebuild_search_index()

if __name__ == "__main__":
    harvest_github()

