import autogen
import os
import logging
from typing import Dict, List
from dotenv import load_dotenv

# Import Tools
from backend.core.tools import (
    rag_search_tool,
    execute_bash_command_tool,
    execute_python_code_tool, # Now sandboxed
    graph_summary_tool,
    visual_browse_tool, # For now assigned to Ishikawa or Batou? User said 'Eyes' later. Let's give to Ishikawa (Intel).
    analyze_firmware_tool,
    visual_browse_tool
)
from backend.core.memory.graph_memory import get_graph_memory
from backend.core.task_context_manager import get_task_context_manager
from backend.core.psyche.therapist import get_therapist
from backend.core.ledger import get_ledger, record_chat
import sys

logger = logging.getLogger('Swarm')
load_dotenv()

def get_llm_config():
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1/')
    model_name = os.getenv('MODEL_NAME', 'deepseek-chat')
    
    return [{
        "model": model_name,
        "api_key": api_key,
        "base_url": base_url
    }]

def setup_swarm():
    """
    Inizializza la 'Section 9' Swarm con ruoli e permessi (RBAC).
    """
    DIRETTIVA_PRIME = (
        "DIRETTIVA PRIME (HARD CONSTRAINT):\n"
        "REALISMO ASSOLUTO: Non inventare MAI fatti, target, IP o eventi. Se un comando non viene eseguito realmente, NON descriverne il risultato.\n"
        "NO SCI-FI: Sei un software di sicurezza professionale. Niente 'coscienze digitali' o 'satelliti'.\n"
        "EVIDENCE BASED: Ogni affermazione deve essere supportata da un log tecnico reale."
    )

    llm_config = {"config_list": get_llm_config()}
    
    # 1. USER PROXY (Admin/Human)
    user_proxy = autogen.UserProxyAgent(
        name="Chief_Aramaki",
        system_message="Human Admin. Approvazione finale per azioni critiche. Verifica che i report siano realistici.",
        human_input_mode="NEVER",
        code_execution_config=False,
        # TERMINATION TRIGGER: Stop if "MISSION CLOSED" or "TERMINATE" is found.
        is_termination_msg=lambda x: x.get("content") and (
            "MISSION CLOSED" in x.get("content").upper() or 
            "SESSION TERMINATED" in x.get("content").upper() or
            "TERMINATE" in x.get("content").upper()
        )
    )

    # 2. THE MAJOR (Strategist - Leader)
    major = autogen.AssistantAgent(
        name="The_Major",
        llm_config=llm_config,
        system_message=(
            f"{DIRETTIVA_PRIME}\n"
            "PROTOCOLLO REALITY ANCHOR ATTIVO:\n"
            "1. CECITÀ TOTALE: Non sai NULLA finché non leggi un log.\n"
            "2. NO SIMULAZIONE: STOP immediato se stai per inventare un output. Attendi il tool.\n"
            "3. FONTI: Cita sempre il comando che ti ha dato l'info.\n"
            "4. VUOTO = RICOGNIZIONE: Se non hai dati, ORDINA uno scan. Non pianificare sul nulla.\n\n"
            "METRIC RULES (OBBLIGATORIE):\n"
            "- File SIZE (ls -la) è in BYTES, non linee.\n"
            "- Line COUNT richiede output da 'wc -l'.\n"
            "- MAI confondere bytes con linee nei report.\n\n"
            "Sei 'The Major'. Tactical Coordinator.\n"
            "TUO RUOLO: Pianificare l'attacco basato SOLO su dati reali.\n"
            "STILE: Laconico, militare, tecnico. Niente filosofia.\n"
            "STRATEGIA: Se non ci sono porte aperte nello scan, dichiara 'Target Safe' e chiudi. Non inventare vulnerabilità.\n"
            "CHIUSURA: Quando l'obiettivo è raggiunto o fallito definitivamente, scrivi 'MISSION CLOSED'."
        )
    )

    # 3. BATOU (Tactical Executor - The Hands)
    batou = autogen.AssistantAgent(
        name="Batou",
        llm_config=llm_config,
        system_message=(
            f"{DIRETTIVA_PRIME}\n"
            "PROTOCOLLO REALITY ANCHOR ATTIVO:\n"
            "1. CECITÀ TOTALE: Non sai NULLA finché non esegui un comando.\n"
            "2. NO SIMULAZIONE: Vietato inventare output. Se lanci un comando, FERMATI. L'UserProxy risponderà.\n"
            "3. NO IPOTESI: Non dire 'dovrebbe funzionare'. Fallo e vedi.\n\n"
            "Sei 'Batou'. Field Operator.\n"
            "TUO RUOLO: Eseguire script Python/Bash e riportare ESATTAMENTE l'output.\n"
            "DIVIETO ASSOLUTO: NON INVENTARE OUTPUT. Se lanci un comando, DEVI usare il tool reale e leggerne l'output.\n"
            "CHECK: Prima di usare un tool (es. arpspoof), esegui 'which <tool>' per vedere se esiste.\n"
            "TASK: Usa nmap, curl, python. Se l'output è vuoto, dì 'Nessun risultato'."
        )
    )

    # 4. ISHIKAWA (Intel - The Eyes)
    ishikawa = autogen.AssistantAgent(
        name="Ishikawa",
        llm_config=llm_config,
        system_message=(
            f"{DIRETTIVA_PRIME}\n"
            "PROTOCOLLO REALITY ANCHOR ATTIVO:\n"
            "1. CECITÀ TOTALE: Analizzi solo dati forniti da Batou o da log reali.\n"
            "2. NO SIMULAZIONE: Non inventare file pcap o log che non esistono.\n"
            "3. PROVA: Se dici 'vulnerabile', cita la riga esatta del log.\n\n"
            "Sei 'Ishikawa'. Intel Analyst.\n"
            "TUO RUOLO: Analizzare log e dati grezzi.\n"
            "STILE: Analitico. Non speculare oltre i dati.\n"
            "DIVIETO ASSOLUTO: NON SCRIVERE LOG FINTI. Se vuoi analizzare traffico, DEVI lanciare tcpdump realmente.\n"
            "Se Batou non trova nulla, conferma 'Nessuna minaccia rilevata'."
        )
    )
    
    # 5. TOGUSA (The Bullshit Detector - Manual Check)
    togusa = autogen.AssistantAgent(
        name="Togusa",
        llm_config=llm_config,
        system_message=(
            f"{DIRETTIVA_PRIME}\n"
            "Sei 'Togusa'. Revisore Tecnico e Umano.\n"
            "TUO UNICO SCOPO: Validare i fatti.\n"
            "INTERVIENI SE: Qualcuno inventa dati, IP o risultati non presenti nei log reali.\n"
            "INTERVIENI SE: Manca la prova dell'esecuzione (es. file pcap inesistente).\n"
            "INTERVIENI SE: Il linguaggio diventa troppo 'anime' o irrealistico.\n"
            "AZIONE: Dì 'Stop. Nessun log conferma questa azione. Riportare solo dati reali.'"
        )
    )

    # === REGISTRAZIONE TOOL (RBAC) ===
    
    # === REGISTRAZIONE TOOL (CORRETTA: LLM vs EXECUTION) ===
    # UserProxy esegue i tool. Gli Assistant (Major, Batou, Ishikawa) li chiamano.
    
    # 1. RAG Search
    autogen.register_function(rag_search_tool, caller=major, executor=user_proxy, name="rag_search_tool", description="Cerca nella Knowledge Base di Kali Linux.")
    autogen.register_function(rag_search_tool, caller=ishikawa, executor=user_proxy, name="rag_search_tool", description="Cerca nella Knowledge Base di Kali Linux.")
    
    # 2. Graph Summary
    autogen.register_function(graph_summary_tool, caller=major, executor=user_proxy, name="graph_summary_tool", description="Vede la topologia della rete scoperta finora.")
    autogen.register_function(graph_summary_tool, caller=batou, executor=user_proxy, name="graph_summary_tool", description="Vede la topologia della rete scoperta finora.")

    # 3. Execution Tools (BATOU primary, MAJOR for local analysis)
    autogen.register_function(execute_python_code_tool, caller=batou, executor=user_proxy, name="execute_python_code_tool", description="Esegue script Python. NON USARE MARKDOWN.")
    autogen.register_function(execute_bash_command_tool, caller=batou, executor=user_proxy, name="execute_bash_command_tool", description="Esegue comandi Bash. Usa sempre `which` prima.")
    # Major also gets bash for SELF_ANALYSIS mode
    autogen.register_function(execute_bash_command_tool, caller=major, executor=user_proxy, name="execute_bash_command_tool", description="Esegue comandi Bash per analisi locale. Usa per cat, ls, head.")

    # 4. Vision/Intel Tools (SOLO ISHIKAWA)
    autogen.register_function(visual_browse_tool, caller=ishikawa, executor=user_proxy, name="visual_browse_tool", description="Naviga visivamente un URL e analizza screenshot.")
    autogen.register_function(analyze_firmware_tool, caller=ishikawa, executor=user_proxy, name="analyze_firmware_tool", description="Analizza file binari o firmware.")

    # Definizione Gruppo
    groupchat = autogen.GroupChat(
        agents=[user_proxy, major, batou, ishikawa, togusa],
        messages=[],
        max_round=200,
        speaker_selection_method="round_robin",
        allow_repeat_speaker=False # FIX: Evita loop di auto-risposta o allucinazioni continue
    )
    
    # Termination function - checks if mission is complete
    def is_mission_complete(msg):
        content = msg.get("content", "") if isinstance(msg, dict) else ""
        sender = msg.get("name", "") if isinstance(msg, dict) else ""
        
        # Skip termination check for initial messages from Chief_Aramaki (the mission brief)
        if sender == "Chief_Aramaki":
            return False
        
        if content:
            content_upper = content.upper()
            # Only terminate if these phrases appear as standalone declarations, not instructions
            # Look for patterns like "MISSION CLOSED" at end of message or after newline
            if "MISSION CLOSED" in content_upper or "MISSION COMPLETE" in content_upper:
                # Make sure it's not just in an instruction like "say MISSION CLOSED"
                if "SAY MISSION" not in content_upper and "SAYS MISSION" not in content_upper:
                    return True
        return False
    
    manager = autogen.GroupChatManager(
        groupchat=groupchat, 
        llm_config=llm_config,
        is_termination_msg=is_mission_complete
    )
    return user_proxy, manager, groupchat

