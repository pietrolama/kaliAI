import logging
import functools
from typing import Any, Callable, Optional

logger = logging.getLogger('ErrorHandling')


class GhostBrainError(Exception):
    """Eccezione base per errori di GhostBrain."""
    pass


class SecurityError(GhostBrainError):
    """Errore relativo alla sicurezza (comando bloccato, etc)."""
    pass


class LLMError(GhostBrainError):
    """Errore durante chiamata LLM."""
    pass


class ConfigurationError(GhostBrainError):
    """Errore di configurazione."""
    pass


class MemoryError(GhostBrainError):
    """Errore nella gestione della memoria."""
    pass


class ExecutionError(GhostBrainError):
    """Errore durante esecuzione comandi."""
    pass


def safe_execute(error_message: str, default_return: Any = None, log_traceback: bool = False):
    """
    Decorator per esecuzione sicura di funzioni.
    
    Args:
        error_message: Messaggio da loggare in caso di errore
        default_return: Valore di default da ritornare in caso di errore
        log_traceback: Se True, logga anche lo stack trace completo
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"{error_message}: {e}")
                if log_traceback:
                    import traceback
                    logger.error(traceback.format_exc())
                return default_return
        return wrapper
    return decorator


def safe_execute_with_retry(max_retries: int = 3, error_message: str = "Errore", 
                            default_return: Any = None):
    """
    Decorator per esecuzione con retry automatico.
    
    Args:
        max_retries: Numero massimo di tentativi
        error_message: Messaggio da loggare
        default_return: Valore di default in caso di fallimento totale
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    logger.warning(
                        f"{error_message} (tentativo {attempt}/{max_retries}): {e}"
                    )
                    if attempt == max_retries:
                        logger.error(f"{error_message}: Fallito dopo {max_retries} tentativi")
            return default_return
        return wrapper
    return decorator


class ErrorHandler:
    """Gestione centralizzata degli errori."""
    
    @staticmethod
    def handle_llm_error(e: Exception, context: str = "") -> str:
        """Gestisce errori LLM."""
        error_msg = f"Errore LLM"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {str(e)}"
        logger.error(error_msg)
        return f"[LLM ERROR] {str(e)}"
    
    @staticmethod
    def handle_security_error(command: str, reason: str = "") -> str:
        """Gestisce errori di sicurezza."""
        error_msg = f"Comando bloccato: {command}"
        if reason:
            error_msg += f" - {reason}"
        logger.warning(error_msg)
        raise SecurityError(error_msg)
    
    @staticmethod
    def handle_execution_error(e: Exception, command: str = "") -> str:
        """Gestisce errori di esecuzione."""
        error_msg = f"Errore esecuzione"
        if command:
            error_msg += f" ({command})"
        error_msg += f": {str(e)}"
        logger.error(error_msg)
        return f"[EXEC ERROR] {str(e)}"
    
    @staticmethod
    def handle_memory_error(e: Exception, operation: str = "") -> None:
        """Gestisce errori di memoria."""
        error_msg = f"Errore memoria"
        if operation:
            error_msg += f" ({operation})"
        error_msg += f": {str(e)}"
        logger.error(error_msg)

