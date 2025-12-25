#!/usr/bin/env python3
"""
RAG Manager - Gestione unificata RAG con sistema modulare
"""
import os
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path

from .knowledge_enhancer import KnowledgeEnhancer
from .sources import registry

logger = logging.getLogger('RAGManager')

class RAGManager:
    """Manager unificato per RAG con sistema modulare"""
    
    def __init__(self, config_path: str = None):
        # Carica embedding manager
        try:
            from .embedding_manager import get_embedding_manager
            self.embedding_manager = get_embedding_manager()
            logger.info(f"EmbeddingManager caricato: {self.embedding_manager.get_model_name()}")
        except ImportError:
            self.embedding_manager = None
            logger.warning("EmbeddingManager non disponibile")
        
        self.enhancer = KnowledgeEnhancer()
        self.config_path = config_path or Path(__file__).parent / 'rag_config.json'
        self.config = self._load_config()
        self._apply_config()
    
    def _load_config(self) -> Dict:
        """Carica configurazione"""
        if not self.config_path.exists():
            logger.warning(f"Config file not found: {self.config_path}")
            return {}
        
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return {}
    
    def _apply_config(self):
        """Applica configurazione ai sources"""
        sources_config = self.config.get('sources', {})
        
        for source_name, config in sources_config.items():
            source = registry.get(source_name)
            if source:
                source.enabled = config.get('enabled', True)
    
    def fetch_all_sources(self, force: bool = False) -> Dict:
        """
        Fetcha dati da tutti i sources abilitati.
        
        Returns:
            Dict con statistiche per source
        """
        stats = {}
        enabled_sources = registry.list_enabled()
        
        logger.info(f"Fetching from {len(enabled_sources)} enabled sources...")
        
        for source_name in enabled_sources:
            source = registry.get(source_name)
            if not source:
                continue
            
            try:
                # Ottieni parametri dal config
                source_config = self.config.get('sources', {}).get(source_name, {})
                params = source_config.get('params', {})
                
                # Fetch
                results = source.fetch(**params)
                
                # Aggiungi a ChromaDB
                collection_name = self._get_collection_for_source(source_name, source_config)
                
                # Check if generator
                import inspect
                is_generator = inspect.isgenerator(results)
                
                if is_generator:
                    added = self._add_generator_to_collection(results, collection_name)
                    fetched_count = added  # Assume all valid
                else:
                    added = self._add_results_to_collection(results, collection_name)
                    fetched_count = len(results)
                
                stats[source_name] = {
                    'fetched': fetched_count,
                    'added': added,
                    'status': 'success'
                }
                
                logger.info(f"✅ {source_name}: {fetched_count} fetched, {added} added")
                
            except Exception as e:
                stats[source_name] = {
                    'fetched': 0,
                    'added': 0,
                    'status': 'error',
                    'error': str(e)
                }
                logger.error(f"❌ {source_name}: {e}")
        
        return stats
    
    def _get_collection_for_source(self, source_name: str, config: Dict) -> str:
        """Determina collection per source"""
        collection_map = {
            'cve': 'cve_database',
            'exploits': 'exploits_db',
            'kb': 'kali_linux_kb',
            'tools': 'tool_manuals',
            'successes': 'successful_attacks'
        }
        
        collection_type = config.get('collection', 'kb')
        return collection_map.get(collection_type, 'kali_linux_kb')
    
    def _add_generator_to_collection(self, results_generator, collection_name: str, batch_size: int = 50) -> int:
        """Aggiunge risultati da un generatore in batch"""
        added = 0
        batch = []
        
        for result in results_generator:
            if result:
                batch.append(result)
                
            if len(batch) >= batch_size:
                added += self._add_results_to_collection(batch, collection_name)
                batch = []
                
                # GC opzionale
                import gc
                if added % 1000 == 0:
                    gc.collect()
        
        # Processa rimanenti
        if batch:
            added += self._add_results_to_collection(batch, collection_name)
            
        return added

    def _add_results_to_collection(self, results: List, collection_name: str, use_batch: bool = True) -> int:
        """Aggiunge risultati a ChromaDB collection"""
        if not results:
            return 0
        
        try:
            collection = getattr(self.enhancer, {
                'cve_database': 'cve_collection',
                'exploits_db': 'exploits_collection',
                'kali_linux_kb': 'kb_collection',
                'tool_manuals': 'tools_collection',
                'successful_attacks': 'success_collection'
            }.get(collection_name, 'kb_collection'))
            
            # Ottimizzazione: usa batch add per velocità
            if use_batch and len(results) > 10:
                return self._add_batch_to_collection(collection, results, collection_name)
            
            # Fallback: add uno per uno
            added = 0
            for result in results:
                doc_data = result.to_document()
                
                # ChromaDB non accetta liste nei metadata - converti in stringhe
                metadata = doc_data['metadata'].copy()
                for key, value in metadata.items():
                    if isinstance(value, list):
                        metadata[key] = ', '.join(str(v) for v in value) if value else ''
                    elif value is None:
                        metadata[key] = ''
                    elif not isinstance(value, (str, int, float, bool)):
                        metadata[key] = str(value)
                
                collection.add(
                    documents=[doc_data['document']],
                    metadatas=[metadata],
                    ids=[f"{result.source_name}_{result.timestamp.timestamp() if result.timestamp else added}"]
                )
                added += 1
            
            return added
            
        except Exception as e:
            logger.error(f"Error adding to collection {collection_name}: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def _add_batch_to_collection(self, collection, results: List, collection_name: str) -> int:
        """Aggiunge risultati in batch per velocità"""
        BATCH_LIMIT = 1000
        total_added = 0
        
        # Split results into smaller chunks
        for i in range(0, len(results), BATCH_LIMIT):
            chunk = results[i:i+BATCH_LIMIT]
            try:
                # Prepara batch
                documents = []
                metadatas = []
                ids = []
                embeddings = []  # Per embeddings pre-calcolati
                
                for j, result in enumerate(chunk):
                    doc_data = result.to_document()
                    
                    # Metadata cleanup
                    metadata = doc_data['metadata'].copy()
                    for key, value in metadata.items():
                        if isinstance(value, list):
                            metadata[key] = ', '.join(str(v) for v in value) if value else ''
                        elif value is None:
                            # ChromaDB non accetta None nei metadata
                            metadata[key] = ''
                        elif not isinstance(value, (str, int, float, bool)):
                            metadata[key] = str(value)
                    
                    documents.append(doc_data['document'])
                    metadatas.append(metadata)
                    
                    # ID unico
                    import uuid
                    doc_id = metadata.get('original_id')
                    if not doc_id:
                        # Usa hash del contenuto o UUID per garantire unicità
                        import hashlib
                        content_hash = hashlib.md5(doc_data['document'].encode('utf-8', 'ignore')).hexdigest()[:10]
                        doc_id = f"{result.source_name}_{result.timestamp.timestamp() if result.timestamp else (i+j)}_{content_hash}_{uuid.uuid4().hex[:6]}"
                    
                    ids.append(doc_id)
                    
                    # Embedding pre-calcolato (se disponibile da knowledge_export)
                    if hasattr(result, 'metadata') and result.metadata.get('has_embedding'):
                        # Prova a ottenere embedding dal source
                        if hasattr(result, 'source_name') and result.source_name == 'knowledge_export':
                            from knowledge.sources import registry
                            export_source = registry.get('knowledge_export')
                            if export_source and hasattr(export_source, 'get_embedding'):
                                embedding = export_source.get_embedding(doc_id)
                                if embedding:
                                    embeddings.append(embedding)
                                    continue
                    
                    # Nessun embedding pre-calcolato
                    embeddings.append(None)
                
                # Aggiungi batch (ChromaDB calcolerà embeddings se None)
                if any(emb is not None for emb in embeddings):
                    # TODO: Gestire embeddings custom se necessario
                    collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    total_added += len(documents)
                else:
                    # Batch add normale (più veloce)
                    collection.add(
                        documents=documents,
                        metadatas=metadatas,
                        ids=ids
                    )
                    total_added += len(documents)
                
            except Exception as e:
                logger.error(f"Error adding chunk {i}-{i+len(chunk)}: {e}")
                import traceback
                traceback.print_exc()
                # Fallback per questo chunk: prova ad aggiungere uno per uno
                total_added += self._add_results_to_collection(chunk, collection_name, use_batch=False)

        return total_added
    
    def enhanced_search(self, query: str, top_k: int = None, 
                       source_filter: Optional[List[str]] = None) -> List[Dict]:
        """
        Ricerca migliorata con weighting e filtering.
        
        Args:
            query: Query di ricerca
            top_k: Numero risultati (usa default da config se None)
            source_filter: Filtra per source specifici
        
        Returns:
            Lista risultati ordinati per rilevanza
        """
        if top_k is None:
            top_k = self.config.get('search', {}).get('default_top_k', 5)
        
        # Usa enhanced_search esistente
        results = self.enhancer.enhanced_search(query, top_k=top_k * 2)  # Prendi più risultati per filtering
        
        # Applica weighting da config
        weights = self.config.get('search', {}).get('collection_weights', {})
        weighted_results = []
        
        for res in results:
            source = res.get('source', 'kb')
            weight = weights.get(source, 1.0)
            
            # Applica weight alla distance (riduce distance = aumenta relevance)
            adjusted_distance = res.get('distance', 1.0) / weight
            
            weighted_results.append({
                **res,
                'distance': adjusted_distance,
                'original_distance': res.get('distance', 1.0),
                'weight': weight
            })
        
        # Filtra per source se richiesto
        if source_filter:
            weighted_results = [r for r in weighted_results if r.get('source') in source_filter]
        
        # Filtra per min relevance
        min_relevance = self.config.get('search', {}).get('min_relevance_score', 0.3)
        weighted_results = [
            r for r in weighted_results 
            if (1.0 - r.get('distance', 1.0)) >= min_relevance
        ]
        
        # Riordina per distance pesata
        weighted_results.sort(key=lambda x: x.get('distance', 1.0))
        
        return weighted_results[:top_k]
    
    def get_stats(self) -> Dict:
        """Statistiche complete RAG"""
        enhancer_stats = self.enhancer.get_stats()
        source_stats = registry.get_stats()
        
        return {
            'collections': enhancer_stats,
            'sources': source_stats,
            'config': {
                'enabled_sources': len(registry.list_enabled()),
                'total_sources': len(registry.list_all())
            }
        }

# Istanza globale
rag_manager = RAGManager()
