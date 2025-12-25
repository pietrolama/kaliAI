import chromadb
import uuid
import os
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Path configuration (ex config.CHROMA_DB_PATH)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_CHROMA_DB_PATH = os.path.join(PROJECT_ROOT, 'chroma_db')

logger = logging.getLogger('MemoryManager')


class MemoryManager:
    """Gestione memoria vettoriale migliorata con ranking intelligente."""
    
    def __init__(self, chroma_db_path: Optional[str] = None):
        """
        Args:
            chroma_db_path: Path database ChromaDB (default da config)
        """
        self.chroma_db_path = chroma_db_path or DEFAULT_CHROMA_DB_PATH
        self.client = chromadb.PersistentClient(path=self.chroma_db_path)
        
        # Collection per LTM
        self.collection = self.client.get_or_create_collection(
            name="long_term_memory",
            metadata={"hnsw:space": "cosine"}
        )
        
        logger.info(f"MemoryManager inizializzato con {self.collection.count()} memorie")
    
    def add_memory(
        self, 
        content: str, 
        metadata: Optional[Dict] = None, 
        importance: float = 1.0
    ) -> str:
        """
        Aggiunge memoria con punteggio di importanza.
        
        Args:
            content: Contenuto della memoria
            metadata: Metadati aggiuntivi
            importance: Punteggio importanza (0.0-10.0, default 1.0)
            
        Returns:
            ID della memoria creata
        """
        if not content or len(content.strip()) == 0:
            logger.warning("Tentativo di salvare memoria vuota")
            return ""
        
        # Prepara metadata
        enhanced_metadata = metadata.copy() if metadata else {}
        enhanced_metadata["importance"] = min(max(importance, 0.0), 10.0)  # Clamp 0-10
        enhanced_metadata["timestamp"] = datetime.now().isoformat()
        enhanced_metadata["length"] = len(content)
        
        # Genera ID
        memory_id = f"mem_{uuid.uuid4()}"
        
        # Salva
        try:
            self.collection.add(
                documents=[content],
                metadatas=[enhanced_metadata],
                ids=[memory_id]
            )
            logger.info(f"Memoria salvata: {memory_id} (importance={importance:.2f})")
            return memory_id
            
        except Exception as e:
            logger.error(f"Errore salvataggio memoria: {e}")
            return ""
    
    def smart_recall(
        self, 
        query: str, 
        top_k: int = 3,
        min_importance: float = 0.0,
        recency_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Recall intelligente che considera importanza, recentezza e rilevanza.
        
        Args:
            query: Query di ricerca
            top_k: Numero risultati
            min_importance: Importanza minima richiesta
            recency_weight: Peso recentezza nel ranking (0.0-1.0)
            
        Returns:
            Lista memorie rankate
        """
        if not query or len(query.strip()) == 0:
            return []
        
        try:
            # Query con più risultati per filtrare e rankare
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k * 3  # Prendiamo 3x per avere margine
            )
            
            if not results or not results.get('documents'):
                return []
            
            # Rank risultati
            ranked = self._rank_memories(
                results, 
                query,
                min_importance,
                recency_weight
            )
            
            # Ritorna top_k
            return ranked[:top_k]
            
        except Exception as e:
            logger.error(f"Errore recall memoria: {e}")
            return []
    
    def _rank_memories(
        self, 
        results: Dict, 
        query: str,
        min_importance: float,
        recency_weight: float
    ) -> List[Dict[str, Any]]:
        """Ranka memorie per importanza, recentezza e rilevanza."""
        memories = []
        
        docs = results.get('documents', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]
        distances = results.get('distances', [[]])[0]
        ids = results.get('ids', [[]])[0]
        
        for doc, meta, distance, memory_id in zip(docs, metadatas, distances, ids):
            # Filtra per importanza minima
            importance = meta.get('importance', 1.0)
            if importance < min_importance:
                continue
            
            # Calcola score combinato
            # 1. Relevance score (da distance, inverso)
            relevance_score = 1.0 - min(distance, 1.0)
            
            # 2. Importance score (normalizzato 0-1)
            importance_score = importance / 10.0
            
            # 3. Recency score
            recency_score = self._calculate_recency_score(meta.get('timestamp'))
            
            # Score finale (weighted average)
            final_score = (
                relevance_score * (1.0 - recency_weight) +
                importance_score * 0.3 +
                recency_score * recency_weight
            )
            
            memories.append({
                "id": memory_id,
                "doc": doc,
                "meta": meta,
                "score": final_score,
                "relevance": relevance_score,
                "importance": importance_score,
                "recency": recency_score
            })
        
        # Ordina per score
        memories.sort(key=lambda x: x['score'], reverse=True)
        
        return memories
    
    def _calculate_recency_score(self, timestamp_str: Optional[str]) -> float:
        """
        Calcola score di recentezza (1.0 = oggi, decay esponenziale).
        
        Args:
            timestamp_str: Timestamp ISO format
            
        Returns:
            Score 0.0-1.0
        """
        if not timestamp_str:
            return 0.0
        
        try:
            timestamp = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            age_seconds = (now - timestamp).total_seconds()
            
            # Decay esponenziale: half-life di 7 giorni
            half_life_seconds = 7 * 24 * 3600
            score = 0.5 ** (age_seconds / half_life_seconds)
            
            return min(max(score, 0.0), 1.0)
            
        except Exception as e:
            logger.warning(f"Errore calcolo recency: {e}")
            return 0.0
    
    def delete_memory(self, memory_id: str) -> bool:
        """Elimina memoria per ID."""
        try:
            self.collection.delete(ids=[memory_id])
            logger.info(f"Memoria eliminata: {memory_id}")
            return True
        except Exception as e:
            logger.error(f"Errore eliminazione memoria {memory_id}: {e}")
            return False
    
    def get_all_memories(self, limit: Optional[int] = None) -> List[Dict]:
        """Ritorna tutte le memorie (opzionalmente limitato)."""
        try:
            results = self.collection.get(include=["documents", "metadatas"])
            
            docs = results.get('documents', [])
            metas = results.get('metadatas', [])
            ids = results.get('ids', [])
            
            memories = []
            for doc, meta, memory_id in zip(docs, metas, ids):
                memories.append({
                    "id": memory_id,
                    "text": doc,
                    "metadata": meta
                })
            
            # Ordina per timestamp (più recenti prima)
            memories.sort(
                key=lambda x: x['metadata'].get('timestamp', ''), 
                reverse=True
            )
            
            if limit:
                memories = memories[:limit]
            
            return memories
            
        except Exception as e:
            logger.error(f"Errore recupero memorie: {e}")
            return []
    
    def search_by_metadata(
        self, 
        metadata_filter: Dict[str, Any], 
        limit: int = 10
    ) -> List[Dict]:
        """
        Cerca memorie per metadata.
        
        Args:
            metadata_filter: Filtro metadata (es: {"type": "step_execution"})
            limit: Numero massimo risultati
            
        Returns:
            Lista memorie che matchano il filtro
        """
        try:
            # ChromaDB where filter
            results = self.collection.get(
                where=metadata_filter,
                limit=limit,
                include=["documents", "metadatas"]
            )
            
            memories = []
            for doc, meta, memory_id in zip(
                results.get('documents', []),
                results.get('metadatas', []),
                results.get('ids', [])
            ):
                memories.append({
                    "id": memory_id,
                    "text": doc,
                    "metadata": meta
                })
            
            return memories
            
        except Exception as e:
            logger.error(f"Errore ricerca metadata: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Ritorna statistiche memoria."""
        try:
            total_count = self.collection.count()
            
            # Analizza metadata
            all_memories = self.get_all_memories()
            
            importance_scores = [
                m['metadata'].get('importance', 0) 
                for m in all_memories
            ]
            
            avg_importance = (
                sum(importance_scores) / len(importance_scores)
                if importance_scores else 0
            )
            
            # Count per tipo
            type_counts = {}
            for m in all_memories:
                mem_type = m['metadata'].get('type', 'unknown')
                type_counts[mem_type] = type_counts.get(mem_type, 0) + 1
            
            return {
                "total_memories": total_count,
                "avg_importance": f"{avg_importance:.2f}",
                "types": type_counts,
                "collection_name": self.collection.name
            }
            
        except Exception as e:
            logger.error(f"Errore statistiche memoria: {e}")
            return {"error": str(e)}
    
    def cleanup_old_memories(self, days: int = 30, keep_important: bool = True):
        """
        Elimina memorie vecchie.
        
        Args:
            days: Memorie più vecchie di N giorni
            keep_important: Se True, mantiene memorie con importance > 5
        """
        try:
            cutoff = datetime.now().timestamp() - (days * 24 * 3600)
            
            all_memories = self.get_all_memories()
            deleted_count = 0
            
            for memory in all_memories:
                timestamp_str = memory['metadata'].get('timestamp')
                importance = memory['metadata'].get('importance', 0)
                
                if not timestamp_str:
                    continue
                
                timestamp = datetime.fromisoformat(timestamp_str).timestamp()
                
                # Skip se importante e keep_important=True
                if keep_important and importance > 5.0:
                    continue
                
                # Elimina se vecchia
                if timestamp < cutoff:
                    self.delete_memory(memory['id'])
                    deleted_count += 1
            
            logger.info(f"Cleanup completato: {deleted_count} memorie eliminate")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Errore cleanup memorie: {e}")
            return 0


# Istanza globale
memory_manager = MemoryManager()

