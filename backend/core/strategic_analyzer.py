#!/usr/bin/env python3
"""
Strategic Analyzer - Valuta se la strategia originale è ancora valida dopo la ricognizione
"""
import logging
from typing import Dict, Optional, Tuple

logger = logging.getLogger('StrategicAnalyzer')

def analyze_strategy_validity(
    original_objective: str,
    reconnaissance_results: str,
    current_steps: list,
    llm_call_fn
) -> Tuple[bool, Optional[str], Optional[list]]:
    """
    Analizza se la strategia originale è ancora valida dopo la ricognizione.
    
    Args:
        original_objective: Obiettivo originale dell'utente
        reconnaissance_results: Risultati della ricognizione iniziale (step 1-2)
        current_steps: Lista degli step attuali
        llm_call_fn: Funzione per chiamare l'LLM
        
    Returns:
        Tuple[is_valid, reason, new_strategy_suggestion]
        - is_valid: True se la strategia è ancora valida, False altrimenti
        - reason: Motivo per cui la strategia non è valida (se is_valid=False)
        - new_strategy_suggestion: Suggerimento per nuova strategia (se is_valid=False)
    """
    
    prompt = f"""
══════════════════════════════════════════════════
🔍 ANALISI STRATEGICA - REALITY CHECK
══════════════════════════════════════════════════

OBIETTIVO ORIGINALE:
{original_objective}

RISULTATI RICOGNIZIONE INIZIALE:
{reconnaissance_results}

STEP PIANIFICATI:
{chr(10).join(f"{i+1}. {step}" for i, step in enumerate(current_steps))}

══════════════════════════════════════════════════
DOMANDA CRITICA:
══════════════════════════════════════════════════

Analizza i risultati della ricognizione e valuta se la strategia pianificata è ancora appropriata.

⚠️ CRITERI PER STRATEGIA INVALIDA:
1. Mismatch tipo target:
   - Obiettivo: "Attacca applicazione web dinamica" → Ricognizione: "Sito statico su GitHub Pages" → ❌ INVALIDA
   - Obiettivo: "Trova vulnerabilità injection" → Ricognizione: "Server GitHub Pages (non accetta POST/input)" → ❌ INVALIDA
   - Obiettivo: "Accedi a dispositivo Android" → Ricognizione: "Dispositivo è router TP-Link (non Android)" → ❌ INVALIDA
   - Obiettivo: "Trova porta ADB" → Ricognizione: "Dispositivo è iPhone (non Android)" → ❌ INVALIDA

2. Tecnologia incompatibile:
   - Strategia: "Cerca form HTML per injection" → Ricognizione: "Sito statico senza form" → ❌ INVALIDA
   - Strategia: "Testa vulnerabilità database" → Ricognizione: "Sito statico senza backend" → ❌ INVALIDA

3. Protocollo errato:
   - Strategia: "Usa HTTP POST per injection" → Ricognizione: "Server rifiuta POST (405 Not Allowed)" → ❌ INVALIDA

✅ CRITERI PER STRATEGIA VALIDA:
- Il tipo di target corrisponde all'obiettivo
- La tecnologia identificata supporta gli attacchi pianificati
- I protocolli necessari sono disponibili

RISPOSTA RICHIESTA (JSON STRICTO):
{{
    "strategy_valid": true/false,
    "reason": "Motivo dettagliato (solo se strategy_valid=false, max 100 caratteri)",
    "target_type_identified": "Tipo reale del target (es. 'GitHub Pages static site', 'Android device', 'IoT router', 'Web application with forms')",
    "new_strategy_suggestion": "Breve suggerimento per nuova strategia appropriata (solo se strategy_valid=false, max 150 caratteri)"
}}

IMPORTANTE: Rispondi SOLO con JSON valido, senza altro testo. Il JSON deve essere parsabile direttamente.
"""
    
    try:
        response = llm_call_fn(prompt)
        
        # Estrai JSON dalla risposta
        import json
        import re
        
        # Cerca JSON nella risposta (pattern più robusto)
        json_match = re.search(r'\{[^{}]*"strategy_valid"[^{}]*\}', response, re.DOTALL)
        if not json_match:
            # Prova pattern più largo
            json_match = re.search(r'\{.*?"strategy_valid".*?\}', response, re.DOTALL)
        
        if json_match:
            try:
                result = json.loads(json_match.group())
            except json.JSONDecodeError:
                # Prova a pulire il JSON
                json_str = json_match.group()
                # Rimuovi commenti e fix comuni
                json_str = re.sub(r'//.*', '', json_str)  # Rimuovi commenti
                json_str = re.sub(r',\s*}', '}', json_str)  # Rimuovi trailing comma
                json_str = re.sub(r',\s*]', ']', json_str)
                result = json.loads(json_str)
        else:
            # Fallback: prova a parsare tutta la risposta
            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                # Ultimo tentativo: cerca valori booleani
                if 'false' in response.lower() or '"strategy_valid": false' in response:
                    # Strategia probabilmente invalida
                    reason_match = re.search(r'"reason":\s*"([^"]+)"', response)
                    target_match = re.search(r'"target_type_identified":\s*"([^"]+)"', response)
                    strategy_match = re.search(r'"new_strategy_suggestion":\s*"([^"]+)"', response)
                    
                    return False, \
                           reason_match.group(1) if reason_match else "Strategia non appropriata per target identificato", \
                           strategy_match.group(1) if strategy_match else None
                else:
                    # Default: strategia valida
                    logger.warning(f"[STRATEGIC-ANALYZER] Impossibile parsare JSON, assumo strategia valida")
                    return True, None, None
        
        is_valid = result.get('strategy_valid', True)
        reason = result.get('reason', '')
        target_type = result.get('target_type_identified', '')
        new_strategy = result.get('new_strategy_suggestion', '')
        
        logger.info(f"[STRATEGIC-ANALYZER] Strategia valida: {is_valid}")
        if not is_valid:
            logger.warning(f"[STRATEGIC-ANALYZER] Strategia invalida: {reason}")
            logger.info(f"[STRATEGIC-ANALYZER] Target identificato: {target_type}")
            logger.info(f"[STRATEGIC-ANALYZER] Nuova strategia suggerita: {new_strategy}")
        
        return is_valid, reason, new_strategy if not is_valid else None
        
    except Exception as e:
        logger.warning(f"[STRATEGIC-ANALYZER] Errore analisi: {e}, assumo strategia valida")
        import traceback
        traceback.print_exc()
        return True, None, None

