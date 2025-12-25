#!/usr/bin/env python3
"""
Knowledge Enhancer - Sistema avanzato per migliorare la knowledge base.

Funzionalità:
1. Multi-source ingestion (PDF, web scraping, API)
2. Auto-learning dai successi
3. CVE database integration
4. Exploit-DB integration
5. Tool manuals auto-indexing
6. Ricerca Ibrida (Semantica + Keyword) con RRF
"""

import os
import logging
import chromadb
import requests
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

# Configurazione Path e Import
try:
    # Tenta import relativo se eseguito come modulo
    from ..config.config import config
    DEFAULT_CHROMA_PATH = config.CHROMA_DB_PATH
except ImportError:
    try:
        # Tenta import assoluto se path è nel sys.path
        from config.config import config
        DEFAULT_CHROMA_PATH = config.CHROMA_DB_PATH
    except ImportError:
        # Fallback
        DEFAULT_CHROMA_PATH = os.path.join(os.getcwd(), "chroma_db")

# Import BM25 Manager
try:
    from .bm25_manager import BM25Manager
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

# Importa configurazione ChromaDB per disabilitare telemetria
try:
    from .chromadb_config import get_chromadb_client
    CHROMADB_CONFIG_AVAILABLE = True
except ImportError:
    CHROMADB_CONFIG_AVAILABLE = False

logger = logging.getLogger('KnowledgeEnhancer')

# Import embedding manager
try:
    from .embedding_manager import get_embedding_manager
    EMBEDDING_MANAGER_AVAILABLE = True
except ImportError:
    EMBEDDING_MANAGER_AVAILABLE = False
    logger.warning("EmbeddingManager non disponibile, usa ChromaDB default")

# ChromaDB EmbeddingFunction wrapper
try:
    import chromadb.utils.embedding_functions as embedding_functions
    CHROMADB_EF_AVAILABLE = True
except ImportError:
    CHROMADB_EF_AVAILABLE = False

class CustomEmbeddingFunction:
    """Wrapper per embedding function custom compatibile con ChromaDB"""
    def __init__(self, embedding_manager):
        self.embedding_manager = embedding_manager
        self._name = f"custom_{embedding_manager.get_model_name().replace('/', '_')}"
    
    def __call__(self, input):
        """Chiamata da ChromaDB"""
        if isinstance(input, str):
            input = [input]
        return self.embedding_manager.encode(input, normalize=True)
    
    def name(self):
        """Nome embedding function per ChromaDB"""
        return self._name


