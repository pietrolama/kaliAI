#!/usr/bin/env python3
"""
Embedding Manager - Gestione centralizzata degli embeddings
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Optional, Callable

logger = logging.getLogger('EmbeddingManager')

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    logger.warning("sentence-transformers non installato, usa: pip install sentence-transformers")

try:
    from langchain_community.embeddings import HuggingFaceEmbeddings
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False


class EmbeddingManager:
    """Manager centralizzato per embeddings"""
    
    _instance = None
    _model = None
    _model_name = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._model is None:
            self._load_model()
    
    def _load_model(self):
        """Carica modello embeddings dalla configurazione"""
        config_path = Path(__file__).parent / 'rag_config.json'
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            model_name = config.get('embeddings', {}).get('model', 'BAAI/bge-small-en-v1.5')
            self._model_name = model_name
            
            logger.info(f"Caricamento modello embeddings: {model_name}")
            
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                # Usa SentenceTransformer (più efficiente)
                self._model = SentenceTransformer(model_name)
                logger.info(f"✅ Modello caricato: {model_name}")
            elif LANGCHAIN_AVAILABLE:
                # Fallback a LangChain
                self._model = HuggingFaceEmbeddings(model_name=model_name)
                logger.warning(f"Usando LangChain (meno efficiente): {model_name}")
            else:
                logger.error("Nessuna libreria embeddings disponibile!")
                self._model = None
                
        except Exception as e:
            logger.error(f"Errore caricamento modello: {e}")
            # Fallback a modello default
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                self._model = SentenceTransformer('all-MiniLM-L6-v2')
                self._model_name = 'all-MiniLM-L6-v2'
                logger.warning("Usando modello fallback: all-MiniLM-L6-v2")
            else:
                self._model = None
    
    def encode(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """
        Genera embeddings per una lista di testi
        
        Args:
            texts: Lista di testi da codificare
            normalize: Normalizza embeddings (raccomandato per bge models)
        
        Returns:
            Lista di embeddings (ogni embedding è una lista di float)
        """
        if self._model is None:
            raise RuntimeError("Modello embeddings non disponibile")
        
        if isinstance(self._model, SentenceTransformer):
            # SentenceTransformer
            embeddings = self._model.encode(
                texts,
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            return embeddings.tolist()
        else:
            # LangChain HuggingFaceEmbeddings
            embeddings = self._model.embed_documents(texts)
            return embeddings
    
    def encode_query(self, query: str, normalize: bool = True) -> List[float]:
        """
        Genera embedding per una query (ottimizzato per ricerca)
        
        Args:
            query: Testo della query
            normalize: Normalizza embedding
        
        Returns:
            Embedding come lista di float
        """
        if self._model is None:
            raise RuntimeError("Modello embeddings non disponibile")
        
        if isinstance(self._model, SentenceTransformer):
            # Per bge models, aggiungi instruction per query
            if 'bge' in self._model_name.lower():
                query_text = f"Represent this sentence for searching relevant passages: {query}"
            else:
                query_text = query
            
            embedding = self._model.encode(
                query_text,
                normalize_embeddings=normalize,
                show_progress_bar=False
            )
            return embedding.tolist()
        else:
            # LangChain
            embedding = self._model.embed_query(query)
            return embedding
    
    def get_model_name(self) -> str:
        """Restituisce nome modello corrente"""
        return self._model_name or 'unknown'
    
    def get_dimensions(self) -> int:
        """Restituisce dimensione embeddings"""
        if self._model is None:
            return 384  # Default
        
        if isinstance(self._model, SentenceTransformer):
            return self._model.get_sentence_embedding_dimension()
        else:
            # LangChain - prova a inferire
            test_emb = self.encode(['test'])
            return len(test_emb[0]) if test_emb else 384


# Singleton instance
_embedding_manager = None

def get_embedding_manager() -> EmbeddingManager:
    """Ottiene istanza singleton di EmbeddingManager"""
    global _embedding_manager
    if _embedding_manager is None:
        _embedding_manager = EmbeddingManager()
    return _embedding_manager