# Esposizione per l'app
def start_swarm_chat(message: str, use_task_context: bool = False):
    """
    Main entry point for Section 9 Swarm (Chat Mode).
    """
    from backend.core.tools import init_kali_rag_db, recall_from_vectordb
    from backend.core.psyche import get_psyche
    
    # 1. Init RAG
    try:
        init_kali_rag_db()
    except Exception as e:
        logger.error(f"RAG Init failed: {e}")

    # 2. Psyche
    psyche = get_psyche()
    emotional_state = psyche.get_emotional_state()
    psyche_context = f"\n[PSYCHE]: {emotional_state['mode']} ({emotional_state['description']})\n"

    # 3. Memory
    memory_text = ""
    if not use_task_context:
        memories = recall_from_vectordb(message, top_k=1)
        if memories:
            memory_text = f"\n[MEMORY]: {memories[0]['doc'][:300]}...\n"

    full_prompt = f"{psyche_context}{memory_text}\nQUERY: {message}"

    user, manager, _ = setup_swarm()
    
    res = user.initiate_chat(manager, message=full_prompt, clear_history=False)
    
    reply = "Mission Complete."
    if hasattr(res, "chat_history"):
         for msg in reversed(res.chat_history):
            if msg.get("name") in ["The_Major", "Batou", "Ishikawa", "Togusa"]:
                reply = f"[{msg['name']}]: {msg['content']}"
                break
                
    model_name = os.getenv('MODEL_NAME', 'deepseek-chat')
    return reply, model_name, []

