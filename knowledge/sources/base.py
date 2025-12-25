#!/usr/bin/env python3
"""
Base Data Source - Classe base per tutti i data source connectors
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

@dataclass
class SourceResult:
    """Risultato da un data source"""
    title: str
    content: str
    source_type: str  # 'cve', 'exploit', 'article', 'tool', etc.
    source_name: str  # Nome del data source
    url: Optional[str] = None
    metadata: Optional[Dict] = None
    timestamp: Optional[datetime] = None
    relevance_score: float = 1.0  # 0.0-1.0, più alto = più rilevante
    
    def to_document(self) -> Dict:
        """Converte in formato documento per ChromaDB"""
        doc_text = f"{self.title}\n\n{self.content}"
        
        meta = {
            'source': self.source_name,
            'type': self.source_type,
            'timestamp': (self.timestamp or datetime.now()).isoformat(),
            'relevance': self.relevance_score
        }
        
        if self.url:
            meta['url'] = self.url
        
        if self.metadata:
            meta.update(self.metadata)
        
        return {
            'document': doc_text,
            'metadata': meta
        }

class DataSource(ABC):
    """Classe base astratta per tutti i data source connectors"""
    
    def __init__(self, name: str, enabled: bool = True):
        self.name = name
        self.enabled = enabled
        self.last_fetch: Optional[datetime] = None
        self.fetch_count = 0
        self.error_count = 0
    
    @abstractmethod
    def fetch(self, **kwargs) -> List[SourceResult]:
        """
        Fetcha dati dal source.
        
        Returns:
            Lista di SourceResult
        """
        pass
    
    @abstractmethod
    def get_source_info(self) -> Dict:
        """
        Ritorna informazioni sul source.
        
        Returns:
            Dict con info (url, description, rate_limit, etc.)
        """
        pass
    
    def validate(self) -> bool:
        """
        Valida se il source è accessibile.
        
        Returns:
            True se accessibile, False altrimenti
        """
        try:
            info = self.get_source_info()
            return info is not None
        except:
            return False
    
    def get_stats(self) -> Dict:
        """Ritorna statistiche del source"""
        return {
            'name': self.name,
            'enabled': self.enabled,
            'last_fetch': self.last_fetch.isoformat() if self.last_fetch else None,
            'fetch_count': self.fetch_count,
            'error_count': self.error_count,
            'success_rate': (self.fetch_count - self.error_count) / max(self.fetch_count, 1) * 100
        }