class KnowledgeEnhancer:
    """Migliora e arricchisce la knowledge base."""
    
    def __init__(self, chroma_db_path: str = None):
        if chroma_db_path is None:
            chroma_db_path = DEFAULT_CHROMA_PATH
            
        self.chroma_db_path = chroma_db_path
        
        # Crea directory se non esiste
        if not os.path.exists(self.chroma_db_path):
            try:
                os.makedirs(self.chroma_db_path, exist_ok=True)
            except Exception as e:
                logger.warning(f"Impossibile creare directory {self.chroma_db_path}: {e}")

        # Disabilita telemetria ChromaDB
        os.environ.setdefault("ANONYMIZED_TELEMETRY", "False")
        
        # Sopprimi warning
        import warnings
        warnings.filterwarnings("ignore", message=".*telemetry.*")
        
        logger.info(f"Inizializzazione ChromaDB in: {self.chroma_db_path}")
        
        # Usa configurazione centralizzata se disponibile
        if CHROMADB_CONFIG_AVAILABLE:
            self.client = get_chromadb_client(chroma_db_path)
        else:
            # Fallback: usa Settings per disabilitare telemetria
            try:
                from chromadb.config import Settings
                settings = Settings(anonymized_telemetry=False)
                self.client = chromadb.PersistentClient(path=chroma_db_path, settings=settings)
            except:
                self.client = chromadb.PersistentClient(path=chroma_db_path)
        
        # Carica embedding manager per query (non cambia embedding function esistenti)
        self.embedding_manager = None
        if EMBEDDING_MANAGER_AVAILABLE:
            try:
                self.embedding_manager = get_embedding_manager()
                model_name = self.embedding_manager.get_model_name()
                logger.info(f"EmbeddingManager disponibile per query: {model_name}")
            except Exception as e:
                logger.warning(f"Errore caricamento EmbeddingManager: {e}")
        
        # Collections specializzate
        # Collection principale unificata (contiene tutti i documenti da knowledge_export.json)
        self.kb_collection = self.client.get_or_create_collection("kali_linux_kb")
        self.exploits_collection = self.client.get_or_create_collection("exploits_db")
        self.cve_collection = self.client.get_or_create_collection("cve_database")
        self.success_collection = self.client.get_or_create_collection("successful_attacks")
        self.tools_collection = self.client.get_or_create_collection("tool_manuals")

        # Inizializza BM25 Manager
        self.bm25_manager = None
        if BM25_AVAILABLE:
            self.bm25_manager = BM25Manager()
            if self.bm25_manager.load_index():
                logger.info("Indice BM25 caricato correttamente.")
            else:
                logger.info("Indice BM25 non trovato o vuoto, sarà necessario ricostruirlo.")
    
    def rebuild_search_index(self):
        """Ricostruisce l'indice di ricerca testuale (BM25) da tutte le collections"""
        if not self.bm25_manager:
            logger.warning("BM25Manager non disponibile.")
            return

        logger.info("Avvio ricostruzione indice di ricerca ibrida...")
        
        all_docs = []
        all_ids = []
        all_metas = []
        
        # Raccolta da tutte le collections
        collections = [
            self.kb_collection,
            self.exploits_collection,
            self.cve_collection,
            self.success_collection,
            self.tools_collection
        ]
        
        for col in collections:
            try:
                # Get all docs
                data = col.get()
                if data and data['documents']:
                    all_docs.extend(data['documents'])
                    all_ids.extend(data['ids'])
                    
                    # Gestione metadati (possono essere None)
                    metas = data.get('metadatas')
                    if not metas:
                        metas = [{}] * len(data['documents'])
                    
                    # Arricchisci metadata con nome collection
                    for m in metas:
                        if m is None: m = {}
                        if not isinstance(m, dict): m = {} # Safety check
                        m['_source_collection'] = col.name
                    
                    all_metas.extend(metas)
            except Exception as e:
                logger.error(f"Errore lettura collection {col.name}: {e}")

        # Build index
        if all_docs:
            self.bm25_manager.build_index(all_docs, all_ids, all_metas)
            logger.info(f"Indice ibrido ricostruito: {len(all_docs)} documenti totali.")
        else:
            logger.warning("Nessun documento trovato per costruire l'indice.")

    def add_exploit_knowledge(self, exploit_data: Dict):
        """
        Aggiunge exploit al database.
        """
        doc_text = f"""
EXPLOIT: {exploit_data.get('title', 'Unknown')}
CVE: {exploit_data.get('cve', 'N/A')}
TARGET: {exploit_data.get('target', 'Generic')}
DIFFICULTY: {exploit_data.get('difficulty', 'unknown')}

DESCRIPTION:
{exploit_data.get('description', 'No description')}

COMMANDS:
{chr(10).join(exploit_data.get('commands', []))}
"""
        
        self.exploits_collection.add(
            documents=[doc_text],
            metadatas=[{
                'type': 'exploit',
                'cve': exploit_data.get('cve', ''),
                'target': exploit_data.get('target', ''),
                'timestamp': datetime.now().isoformat()
            }],
            ids=[f"exploit_{exploit_data.get('cve', datetime.now().timestamp())}"]
        )
        
        logger.info(f"Exploit aggiunto: {exploit_data.get('title')}")

    def add_cve_info(self, cve_id: str, description: str, affected: str):
        """Aggiunge info CVE."""
        doc_text = f"""
CVE: {cve_id}
AFFECTED: {affected}

DESCRIPTION:
{description}
"""
        self.cve_collection.add(
            documents=[doc_text],
            metadatas=[{'type': 'cve', 'cve_id': cve_id, 'timestamp': datetime.now().isoformat()}],
            ids=[f"cve_{cve_id}"]
        )
        logger.info(f"CVE aggiunta: {cve_id}")
    
    def learn_from_success(self, attack_type: str, target: str, commands: List[str], result: str, 
                          target_profile: Optional[Dict] = None, step_description: str = ""):
        """Impara da un attacco riuscito."""
        if target_profile is None:
            target_profile = {}
            
        # Costruisci profilo target
        profile_text = ""
        if target_profile:
            profile_text = "PROFILO TARGET:\n"
            if target_profile.get('ports'):
                profile_text += f"- Porte aperte: {', '.join(target_profile['ports'])}\n"
            if target_profile.get('os'):
                profile_text += f"- OS: {target_profile['os']}\n"
            if target_profile.get('vendor'):
                profile_text += f"- Vendor/Brand: {target_profile['vendor']}\n"
            if target_profile.get('service'):
                profile_text += f"- Servizio: {target_profile['service']}\n"
        
        # Comando vincente principale
        winning_command = commands[0] if commands else ""
        if len(commands) > 1:
            for cmd in commands:
                if 'nc -u' in cmd or 'netcat -u' in cmd:
                    winning_command = cmd
                    break
        
        doc_text = f"""
🎯 PLAYBOOK SUCCESSO: {attack_type}

{profile_text}

COMANDO VINCENTE:
{winning_command}

TUTTI I COMANDI ESEGUITI:
{chr(10).join(f'{i+1}. {cmd}' for i, cmd in enumerate(commands))}

RISULTATO:
{result}

CONTESTO STEP:
{step_description}

LEZIONI APPRESE:
- Questo approccio funziona per dispositivi con profilo: {profile_text.strip() if profile_text else 'N/A'}
- Il comando '{winning_command.split()[0] if winning_command else 'N/A'}' è efficace per {attack_type}

RIUSO FUTURO:
Quando rilevi un dispositivo simile, usa direttamente: {winning_command}
"""
        
        metadata = {
            'type': 'success',
            'attack_type': attack_type,
            'target': target,
            'timestamp': datetime.now().isoformat(),
            'winning_command': winning_command,
        }
        
        if target_profile.get('ports'):
            metadata['ports'] = ','.join(target_profile['ports'])
        if target_profile.get('protocol'):
            metadata['protocol'] = target_profile['protocol']
        if target_profile.get('vendor'):
            metadata['vendor'] = target_profile['vendor']
        
        self.success_collection.add(
            documents=[doc_text],
            metadatas=[metadata],
            ids=[f"success_{datetime.now().timestamp()}"]
        )
        
        logger.info(f"✅ Playbook salvato: {attack_type}")

    def add_playbook_entry(self, entry_type: str, title: str, content: str, metadata: Dict):
        """
        Aggiunge una voce al playbook (successo o fallimento).
        """
        # Standardizza entry_type
        entry_type = entry_type.lower()
        if entry_type not in ['success', 'failure']:
            entry_type = 'note'
            
        doc_text = f"""
PLAYBOOK {entry_type.upper()}: {title}

{content}

TIMESTAMP: {datetime.now().isoformat()}
"""
        
        # I successi vanno nella collection prioritaria, i fallimenti nella KB generale
        if entry_type == 'success':
            collection = self.success_collection
        else:
            collection = self.kb_collection
            
        # Assicura che metadata abbia campi base
        safe_metadata = metadata.copy()
        safe_metadata['type'] = f"playbook_{entry_type}"
        safe_metadata['timestamp'] = datetime.now().isoformat()
        
        # Converti liste in stringhe per ChromaDB
        for k, v in safe_metadata.items():
            if isinstance(v, list):
                safe_metadata[k] = ','.join(str(x) for x in v)
        
        collection.add(
            documents=[doc_text],
            metadatas=[safe_metadata],
            ids=[f"playbook_{entry_type}_{datetime.now().timestamp()}"]
        )
        logger.info(f"✅ Playbook {entry_type} salvato: {title}")
    
    def index_tool_manual(self, tool_name: str):
        """
        Indicizza il manuale di un tool (man page).
        """
        try:
            import subprocess
            
            result = subprocess.run(
                f"man {tool_name}",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                manual_text = result.stdout
                chunks = self._chunk_text(manual_text, chunk_size=500)
                
                for i, chunk in enumerate(chunks):
                    self.tools_collection.add(
                        documents=[chunk],
                        metadatas=[{
                            'tool': tool_name,
                            'type': 'manual',
                            'chunk': i
                        }],
                        ids=[f"manual_{tool_name}_{i}"]
                    )
                
                logger.info(f"Manuale {tool_name} indicizzato: {len(chunks)} chunks")
                return True
            else:
                logger.warning(f"Man page per {tool_name} non trovata")
                return False
        except Exception as e:
            logger.error(f"Errore indicizzazione manuale {tool_name}: {e}")
            return False

    def _chunk_text(self, text: str, chunk_size: int = 1000) -> List[str]:
        """Divide testo in chunk."""
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + 1 > chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(word)
            current_length += len(word) + 1
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def get_stats(self) -> Dict:
        """Statistiche knowledge base."""
        return {
            'kali_kb': self.kb_collection.count(),  # Collection principale unificata
            'exploits': self.exploits_collection.count(),
            'cve': self.cve_collection.count(),
            'successes': self.success_collection.count(),
            'tools': self.tools_collection.count(),
            'total': sum([
                self.kb_collection.count(),
                self.exploits_collection.count(),
                self.cve_collection.count(),
                self.success_collection.count(),
                self.tools_collection.count()
            ])
        }
    
    def enhanced_search(self, query: str, top_k: int = 5, prioritize_successes: bool = True) -> List[Dict]:
        """
        Ricerca Ibrida (Vettoriale + Keyword) con Reciprocal Rank Fusion (RRF).
        Combina risultati semantici (ChromaDB) con keyword esatte (BM25).
        """
        # 1. RICERCA VETTORIALE (Semantic Search)
        # Raccogli risultati da tutte le collections
        vector_candidates = []
        
        collections = {
            'successes': self.success_collection,
            'kb': self.kb_collection,
            'exploits': self.exploits_collection,
            'cve': self.cve_collection,
            'tools': self.tools_collection
        }
        
        # Cerca in tutte le collections
        # Limitiamo a top_k * 2 per avere abbastanza candidati per la fusione
        search_k = top_k * 2
        
        for col_name, collection in collections.items():
            if collection is None or collection.count() == 0:
                continue
            
            try:
                # Query con n_results un po' più alto per filtrare dopo
                results = collection.query(
                    query_texts=[query],
                    n_results=search_k
                )
                
                if results and results.get('documents'):
                    # Zip inclusi gli IDs per identificazione univoca
                    for docs, metas, dists, ids in zip(
                        results['documents'],
                        results.get('metadatas', [[]]),
                        results.get('distances', [[]]),
                        results.get('ids', [[]])
                    ):
                        for doc, meta, dist, doc_id in zip(docs, metas, dists, ids):
                            vector_candidates.append({
                                'id': doc_id,
                                'doc': doc,
                                'meta': meta if meta else {},
                                'distance': dist, # 0 = identico, 1+ = diverso
                                'source': col_name
                            })
            except Exception as e:
                logger.error(f"Errore vector search in {col_name}: {e}")
        
        # Ordina candidati vettoriali per distanza (minore è meglio)
        vector_candidates.sort(key=lambda x: x['distance'])
        # Prendi i top assoluti
        vector_top = vector_candidates[:search_k]
        
        # 2. RICERCA KEYWORD (BM25)
        bm25_top = []
        if self.bm25_manager and self.bm25_manager.bm25:
            bm25_top = self.bm25_manager.search(query, top_k=search_k)
        
        # 3. RECIPROCAL RANK FUSION (RRF)
        # Score = 1 / (k + rank)
        rrf_k = 60
        doc_scores = {}
        doc_map = {} # ID -> {doc, meta, source} per ricostruire il risultato
        
        # Processa Vector Results
        for rank, res in enumerate(vector_top):
            doc_id = res['id']
            # Normalizza distance in uno score simil-rank se necessario, ma qui usiamo il rank
            score = 1 / (rrf_k + rank + 1)
            
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score
            
            # Salva info documento se prima volta
            if doc_id not in doc_map:
                doc_map[doc_id] = res
        
        # Processa BM25 Results
        for rank, res in enumerate(bm25_top):
            doc_id = res['id']
            score = 1 / (rrf_k + rank + 1)
            
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score
            
            # Se il documento è trovato solo via BM25 (non vettoriale), aggiungilo
            if doc_id not in doc_map:
                # BM25 result ha chiavi diverse, adattiamo
                # meta potrebbe non avere 'source', cerchiamo di recuperarlo o metterlo default
                source = 'bm25_match'
                # Se abbiamo i metadati originali, usiamo quelli
                if res.get('meta') and '_source_collection' in res['meta']:
                    source = res['meta']['_source_collection']
                
                doc_map[doc_id] = {
                    'id': doc_id,
                    'doc': res['doc'],
                    'meta': res['meta'],
                    'distance': 0.5, # Valore medio fittizio
                    'source': source,
                    'is_keyword_match': True # Flag per indicare match esatto
                }

        # Ordina per score RRF finale
        ranked_ids = sorted(doc_scores.keys(), key=lambda pid: doc_scores[pid], reverse=True)
        
        # Costruisci lista finale
        final_results = []
        for doc_id in ranked_ids[:top_k]:
            res = doc_map[doc_id]
            
            # Applica boost priorità successi (se richiesto)
            # Nota: RRF già li ha ordinati, ma possiamo forzare i successi in cima se sono nel set
            final_results.append(res)
            
        # Ri-applica logica di priorità successi (force to top)
        if prioritize_successes:
            successes = [r for r in final_results if r.get('source') == 'successes' or r.get('source') == 'successful_attacks']
            others = [r for r in final_results if r not in successes]
            
            if successes:
                # Metti il miglior successo in cima assoluta
                final_results = [successes[0]] + [x for x in successes[1:] + others]
                # Taglia di nuovo a top_k
                final_results = final_results[:top_k]
        
        return final_results


# Istanza globale
knowledge_enhancer = KnowledgeEnhancer()

if __name__ == "__main__":
    # Test rapido
    print("KnowledgeEnhancer inizializzato.")
    # Prova a ricostruire l'indice se vuoto
    if not knowledge_enhancer.bm25_manager or not knowledge_enhancer.bm25_manager.bm25:
        print("Ricostruzione indice BM25...")
        knowledge_enhancer.rebuild_search_index()
    
    stats = knowledge_enhancer.get_stats()
    print(f"Stats: {stats}")