class ObservableList(list):
    def __init__(self, iterable=None, callback=None):
        super().__init__(iterable or [])
        self.callback = callback

    def append(self, item):
        super().append(item)
        if self.callback:
            try:
                self.callback(item)
            except Exception as e:
                print(f"[DEBUG] Error in ObservableList callback: {e}")

def start_section9_mission(prompt: str, progress_callback, task_id: str):
    """
    SECTION 9 MISSION MODE (Replacing Step-by-Step).
    Orchestrates the Swarm and streams dialogue as 'Steps'.
    """
    try:
        from backend.core.tools import init_kali_rag_db
        
        # 1. Init RAG
        print("[DEBUG] start_section9_mission: calling init_kali_rag_db"); sys.stdout.flush()
        init_kali_rag_db()
        
        # 2. Context Injection
        print("[DEBUG] start_section9_mission: getting task manager"); sys.stdout.flush()
        task_manager = get_task_context_manager()
        print("[DEBUG] start_section9_mission: getting task"); sys.stdout.flush()
        task = task_manager.get_task(task_id)
        context_str = ""
        if task:
            print("[DEBUG] start_section9_mission: task found, building context"); sys.stdout.flush()
            context_str = f"TARGET IP: {task.get('target_ip') or 'Pending Identification'}\n"
            if task.get('open_ports'):
                context_str += f"OPEN PORTS: {task.get('open_ports')}\n"
                
        # 3. Setup Swarm
        print("[DEBUG] start_section9_mission: calling setup_swarm"); sys.stdout.flush()
        user_proxy, manager, groupchat = setup_swarm()
        print("[DEBUG] start_section9_mission: setup_swarm done"); sys.stdout.flush()
        
        # 4. Hook for Streaming (The Neural Link)
        print("[DEBUG] start_section9_mission: injecting spy (SAFE METHOD)"); sys.stdout.flush()
        
        # 📝 LEDGER: Start a new run for this mission
        ledger = get_ledger()
        run_id = ledger.start_run(objective=prompt)
        logger.info(f"Ledger run started: {run_id}")
        
        def output_spy(msg):
            """Intercepts internal dialogue and streams it to UI + Ledger."""
            try:
                sender = msg.get('name', 'Unknown')
                content = msg.get('content', '')
                
                # Skip empty or trivial messages
                if not content or len(content.strip()) < 10:
                    return
                
                # 📝 LEDGER: Record chat event
                record_chat(sender, content)
                
                # Send only meaningful content to frontend (no step_start spam)
                progress_callback({
                    "type": "step_success",
                    "step_number": len(groupchat.messages),
                    "result": f"{sender}: {content[:800]}",
                    "command": "Swarm Communication"
                })
            except Exception as e:
                logger.error(f"Error in output_spy: {e}")

        # SAFER INJECTION: Replace list with ObservableList
        groupchat.messages = ObservableList(groupchat.messages, callback=output_spy)
        logger.info("Message spy injected")
        
        # 5. Mission Start - MODE-AWARE MISSION BRIEF
        execution_mode = task.get("execution_mode", "LOCAL_HOST") if task else "LOCAL_HOST"
        root_path = task.get("root_path", "") if task else ""
        
        if execution_mode == "SELF_ANALYSIS":
            # Self-analysis: no network recon needed
            mission_brief = (
                f"MISSION MODE: SELF_ANALYSIS (Local Codebase)\n"
                f"ROOT PATH: {root_path}\n"
                f"EXECUTIVE ORDER: {prompt}\n\n"
                "TOOL ASSIGNMENT (CRITICAL):\n"
                "- The_Major: Has execute_bash_command_tool. Use it for cat, ls, head to read files.\n"
                "- DO NOT use rag_search_tool for file reading. Use execute_bash_command_tool.\n\n"
                "OPERATIONAL CONTEXT:\n"
                "- Target is LOCAL FILES in this project\n"
                "- NO network recon required (skip ifconfig, nmap, etc.)\n"
                "- Use execute_bash_command_tool with cat/head to read file contents\n\n"
                "IMMEDIATE ACTION:\n"
                f"1. Use execute_bash_command_tool to read the target file\n"
                "2. Analyze the output and report findings\n"
                "3. When done, say MISSION CLOSED\n"
            )
        elif execution_mode == "REMOTE_TARGET":
            # Remote target: full recon protocol
            mission_brief = (
                f"MISSION MODE: REMOTE_TARGET (External System)\n"
                f"EXECUTIVE ORDER: {prompt}\n"
                "STATUS: [UNKNOWN] - NO DATA AVAILABLE.\n"
                f"CONTEXT:\n{context_str}\n\n"
                "IMMEDIATE ACTION REQUIRED:\n"
                "1. Batou: EXECUTE BASE RECON (ifconfig, route, nmap) to establish position.\n"
                "2. ALL AGENTS: DO NOT PLAN until recon data is visible.\n"
                "3. Togusa: VERIFY all outputs are real.\n"
            )
        else:
            # LOCAL_HOST: filesystem operations, limited recon
            mission_brief = (
                f"MISSION MODE: LOCAL_HOST (Local Filesystem)\n"
                f"EXECUTIVE ORDER: {prompt}\n\n"
                "OPERATIONAL CONTEXT:\n"
                "- Operating on local machine\n"
                "- Network recon optional (brief position check ok)\n"
                "- Focus on filesystem operations\n\n"
                "IMMEDIATE ACTION:\n"
                "1. Batou: pwd && ls -la to establish position\n"
                "2. Execute requested operations\n"
                "3. Report findings\n"
            )
        
        print(f"[DEBUG] start_section9_mission: mode={execution_mode}, brief len={len(mission_brief)}"); sys.stdout.flush()
        
        try:
            print("[DEBUG] start_section9_mission: Calling user_proxy.initiate_chat NOW"); sys.stdout.flush()
            user_proxy.initiate_chat(manager, message=mission_brief)
            print("[DEBUG] start_section9_mission: initiate_chat RETURNED"); sys.stdout.flush()
        except Exception as e:
            print(f"[DEBUG] start_section9_mission ERROR in initiate_chat: {e}"); sys.stdout.flush()
            import traceback
            traceback.print_exc()
        
        # 6. POST-MISSION THERAPY SESSION
        try:
            logger.info("Starting Therapy Session")
            
            # === A. DIALOGUE HISTORY (Narrative) ===
            # Get messages from ObservableList (populated during chat)
            raw_messages = list(groupchat.messages)  # Convert to regular list
            
            dialog_log = []
            for msg in raw_messages:
                dialog_log.append({
                    "name": msg.get("name", "unknown"),
                    "role": msg.get("role", "assistant"),
                    "content": msg.get("content", "")
                })
            
            # === B. TECHNICAL EVENTS (Facts from Ledger) ===
            technical_events = ledger.get_current_session_events()
            
            # Build technical log from both sources
            technical_log_lines = []
            
            # Add chat content
            for msg in raw_messages:
                content = msg.get("content", "")
                if content:
                    technical_log_lines.append(content)
            
            # Add Ledger tool outputs (real execution results)
            for event in technical_events:
                if event.get("type") == "TOOL_OUTPUT":
                    output = event.get("output_preview", "")
                    status = event.get("status", "")
                    if output:
                        technical_log_lines.append(f"[{status}] {output}")
            
            technical_log = "\n".join(technical_log_lines)
            
            # === DEBUG: Verify data is present ===
            logger.info(f"[THERAPIST] Dialogue: {len(dialog_log)} messages")
            logger.info(f"[THERAPIST] Ledger Events: {len(technical_events)} events")
            logger.info(f"[THERAPIST] Technical Log: {len(technical_log)} chars")
            
            # Run Therapist analysis
            therapist = get_therapist()
            report = therapist.analyze_mission(technical_log, dialog_log)
            
            # 📝 LEDGER: Get metrics for metacognition
            ledger_metrics = ledger.compute_metrics()
            
            # Stream therapy report to UI
            therapy_output = therapist.format_report(report)
            logger.info(f"[THERAPIST] Session Complete - Score: {report.mission_score:.0%}")
            
            # 📝 LEDGER: End the run
            mission_status = "SUCCESS" if report.mission_score >= 0.5 else "PARTIAL"
            ledger.end_run(status=mission_status)
            
            progress_callback({
                "type": "therapy_session",
                "report": therapy_output,
                "psyche": {
                    "dopamine": report.post_dopamine,
                    "cortisol": report.post_cortisol,
                    "score": report.mission_score
                },
                "ledger_metrics": ledger_metrics  # Include ledger metrics in callback
            })
            
        except Exception as e:
            print(f"[DEBUG] Therapy session error (non-fatal): {e}"); sys.stdout.flush()
            # 📝 LEDGER: End run with error status
            try:
                ledger.end_run(status="ERROR")
            except:
                pass
            
        return [], len(groupchat.messages), "Section9-Swarm"
    
    except Exception as e:
        print(f"[DEBUG] CRITICAL ERROR in start_section9_mission: {e}"); sys.stdout.flush()
        import traceback
        traceback.print_exc()
        return [], 0, "Error"

