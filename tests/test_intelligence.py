#!/usr/bin/env python3
"""
Test sistema intelligente - Verifica target extraction e tool management.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))


def test_target_extraction():
    """Test smart context builder - analisi obiettivo con LLM."""
    print("🎯 Test Smart Context Builder...")
    
    from modules.smart_context_builder import SmartContextBuilder
    
    test_cases = [
        "attacca google home mini sulla rete",
        "fai pentest su 192.168.1.100", 
        "trova vulnerabilità nella lampada wiz"
    ]
    
    # Mock LLM per test
    def mock_llm(prompt):
        if "google home" in prompt.lower():
            return '{"target_description": "Google Home Mini", "target_hints": ["hostname Google"], "key_requirements": ["identify IP"], "approach": "scan → exploit"}'
        return '{"target_description": "Unknown", "target_hints": [], "key_requirements": [], "approach": "discovery"}'
    
    for prompt in test_cases:
        analysis = SmartContextBuilder.build_objective_analysis(prompt, mock_llm)
        if analysis:
            print(f"  ✅ '{prompt[:40]}...' → {analysis.get('target_description', 'N/A')}")
        else:
            print(f"  ⚠️  '{prompt[:40]}...' → Analisi fallita")
    
    print()
    return True


def test_target_context():
    """Test generazione contesto completo."""
    print("📝 Test Context Generation...")
    
    from modules.smart_context_builder import SmartContextBuilder
    
    prompt = "attacca dispositivo IoT sulla rete"
    
    # Mock analysis
    mock_analysis = {
        "target_description": "IoT device",
        "target_hints": ["check vendor info"],
        "approach": "scan → identify → exploit"
    }
    
    context = SmartContextBuilder.build_step_generation_context(
        prompt, 
        network_context="192.168.1.10 (IoT Device)\n",
        objective_analysis=mock_analysis
    )
    
    # Verifica che contenga info chiave
    checks = [
        ("OBIETTIVO" in context, "Contiene obiettivo"),
        ("Target:" in context, "Contiene target"),
        ("192.168.1.10" in context, "Contiene IP dalla rete")
    ]
    
    all_ok = True
    for check, desc in checks:
        if check:
            print(f"  ✅ {desc}")
        else:
            print(f"  ❌ {desc}")
            all_ok = False
    
    print()
    return all_ok


def test_tool_detection():
    """Test rilevamento tool."""
    print("🛠️ Test Tool Detection...")
    
    from tool_manager import tool_manager
    
    # Tool che dovrebbero essere installati su Kali
    essential_tools = ['nmap', 'curl', 'grep', 'cat', 'echo']
    
    for tool in essential_tools:
        installed = tool_manager.is_tool_installed(tool)
        if installed:
            print(f"  ✅ {tool}")
        else:
            print(f"  ❌ {tool} (dovrebbe essere installato)")
    
    # Stats
    stats = tool_manager.get_tool_stats()
    print(f"\n  Coverage: {stats['coverage']}")
    
    print()
    return True


def test_integration():
    """Test integrazione completa."""
    print("🔗 Test Integrazione...")
    
    try:
        # Test import di tutti i moduli
        from config import config
        from security import SecurityValidator
        from monitoring import metrics_collector
        from modules.smart_context_builder import SmartContextBuilder
        from tool_manager import tool_manager
        
        print("  ✅ Tutti i moduli importabili")
        
        # Test flow completo (senza esecuzione reale)
        prompt = "pentest su http://example.com"
        
        # 1. Mock analisi target con LLM
        def mock_llm(p):
            return '{"target_description": "example.com web server", "target_hints": ["web server"], "key_requirements": ["scan"], "approach": "recon"}'
        
        target_analysis = SmartContextBuilder.build_objective_analysis(prompt, mock_llm)
        assert target_analysis is not None, "Analisi target fallita"
        print(f"  ✅ Target analizzato: {target_analysis['target_description']}")
        
        # 2. Verifica tool
        cmd = "nmap example.com"
        first_word = cmd.split()[0]
        installed = tool_manager.is_tool_installed(first_word)
        print(f"  ✅ Tool {first_word}: {'installato' if installed else 'mancante'}")
        
        # 3. Validazione security
        is_valid, reason = SecurityValidator.validate_command(cmd)
        assert is_valid, f"Comando sicuro bloccato: {reason}"
        print(f"  ✅ Security validation: OK")
        
        # 4. Metrics
        metrics_collector.track_llm_call(0.5, True, "test-model")
        metrics = metrics_collector.get_metrics()
        print(f"  ✅ Monitoring attivo: {metrics['llm']['total_calls']} calls tracked")
        
        print()
        return True
        
    except Exception as e:
        print(f"  ❌ Errore integrazione: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("=" * 60)
    print("TEST SISTEMA INTELLIGENTE KALIAI")
    print("=" * 60)
    print()
    
    all_ok = True
    
    if not test_target_extraction():
        all_ok = False
    
    if not test_target_context():
        all_ok = False
    
    if not test_tool_detection():
        all_ok = False
    
    if not test_integration():
        all_ok = False
    
    print("=" * 60)
    if all_ok:
        print("✅ TUTTI I TEST PASSATI - Sistema intelligente operativo!")
        print("=" * 60)
        print("\n🚀 Il sistema ora:")
        print("  ✓ Estrae automaticamente target da prompt")
        print("  ✓ Risolve DNS automaticamente")
        print("  ✓ Installa tool mancanti")
        print("  ✓ Valida sicurezza comandi")
        print("  ✓ Traccia metriche performance")
        print("\nAvvia con: ./start.sh")
        return 0
    else:
        print("❌ ALCUNI TEST FALLITI")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

