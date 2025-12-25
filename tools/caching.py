import hashlib
import json
import time
import logging
from functools import lru_cache
from typing import Any, Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger('Caching')


class ResponseCache:
    """Cache per risposte LLM."""
    
    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600):
        """
        Args:
            max_size: Dimensione massima cache
            ttl_seconds: Time-to-live delle entry in secondi
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.access_times: Dict[str, float] = {}
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, prompt: str, temperature: float = 0.3) -> Optional[Any]:
        """
        Recupera risposta dalla cache.
        
        Args:
            prompt: Prompt della richiesta
            temperature: Temperatura usata (parte della chiave)
            
        Returns:
            Risposta cached o None se non trovata
        """
        cache_key = self._generate_key(prompt, temperature)
        
        if cache_key in self.cache:
            # Check TTL
            entry = self.cache[cache_key]
            if time.time() - entry['timestamp'] < self.ttl_seconds:
                self.hit_count += 1
                self.access_times[cache_key] = time.time()
                logger.debug(f"Cache HIT per prompt: {prompt[:50]}...")
                return entry['response']
            else:
                # Entry scaduta
                del self.cache[cache_key]
                del self.access_times[cache_key]
        
        self.miss_count += 1
        logger.debug(f"Cache MISS per prompt: {prompt[:50]}...")
        return None
    
    def set(self, prompt: str, response: Any, temperature: float = 0.3):
        """
        Salva risposta in cache.
        
        Args:
            prompt: Prompt della richiesta
            response: Risposta da cachare
            temperature: Temperatura usata
        """
        cache_key = self._generate_key(prompt, temperature)
        
        # Evict se cache piena (LRU)
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        self.cache[cache_key] = {
            'response': response,
            'timestamp': time.time()
        }
        self.access_times[cache_key] = time.time()
        logger.debug(f"Cache SET per prompt: {prompt[:50]}...")
    
    def _generate_key(self, prompt: str, temperature: float) -> str:
        """Genera chiave cache univoca."""
        # Include temperatura nella chiave (temperature diverse = risposte diverse)
        key_data = f"{prompt}_{temperature}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _evict_lru(self):
        """Rimuove entry meno recentemente usata (LRU)."""
        if not self.access_times:
            return
        
        # Trova chiave con access time più vecchio
        lru_key = min(self.access_times, key=self.access_times.get)
        
        del self.cache[lru_key]
        del self.access_times[lru_key]
        logger.debug(f"Cache EVICT: {lru_key}")
    
    def clear(self):
        """Svuota cache."""
        self.cache.clear()
        self.access_times.clear()
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Ritorna statistiche cache."""
        total = self.hit_count + self.miss_count
        hit_rate = (self.hit_count / total * 100) if total > 0 else 0
        
        return {
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_count': self.hit_count,
            'miss_count': self.miss_count,
            'hit_rate': f"{hit_rate:.2f}%",
            'ttl_seconds': self.ttl_seconds
        }


class EmbeddingCache:
    """Cache per embeddings (più costosi da generare)."""
    
    def __init__(self, max_size: int = 5000):
        self.max_size = max_size
        self._cache: Dict[str, Any] = {}
    
    @lru_cache(maxsize=5000)
    def get_embedding_cached(self, text: str) -> str:
        """
        Ritorna hash dell'embedding (la vera cache è nell'lru_cache).
        Usare con embedding model che ha metodo .embed_query()
        """
        return hashlib.sha256(text.encode()).hexdigest()
    
    def clear(self):
        """Svuota cache."""
        self.get_embedding_cached.cache_clear()


class MemoryCache:
    """Cache per recall memoria vettoriale (evita query ripetute)."""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        Args:
            ttl_seconds: TTL breve (5 min default) - la memoria cambia spesso
        """
        self.ttl_seconds = ttl_seconds
        self.cache: Dict[str, Dict] = {}
    
    def get(self, query: str, top_k: int) -> Optional[list]:
        """Recupera recall dalla cache."""
        cache_key = self._generate_key(query, top_k)
        
        if cache_key in self.cache:
            entry = self.cache[cache_key]
            if time.time() - entry['timestamp'] < self.ttl_seconds:
                logger.debug(f"Memory cache HIT: {query[:50]}...")
                return entry['results']
            else:
                del self.cache[cache_key]
        
        return None
    
    def set(self, query: str, top_k: int, results: list):
        """Salva recall in cache."""
        cache_key = self._generate_key(query, top_k)
        self.cache[cache_key] = {
            'results': results,
            'timestamp': time.time()
        }
    
    def _generate_key(self, query: str, top_k: int) -> str:
        return hashlib.md5(f"{query}_{top_k}".encode()).hexdigest()
    
    def invalidate(self):
        """Invalida tutta la cache (chiamare dopo add_memory)."""
        self.cache.clear()
        logger.debug("Memory cache invalidated")


# Istanze globali
response_cache = ResponseCache(max_size=1000, ttl_seconds=3600)
embedding_cache = EmbeddingCache(max_size=5000)
memory_cache = MemoryCache(ttl_seconds=300)


def get_cache_stats() -> Dict[str, Any]:
    """Ritorna statistiche di tutte le cache."""
    return {
        'response_cache': response_cache.get_stats(),
        'memory_cache_size': len(memory_cache.cache),
        'embedding_cache_info': embedding_cache.get_embedding_cached.cache_info()._asdict()
    }

