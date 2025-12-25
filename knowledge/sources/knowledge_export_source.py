#!/usr/bin/env python3
"""
Knowledge Export Source - Importa knowledge base da file JSON export
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from .base import DataSource, SourceResult

class KnowledgeExportSource(DataSource):
    """Source per importare knowledge base da file JSON export"""
    
    def __init__(self, json_path: str = None, enabled: bool = True):
        super().__init__('knowledge_export', enabled)
        
        # Default path: project root
        if json_path is None:
            project_root = Path(__file__).parent.parent.parent
            json_path = project_root / 'data' / 'knowledge_export.json'
        
        self.json_path = Path(json_path) if isinstance(json_path, str) else json_path
        self.embeddings_cache = {}  # Cache embeddings se necessario
    
    def fetch(self, limit: Optional[int] = None, category_filter: Optional[str] = None) -> List[SourceResult]:
        """
        Importa documenti dal file JSON export.
        
        Args:
            limit: Limita numero documenti (None = tutti)
            category_filter: Filtra per categoria (None = tutte)
        
        Returns:
            Lista di SourceResult
        """
        if not self.enabled:
            return []
        
        if not self.json_path.exists():
            print(f"[Knowledge Export] ⚠️  File non trovato: {self.json_path}")
            return []
        
        results = []
        
        try:
            print(f"[Knowledge Export] 📂 Caricamento {self.json_path}...")
            
            with open(self.json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            total_docs = data.get('total_documents', 0)
            documents = data.get('documents', [])
            export_date = data.get('export_date', '')
            
            print(f"[Knowledge Export] 📊 Trovati {total_docs} documenti")
            
            # Applica filtri
            filtered_docs = documents
            if category_filter:
                filtered_docs = [
                    doc for doc in filtered_docs 
                    if doc.get('metadata', {}).get('category') == category_filter
                ]
                print(f"[Knowledge Export] 🔍 Filtrati per categoria '{category_filter}': {len(filtered_docs)} documenti")
            
            if limit:
                filtered_docs = filtered_docs[:limit]
                print(f"[Knowledge Export] ⏹️  Limitati a {limit} documenti")
            
            # Converti in SourceResult
            for doc in filtered_docs:
                doc_id = doc.get('id', '')
                content = doc.get('content', '')
                metadata = doc.get('metadata', {})
                embedding = doc.get('embedding', [])
                
                # Estrai info da metadata
                title = metadata.get('title', doc_id[:50])
                source = metadata.get('source', 'unknown')
                category = metadata.get('category', 'general')
                url = metadata.get('url', '')
                timestamp_str = metadata.get('timestamp', export_date)
                
                # Parse timestamp
                try:
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    else:
                        timestamp = datetime.now()
                except:
                    timestamp = datetime.now()
                
                # Costruisci content completo
                full_content = f"{title}\n\n{content}"
                
                # Relevance score basato su categoria
                relevance_map = {
                    'documentation': 0.8,
                    'exploit': 0.95,
                    'cve': 0.9,
                    'tool': 0.85,
                    'tutorial': 0.75
                }
                relevance = relevance_map.get(category.lower(), 0.7)
                
                result = SourceResult(
                    title=title,
                    content=full_content,
                    source_type=category,
                    source_name='knowledge_export',
                    url=url if url else None,
                    metadata={
                        'original_id': doc_id,
                        'category': category,
                        'source': source,
                        'has_embedding': len(embedding) > 0,
                        'embedding_dim': len(embedding) if embedding else 0
                    },
                    timestamp=timestamp,
                    relevance_score=relevance
                )
                
                # Salva embedding se presente (per uso futuro)
                if embedding:
                    self.embeddings_cache[doc_id] = embedding
                
                results.append(result)
            
            self.fetch_count += 1
            self.last_fetch = datetime.now()
            
            print(f"[Knowledge Export] ✅ Importati {len(results)} documenti")
            
        except Exception as e:
            self.error_count += 1
            print(f"[Knowledge Export] ❌ Errore fetch: {e}")
            import traceback
            traceback.print_exc()
        
        return results
    
    def get_embedding(self, doc_id: str) -> Optional[List[float]]:
        """Ottiene embedding per un documento (se disponibile)"""
        return self.embeddings_cache.get(doc_id)
    
    def get_source_info(self) -> Dict:
        """Info sul source"""
        file_size = self.json_path.stat().st_size / (1024 * 1024) if self.json_path.exists() else 0
        
        return {
            'name': self.name,
            'type': 'knowledge_export',
            'url': str(self.json_path),
            'description': f'Knowledge base export da altro progetto ({file_size:.1f} MB)',
            'rate_limit': 'None (file locale)',
            'requires_auth': False,
            'file_size_mb': file_size
        }

