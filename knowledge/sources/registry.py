#!/usr/bin/env python3
"""
Source Registry - Registro centrale per tutti i data sources
"""
from typing import Dict, List, Optional
from .base import DataSource

class SourceRegistry:
    """Registro centrale per gestire tutti i data sources"""
    
    def __init__(self):
        self._sources: Dict[str, DataSource] = {}
    
    def register(self, source: DataSource):
        """Registra un nuovo data source"""
        self._sources[source.name] = source
    
    def get(self, name: str) -> Optional[DataSource]:
        """Ottiene un source per nome"""
        return self._sources.get(name)
    
    def list_all(self) -> List[str]:
        """Lista tutti i source registrati"""
        return list(self._sources.keys())
    
    def list_enabled(self) -> List[str]:
        """Lista solo i source abilitati"""
        return [name for name, source in self._sources.items() if source.enabled]
    
    def get_all(self) -> Dict[str, DataSource]:
        """Ritorna tutti i sources"""
        return self._sources.copy()
    
    def get_stats(self) -> Dict:
        """Statistiche su tutti i sources"""
        total = len(self._sources)
        enabled = len(self.list_enabled())
        
        stats = {
            'total_sources': total,
            'enabled_sources': enabled,
            'disabled_sources': total - enabled,
            'sources': {}
        }
        
        for name, source in self._sources.items():
            stats['sources'][name] = source.get_stats()
        
        return stats

# Istanza globale
registry = SourceRegistry()

