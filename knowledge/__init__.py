"""
Knowledge System - Sistema di gestione della conoscenza per KaliAI

Questo package contiene tutti i moduli relativi alla knowledge base:
- Gestione database vettoriale (ChromaDB)
- Fetching da fonti esterne
- Hunting exploit automatico
- Enhancement e improvement
"""

from .knowledge_enhancer import knowledge_enhancer
from .knowledge_fetcher import fetcher
from .exploit_hunter import exploit_hunter

__all__ = ['knowledge_enhancer', 'fetcher', 'exploit_hunter']

