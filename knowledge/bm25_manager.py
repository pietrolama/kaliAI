import pickle
import os
import logging
from typing import List, Dict, Any
from rank_bm25 import BM25Okapi
import re
import time

logger = logging.getLogger('BM25Manager')

class BM25Manager:
    """Gestore per l'indice di ricerca testuale (Keyword Search)"""
    
    def __init__(self, index_path: str = None):
        if index_path is None:
            # Path relativo al progetto
            base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
            index_path = os.path.join(base_path, "bm25_index.pkl")
            
        self.index_path = index_path
        self.bm25 = None
        self.documents = []      # Contenuto testuale
        self.doc_ids = []        # ID corrispondenti in ChromaDB
        self.doc_metadatas = []  # Metadata per filtro rapido
        self.last_update = 0
        
    def _tokenize(self, text: str) -> List[str]:
        """Tokenizzazione ottimizzata per termini tecnici (CVE, flag, IP)"""
        if not text:
            return []
        text = text.lower()
        # Regex che cattura:
        # - Parole alfanumeriche standard
        # - Flag tipo -sS, --script
        # - Identificatori tipo CVE-2024-1234
        # - Versioni tipo v1.2.3
        tokens = re.findall(r'\b[\w\-\.]+\b|-[a-zA-Z0-9]+', text)
        return tokens

    def build_index(self, documents: List[str], ids: List[str], metadatas: List[Dict]):
        """Costruisce indice da zero"""
        if not documents:
            logger.warning("Nessun documento per costruire indice BM25")
            return
            
        start_time = time.time()
        logger.info(f"Costruzione indice BM25 per {len(documents)} documenti...")
        
        tokenized_corpus = [self._tokenize(doc) for doc in documents]
        self.bm25 = BM25Okapi(tokenized_corpus)
        
        self.documents = documents
        self.doc_ids = ids
        self.doc_metadatas = metadatas
        self.last_update = time.time()
        
        self.save_index()
        logger.info(f"Indice BM25 costruito in {time.time() - start_time:.2f}s.")

    def save_index(self):
        """Salva indice su disco"""
        try:
            state = {
                'bm25': self.bm25,
                'documents': self.documents,
                'doc_ids': self.doc_ids,
                'doc_metadatas': self.doc_metadatas,
                'last_update': self.last_update
            }
            os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
            with open(self.index_path, 'wb') as f:
                pickle.dump(state, f)
            logger.debug(f"Indice BM25 salvato in {self.index_path}")
        except Exception as e:
            logger.error(f"Errore salvataggio indice BM25: {e}")

    def load_index(self) -> bool:
        """Carica indice da disco"""
        if not os.path.exists(self.index_path):
            return False
        try:
            with open(self.index_path, 'rb') as f:
                state = pickle.load(f)
            self.bm25 = state['bm25']
            self.documents = state['documents']
            self.doc_ids = state['doc_ids']
            self.doc_metadatas = state.get('doc_metadatas', [])
            self.last_update = state.get('last_update', 0)
            
            logger.info(f"Indice BM25 caricato: {len(self.documents)} documenti.")
            return True
        except Exception as e:
            logger.error(f"Errore caricamento indice BM25: {e}")
            return False

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Ricerca keyword pura"""
        if not self.bm25:
            return []
        
        tokenized_query = self._tokenize(query)
        if not tokenized_query:
            return []
            
        # Ottieni score
        scores = self.bm25.get_scores(tokenized_query)
        
        # Trova top_k indici
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
        
        results = []
        for idx in top_indices:
            if scores[idx] > 0: # Filtra risultati irrilevanti
                results.append({
                    'doc': self.documents[idx],
                    'id': self.doc_ids[idx],
                    'meta': self.doc_metadatas[idx] if idx < len(self.doc_metadatas) else {},
                    'score': scores[idx], # Score BM25 (non normalizzato 0-1)
                    'source': 'bm25'
                })
        
        return results

