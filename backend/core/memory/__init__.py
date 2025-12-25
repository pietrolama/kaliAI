"""
Memory Management Module
Gestisce memorie a lungo termine (ChromaDB) e contextual memory (JSON)
"""
from .memory_manager import (
    add_memory_to_vectordb,
    recall_from_vectordb,
    list_all_long_term_memories,
    delete_memory_from_vectordb,
    add_contextual_solution
)

__all__ = [
    'add_memory_to_vectordb',
    'recall_from_vectordb',
    'list_all_long_term_memories',
    'delete_memory_from_vectordb',
    'add_contextual_solution'
]

