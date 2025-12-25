"""
Playbook Analyzer - Analisi post-azione per creazione playbook 2.0
Identifica combo vincenti e anti-pattern dai log di esecuzione.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime

from knowledge.knowledge_enhancer import knowledge_enhancer
from backend.core.ghostbrain_autogen import call_llm_streaming

logger = logging.getLogger('PlaybookAnalyzer')

class PlaybookAnalyzer:
    """Analizza log di esecuzione per estrarre conoscenza."""
    
    def __init__(self):
        self.enhancer = knowledge_enhancer
        
    def analyze_session(self, objective: str, steps_data: List[Dict[str, Any]]) -> Dict:
        """
        Analizza una sessione completa di step per estrarre playbook.
        
        Args:
            objective: Obiettivo originale
            steps_data: Lista di risultati step (command, output, status)
            
        Returns:
            Dict con risultati analisi (successi, fallimenti)
        """
        logger.info(f"Avvio analisi playbook per obiettivo: {objective[:50]}...")
        
        # 1. Prepara contesto per LLM
        session_log = f"OBIETTIVO: {objective}\n\n"
        for step in steps_data:
            status_icon = "✅" if step.get('status') == 'completato' else "❌"
            session_log += f"{status_icon} STEP {step.get('step_number')}: {step.get('step_description')}\n"
            session_log += f"   CMD: {step.get('command')}\n"
            session_log += f"   OUT: {str(step.get('result', ''))[:500]}...\n\n"
            
        # 2. Prompt per analisi
        prompt = f"""
Sei un esperto di Cybersecurity e Knowledge Management.
Analizza il seguente log di esecuzione per creare un "Playbook 2.0".

LOG SESSIONE:
{session_log}

COMPITI:
1. Identifica la "Combo Vincente" (SUCCESS): La sequenza esatta di comandi che ha portato al risultato utile.
   - Quali flag erano essenziali?
   - Qual è il contesto specifico in cui funziona?
   
2. Identifica gli "Anti-Pattern" (FAILURE): Cosa NON ha funzionato e perché.
   - Comandi che hanno dato errore o timeout.
   - Approcci sbagliati per questo target specifico.

FORMATO RISPOSTA JSON:
{{
    "successes": [
        {{
            "title": "Titolo descrittivo successo",
            "content": "Descrizione dettagliata, comandi, e contesto in markdown",
            "commands": ["cmd1", "cmd2"],
            "tags": ["tag1", "tag2"]
        }}
    ],
    "failures": [
        {{
            "title": "Titolo descrittivo fallimento/errore",
            "content": "Spiegazione del perché non ha funzionato e cosa evitare",
            "avoid_commands": ["cmd_errato"],
            "tags": ["error", "tag2"]
        }}
    ]
}}

Se non ci sono successi o fallimenti rilevanti, restituisci liste vuote.
Sii tecnico e preciso.
"""

        try:
            # Chiamata LLM (simulata o reale)
            # Qui usiamo call_llm_streaming ma accumuliamo la risposta
            full_response = ""
            for chunk in call_llm_streaming(prompt, max_tokens=2000, temperature=0.2):
                if chunk:
                    full_response += chunk
            
            # Parsing JSON (gestione errori base)
            import json
            
            # Pulisci markdown json se presente
            clean_response = full_response.replace('```json', '').replace('```', '').strip()
            
            analysis = json.loads(clean_response)
            
            # 3. Salvataggio in Knowledge Base
            saved_count = {'success': 0, 'failure': 0}
            
            # Salva successi
            for success in analysis.get('successes', []):
                self.enhancer.add_playbook_entry(
                    entry_type='success',
                    title=success.get('title', 'Unknown Success'),
                    content=success.get('content', ''),
                    metadata={
                        'objective': objective,
                        'tags': success.get('tags', []),
                        'commands': success.get('commands', [])
                    }
                )
                saved_count['success'] += 1
                
            # Salva fallimenti
            for failure in analysis.get('failures', []):
                self.enhancer.add_playbook_entry(
                    entry_type='failure',
                    title=failure.get('title', 'Unknown Failure'),
                    content=failure.get('content', ''),
                    metadata={
                        'objective': objective,
                        'tags': failure.get('tags', []),
                        'avoid_commands': failure.get('avoid_commands', [])
                    }
                )
                saved_count['failure'] += 1
            
            logger.info(f"Analisi completata: {saved_count['success']} successi, {saved_count['failure']} fallimenti salvati.")
            return saved_count
            
        except Exception as e:
            logger.error(f"Errore durante analisi playbook: {e}")
            return {'error': str(e)}

# Istanza globale
playbook_analyzer = PlaybookAnalyzer()

