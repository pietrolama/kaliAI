#!/usr/bin/env python3
"""
Test completo del sistema KaliAI per verificare che tutti i moduli funzionino.
"""

import sys
import os

# Setup path
sys.path.insert(0, os.path.dirname(__file__))

def test_imports():
    """Test import di tutti i moduli."""
    print("🔧 Test Import Moduli...")
    
    try:
        from config import config
        print("  ✅ config")
    except Exception as e:
        print(f"  ❌ config: {e}")
        return False
    
    try:
        from error_handling import safe_execute
        print("  ✅ error_handling")
    except Exception as e:
        print(f"  ❌ error_handling: {e}")
        return False
    
    try:
        from security import SecurityValidator
        print("  ✅ security")
    except Exception as e:
        print(f"  ❌ security: {e}")
        return False
    
    try:
        from caching import response_cache
        print("  ✅ caching")
    except Exception as e:
        print(f"  ❌ caching: {e}")
        return False
    
    try:
        from monitoring import metrics_collector
        print("  ✅ monitoring")
    except Exception as e:
        print(f"  ❌ monitoring: {e}")
        return False
    
    try:
        from memory_manager import memory_manager
        print("  ✅ memory_manager")
    except Exception as e:
        print(f"  ❌ memory_manager: {e}")
        return False
    
    try:
        from modules.ghostbrain_autogen import start_autogen_chat
        print("  ✅ ghostbrain_autogen")
    except Exception as e:
        print(f"  ❌ ghostbrain_autogen: {e}")
        return False
    
    try:
        from modules.tools import execute_bash_command
        print("  ✅ tools")
    except Exception as e:
        print(f"  ❌ tools: {e}")
        return False
    
    try:
        from app import app
        print("  ✅ Flask app")
    except Exception as e:
        print(f"  ❌ Flask app: {e}")
        return False
    
    return True


def test_config():
    """Test configurazione."""
    print("\n🔧 Test Configurazione...")
    
    from config import config
    
    try:
        config.validate()
        print("  ✅ Configurazione valida")
        print(f"     - Modello: {config.MODEL_NAME}")
        print(f"     - Base URL: {config.OPENAI_BASE_URL}")
        print(f"     - Timeout: {config.COMMAND_TIMEOUT}s")
        return True
    except Exception as e:
        print(f"  ❌ Configurazione non valida: {e}")
        return False


def test_security():
    """Test sicurezza."""
    print("\n🔧 Test Security...")
    
    from security import SecurityValidator
    
    # Test comandi sicuri
    safe_cmds = ["ls -la", "echo test"]
    for cmd in safe_cmds:
        is_valid, reason = SecurityValidator.validate_command(cmd)
        if not is_valid:
            print(f"  ❌ Comando sicuro bloccato: {cmd}")
            return False
    
    # Test comandi pericolosi
    dangerous_cmds = ["rm -rf /", "sudo reboot"]
    for cmd in dangerous_cmds:
        is_valid, reason = SecurityValidator.validate_command(cmd)
        if is_valid:
            print(f"  ❌ Comando pericoloso NON bloccato: {cmd}")
            return False
    
    print("  ✅ Validazione comandi funziona")
    return True


def test_monitoring():
    """Test monitoring."""
    print("\n🔧 Test Monitoring...")
    
    from monitoring import metrics_collector
    import time
    
    # Track operazioni
    metrics_collector.track_llm_call(0.5, True, "test-model")
    metrics_collector.track_command_execution("ls", 0.1, True, 100)
    
    metrics = metrics_collector.get_metrics()
    
    if metrics['llm']['total_calls'] < 1:
        print("  ❌ Metrics non tracciati")
        return False
    
    print("  ✅ Monitoring funziona")
    print(f"     - LLM calls: {metrics['llm']['total_calls']}")
    print(f"     - Commands: {metrics['commands']['total_executions']}")
    return True


def test_chat():
    """Test chat (senza chiamata API reale)."""
    print("\n🔧 Test Chat...")
    
    # Test che la funzione esista e sia chiamabile
    from modules.ghostbrain_autogen import start_autogen_chat
    
    print("  ✅ Chat function importabile")
    print("     (Skip test API reale)")
    return True


def main():
    print("=" * 60)
    print("TEST SISTEMA KALIAI")
    print("=" * 60)
    
    all_ok = True
    
    # Run tests
    if not test_imports():
        all_ok = False
    
    if not test_config():
        all_ok = False
    
    if not test_security():
        all_ok = False
    
    if not test_monitoring():
        all_ok = False
    
    if not test_chat():
        all_ok = False
    
    print("\n" + "=" * 60)
    if all_ok:
        print("✅ TUTTI I TEST PASSATI - Sistema funzionante")
        print("=" * 60)
        print("\nPer avviare il sistema:")
        print("  ./start.sh")
        return 0
    else:
        print("❌ ALCUNI TEST FALLITI - Verifica gli errori sopra")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

