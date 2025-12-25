#!/usr/bin/env python3
"""
Smart Context Builder - Costruisce contesto ricco per l'LLM invece di hard-coding.

Filosofia: Aiuta l'LLM a ragionare correttamente da subito, non correggere dopo.
"""
import logging
from typing import Dict, Optional, List

logger = logging.getLogger('SmartContext')

class SmartContextBuilder:
    """Costruisce contesto intelligente per step generation"""
    
    @staticmethod
    def build_network_context() -> str:
        """
        Esegue scan preliminare della rete e costruisce contesto.
        L'LLM può usare questi dati invece di fare scan ripetuti.
        
        Strategia ottimizzata:
        1. Scan veloce range comune (192.168.1.1-50) - 15 secondi
        2. Se fallisce, fallback scan completo limitato
        """
        import subprocess
        
        try:
            # Quick scan range comune (router + primi 50 host)
            # Più veloce di /24 completo
            result = subprocess.run(
                ['nmap', '-sn', '-T5', '--min-rate', '1000', '--host-timeout', '500ms', 
                 '192.168.1.1-50'],
                capture_output=True,
                text=True,
                timeout=15  # Aumentato timeout
            )
            
            # Estrai dispositivi
            lines = result.stdout.split('\n')
            devices = []
            current_ip = None
            
            for line in lines:
                if 'Nmap scan report for' in line:
                    # Estrai IP e hostname
                    parts = line.split()
                    if len(parts) >= 5 and '(' in line:
                        # Formato: "Nmap scan report for hostname (IP)"
                        hostname = parts[4]
                        ip = parts[5].strip('()')
                        current_ip = {'ip': ip, 'hostname': hostname}
                    elif len(parts) >= 5:
                        # Formato: "Nmap scan report for IP"
                        ip = parts[4]
                        current_ip = {'ip': ip, 'hostname': ip}
                elif 'MAC Address:' in line and current_ip:
                    # Estrai vendor
                    vendor = line.split('(')[1].split(')')[0] if '(' in line else 'Unknown'
                    current_ip['vendor'] = vendor
                    devices.append(current_ip)
                    current_ip = None
                elif current_ip and 'Host is up' in line:
                    # Host trovato senza MAC (probabilmente quello locale)
                    devices.append(current_ip)
                    current_ip = None
            
            if not devices:
                logger.warning("Network scan: nessun dispositivo trovato")
                return ""
            
            # Costruisci contesto naturale con enfasi su MAC address vendor
            context = "RETE LOCALE SCANSIONATA:\n\n"
            
            for device in devices[:15]:  # Max 15 dispositivi
                context += f"• {device['ip']}"
                if device.get('hostname', '') not in ['', device['ip']]:
                    context += f" ({device['hostname']})"
                if device.get('vendor'):
                    context += f" - MAC Vendor: {device['vendor']}"
                context += "\n"
            
            context += f"\n✅ Trovati {len(devices)} host attivi"
            context += "\n💡 USA QUESTI IP nei comandi invece di fare scan ripetuti."
            context += "\n🎯 IMPORTANTE: MAC Address Vendor è identificatore affidabile per dispositivi specifici (es. 'Xiaomi Communications' per Xiaomi).\n"
            
            logger.info(f"Network scan: trovati {len(devices)} dispositivi")
            return context
            
        except subprocess.TimeoutExpired:
            logger.warning("Network scan timeout - usando fallback")
            # Fallback: almeno trova il gateway
            try:
                result = subprocess.run(
                    ['nmap', '-sn', '-T5', '192.168.1.1'],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                if '192.168.1.1' in result.stdout and 'Host is up' in result.stdout:
                    return "RETE LOCALE:\n\n• 192.168.1.1 (Gateway)\n\n💡 Scan completo fallito, usa discovery manuale.\n"
            except:
                pass
            return ""
        except Exception as e:
            logger.warning(f"Network context scan failed: {e}")
            return ""
    
    @staticmethod
    def build_objective_analysis(prompt: str, llm_call_fn) -> Optional[Dict]:
        """
        Chiede all'LLM di analizzare l'obiettivo PRIMA di generare step.
        
        Returns:
            {
                "target_description": str,  # "Google Home Mini sulla rete"
                "target_hints": List[str],  # ["cerca 'Google' in hostname", "porta 8008/8009"]
                "key_requirements": List[str],  # ["identificare IP", "ottenere shell"]
                "approach": str  # "network scan -> identify -> exploit"
            }
        """
        
        analysis_prompt = f"""Analizza questo obiettivo di penetration testing:

"{prompt}"

Rispondi in JSON con:
1. target_description: Descrizione del target da attaccare
2. target_hints: Come identificare il target nella rete (hostname patterns, MAC address vendor, porte tipiche, etc)
3. key_requirements: Requisiti chiave da soddisfare
4. approach: Strategia generale (3-5 parole)

⚠️ IMPORTANTE per identificazione target:
- Se l'utente specifica un modello/device (es. "Xiaomi Pad 5"), includi nel target_hints:
  * "MAC address vendor contiene 'Xiaomi Communications'" (identificatore più affidabile)
  * "hostname contiene 'Xiaomi' o 'Pad'"
- MAC address vendor è più affidabile dell'hostname per identificare dispositivi specifici

Esempio:
{{
  "target_description": "Xiaomi Pad 5 Android tablet",
  "target_hints": ["MAC address vendor contiene 'Xiaomi Communications'", "hostname contiene 'Xiaomi' o 'Pad'", "porta 5555 per ADB se debug wireless attivo"],
  "key_requirements": ["identificare IP del dispositivo con certezza via MAC vendor", "trovare porta ADB aperta", "ottenere accesso ai dati"],
  "approach": "identify target → scan ports → exploit"
}}

JSON:"""
        
        try:
            response = llm_call_fn(analysis_prompt)
            
            # Parse JSON dalla risposta
            import json
            import re
            
            # Cerca JSON nel response (potrebbe avere testo prima/dopo)
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                analysis = json.loads(json_match.group(0))
                logger.info(f"[ANALYSIS] Target: {analysis.get('target_description', 'N/A')}")
                return analysis
            
        except Exception as e:
            logger.warning(f"Objective analysis failed: {e}")
        
        return None
    
    @staticmethod
    def build_step_generation_context(
        prompt: str,
        network_context: str = "",
        objective_analysis: Optional[Dict] = None,
        rag_knowledge: str = ""
    ) -> str:
        """
        Costruisce contesto completo per generazione step intelligente.
        """
        
        context = f"OBIETTIVO PRINCIPALE:\n{prompt}\n\n"
        
        # Aggiungi conoscenza da RAG (IMPORTANTE!)
        if rag_knowledge:
            context += "📚 CONOSCENZA DALLA KNOWLEDGE BASE:\n"
            context += rag_knowledge + "\n"
            context += "⚠️ USA le CVE e tecniche sopra se rilevanti per il target!\n\n"
        
        # Aggiungi analisi obiettivo se disponibile
        if objective_analysis:
            context += "ANALISI OBIETTIVO:\n"
            context += f"• Target: {objective_analysis.get('target_description', 'N/A')}\n"
            
            hints = objective_analysis.get('target_hints', [])
            if hints:
                context += f"• Come identificare target:\n"
                for hint in hints:
                    context += f"  - {hint}\n"
            
            context += f"• Strategia: {objective_analysis.get('approach', 'N/A')}\n\n"
        
        # Aggiungi contesto di rete se disponibile
        if network_context:
            context += network_context + "\n"
        
        # Istruzioni per generazione step
        context += """
GENERA STEP INTELLIGENTI:
1. Ogni step deve essere SPECIFICO e usare dati reali (IP dal contesto sopra)
2. NO placeholder come <IP> o [target] - USA IP VERI
3. Se devi identificare un target, USA gli hint sopra
4. Comandi VELOCI (timeout max 10s): usa -T4, --max-retries 1, --host-timeout 10s
5. NO comandi complessi con pipe/loop - comandi SEMPLICI
6. USA CVE e tecniche dalla knowledge base quando applicabili

Genera 3-5 step operativi:"""
        
        return context
    
    @staticmethod
    def enrich_step_with_context(
        step_description: str,
        previous_results: List[Dict],
        objective_analysis: Optional[Dict] = None
    ) -> str:
        """
        Arricchisce un singolo step con contesto da step precedenti.
        """
        
        enriched = f"STEP DA ESEGUIRE:\n{step_description}\n\n"
        
        # Estrai dati critici da step precedenti
        found_ips = []
        found_devices = []
        
        for prev_step in previous_results:
            if prev_step.get('success'):
                output = prev_step.get('output', '')
                
                # Estrai IP
                import re
                ips = re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', output)
                found_ips.extend(ips)
                
                # Estrai device info se presente objective analysis
                if objective_analysis:
                    target_desc = objective_analysis.get('target_description', '').lower()
                    keywords = target_desc.split()[:3]  # Prime 3 parole chiave
                    
                    for line in output.split('\n'):
                        if any(kw in line.lower() for kw in keywords):
                            found_devices.append(line.strip())
        
        # Aggiungi dati trovati
        if found_ips:
            unique_ips = list(set(found_ips))[:10]
            enriched += f"IP IDENTIFICATI (USA QUESTI!):\n"
            for ip in unique_ips:
                enriched += f"  • {ip}\n"
            enriched += "\n"
        
        if found_devices:
            enriched += f"DISPOSITIVI IDENTIFICATI:\n"
            for dev in found_devices[:5]:
                enriched += f"  • {dev}\n"
            enriched += "\n"
        
        # Hint da objective analysis
        if objective_analysis:
            enriched += f"TARGET: {objective_analysis.get('target_description', 'N/A')}\n"
            enriched += "IMPORTANTE: Focalizzati SOLO su questo target specifico!\n\n"
        
        enriched += "GENERA COMANDO BASH ESEGUIBILE (max 150 caratteri, NO placeholder):\n"
        
        return enriched


# Funzione helper per uso facile
def build_smart_context_for_execution(prompt: str, llm_call_fn) -> Dict:
    """
    Costruisce tutto il contesto necessario per esecuzione intelligente.
    
    Returns:
        {
            "network_context": str,
            "objective_analysis": Dict,
            "rag_knowledge": str,
            "step_generation_context": str
        }
    """
    
    logger.info("[SMART-CONTEXT] Building intelligent context...")
    
    # 1. Scan rete preliminare (se possibile)
    network_ctx = SmartContextBuilder.build_network_context()
    
    # 2. Analisi obiettivo con LLM
    obj_analysis = SmartContextBuilder.build_objective_analysis(prompt, llm_call_fn)
    
    # 3. 🔥 NUOVO: Ricerca RAG sulla knowledge base
    rag_knowledge = ""
    try:
        from knowledge import knowledge_enhancer
        
        # Estrai keywords dal prompt per ricerca mirata
        target_desc = obj_analysis.get('target_description', prompt) if obj_analysis else prompt
        
        # Query principale: include vulnerability/exploit per CVE
        search_query = f"{target_desc} vulnerability exploit CVE"
        
        logger.info(f"[RAG-SEARCH] Query: {search_query[:80]}...")
        
        results = knowledge_enhancer.enhanced_search(search_query, top_k=3)
        
        # Se non trova risultati, prova query più generica (per IoT devices, protocolli, etc)
        if not results or len(results) == 0:
            logger.info("[RAG-SEARCH] Query specifica senza risultati, prova query generica...")
            generic_query = f"{target_desc} protocol port command"
            results = knowledge_enhancer.enhanced_search(generic_query, top_k=3)
        
        # Se ancora nulla, prova solo il target
        if not results or len(results) == 0:
            logger.info("[RAG-SEARCH] Query generica senza risultati, prova solo target...")
            simple_query = target_desc
            results = knowledge_enhancer.enhanced_search(simple_query, top_k=5)
        
        if results:
            logger.info(f"[RAG-SEARCH] Trovati {len(results)} documenti rilevanti")
            
            rag_knowledge = ""
            for i, res in enumerate(results, 1):
                source = res['source'].upper()
                doc = res['doc'][:400]  # Max 400 char per documento
                rag_knowledge += f"[{source}]\n{doc}\n\n"
            
            # Tronca se troppo lungo
            if len(rag_knowledge) > 1500:
                rag_knowledge = rag_knowledge[:1500] + "\n[...troncato...]"
        else:
            logger.info("[RAG-SEARCH] Nessun documento rilevante trovato")
            
    except Exception as e:
        logger.warning(f"[RAG-SEARCH] Errore: {e}")
        rag_knowledge = ""
    
    # 4. Contesto completo per step generation
    step_gen_ctx = SmartContextBuilder.build_step_generation_context(
        prompt, 
        network_ctx, 
        obj_analysis,
        rag_knowledge
    )
    
    return {
        "network_context": network_ctx,
        "objective_analysis": obj_analysis,
        "rag_knowledge": rag_knowledge,
        "step_generation_context": step_gen_ctx
    }

