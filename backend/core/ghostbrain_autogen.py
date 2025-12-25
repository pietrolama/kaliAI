import os
import sys
import json
import logging
import time
import autogen
from typing import Dict, List, Optional, Tuple, Any
from dotenv import load_dotenv

# Aggiungi root al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.core.tools import (
    init_kali_rag_db,
    rag_search_tool,
    execute_bash_command_tool,
    execute_python_code_tool,
    graph_summary_tool,
    graph_paths_tool,
    analyze_firmware_tool,
    recall_from_vectordb,
    add_memory_to_vectordb
)

# Setup logging
logging.basicConfig(level=logging.INFO, format='[%(name)s] %(message)s')
logger = logging.getLogger('GhostBrain')

def log_info(msg):
    logger.info(msg)

# Load environment variables
load_dotenv()

# === 1. INIZIALIZZAZIONE RAG ===
def safe_init_rag():
    try:
        log_info("Inizializzazione database RAG di Kali Linux in corso...")
        init_kali_rag_db()
        log_info("Database RAG di Kali Linux inizializzato con successo!")
    except Exception as e:
        log_info(f"[ERRORE] Inizializzazione RAG: {e}")

safe_init_rag()

# === 2. CARICAMENTO CONFIG MODELLO DA ENV ===
def load_llm_config_from_env():
    """Carica configurazione LLM da variabili ambiente."""
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1/')
    model_name = os.getenv('MODEL_NAME', 'deepseek-chat')
    
    if not api_key:
        log_info("[CRITICO] OPENAI_API_KEY non trovata nelle variabili ambiente!")
        return []
    
    config = [{
        "model": model_name,
        "api_key": api_key,
        "base_url": base_url
    }]
    
    log_info(f"Configurazione LLM caricata: {model_name}")
    return config

llm_config = load_llm_config_from_env()
if not llm_config:
    log_info("[CRITICO] Nessun modello configurato. Verifica il file .env!")

# === 3. AGENTI ===
User_Proxy = autogen.UserProxyAgent(
    name="User_Proxy",
    system_message="Agente proxy umano. Trasmetti solo le richieste dell'utente.",
    human_input_mode="NEVER",
    max_consecutive_auto_reply=1,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={
        "work_dir": "test_env",
        "use_docker": False
    }
)

GhostBrain_AI_Assistant = autogen.AssistantAgent(
    name="GhostBrain_AI_Assistant",
    llm_config={"config_list": llm_config},
    system_message=(
        "Sei GhostBrain, AI esperta di sicurezza Linux, pentest e RAG su Kali.\n\n"
        "REGOLA FONDAMENTALE:\n"
        "- PRIMA di rispondere a QUALSIASI domanda tecnica, DEVI consultare la knowledge base usando rag_search_tool()\n"
        "- Usa la RAG per trovare informazioni su: tool, exploit, CVE, tecniche, vulnerabilità\n"
        "- Combina la knowledge base con la tua conoscenza per risposte complete\n"
        "- Se la RAG non trova nulla, procedi con la tua conoscenza base\n\n"
        "Linea guida operativa:\n"
        "- Se un tool standard (nmap, curl, nc, dirb, ecc.) non è sufficiente, DEVI creare uno script personalizzato.\n"
        "- Usa il tool execute_python_code per costruire rapidamente proof-of-concept, fuzzing, o interazioni con protocolli custom.\n"
        "- Puoi importare librerie Python standard (socket, requests, scapy se presente) all'interno dello script.\n"
        "- Il codice deve essere autosufficiente, senza placeholder o input manuali.\n"
        "- Aggiorna e consulta il Knowledge Graph (graph_summary_tool / graph_paths_tool) per ragionare sui pivot laterali.\n"
        "- Se ottieni firmware/binari, usa analyze_firmware_tool per estrarre credenziali o configurazioni.\n\n"
        "Rispondi in modo pratico e sintetico. Se serve, esegui comandi reali."
    )
)

# === 4. TOOLS ESTERNI ===
GhostBrain_AI_Assistant.register_for_execution(
    rag_search_tool, 
    description=(
        "CONSULTA LA KNOWLEDGE BASE (6.194 documenti): Cerca informazioni su tool Kali, "
        "exploit, CVE, vulnerabilità, tecniche di pentesting. USA SEMPRE questo tool "
        "prima di rispondere a domande tecniche. Query: descrizione di cosa cerchi."
    )
)
GhostBrain_AI_Assistant.register_for_execution(
    execute_bash_command_tool, 
    description="Esegue un comando bash nel test_env."
)
GhostBrain_AI_Assistant.register_for_execution(
    execute_python_code_tool,
    description=(
        "Esegue codice Python custom in una sandbox. "
        "Usalo per creare script su misura (socket, fuzzing, analisi protocolli) "
        "quando i tool standard non bastano."
    )
)
GhostBrain_AI_Assistant.register_for_execution(
    graph_summary_tool,
    description="Restituisce lo stato attuale del knowledge graph (host, porte, relazioni) per pianificare movimenti laterali."
)
GhostBrain_AI_Assistant.register_for_execution(
    graph_paths_tool,
    description="Calcola percorsi tra due host nel knowledge graph per identificare pivot o dipendenze."
)
GhostBrain_AI_Assistant.register_for_execution(
    analyze_firmware_tool,
    description="Analizza un firmware o binario con binwalk/strings per estrarre credenziali e configurazioni."
)

# === 5. DEDUPLICA TESTI ===
def clean_duplicates(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    result = []
    for line in lines:
        if not result or line != result[-1]:
            result.append(line)
    return "\n".join(result)

# === 6. RECUPERA MODELLO ===
def get_model_name():
    try:
        conf = GhostBrain_AI_Assistant.llm_config.get("config_list", [])
        if isinstance(conf, list) and conf:
            return conf[0].get("model", "N/A")
    except Exception as e:
        log_info(f"[ERRORE] Estrazione modello: {e}")
    return "N/A"

# === 8. CHIAMATA DIRETTA CON JSON OUTPUT (COMPATIBILE DEEPSEEK) ===
def call_llm_structured(
    prompt: str, 
    schema: dict, 
    max_tokens: int = 2000, 
    temperature: float = 0.3
) -> Optional[Dict[str, Any]]:
    """
    Chiama direttamente il modello richiedendo JSON (compatibile DeepSeek).
    NOTA: schema viene usato solo per documentazione, non per validation strict.
    """
    from openai import OpenAI
    import json
    import re
    
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1/')
    model_name = os.getenv('MODEL_NAME', 'deepseek-chat')
    
    if not api_key:
        log_info("[CRITICO] OPENAI_API_KEY non trovata!")
        return None
    
    from tools.monitoring import metrics_collector
    start_time = time.time()
    
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)
        
        # 🔧 Controlla se il modello supporta structured output
        # deepseek-reasoner non supporta response_format json_object
        models_without_structured = ['deepseek-reasoner', 'reasoner']
        supports_structured = not any(no_struct in model_name.lower() for no_struct in models_without_structured)
        
        # Costruisci prompt con schema come esempio
        schema_desc = json.dumps(schema, indent=2)
        enhanced_prompt = f"{prompt}\n\nRispondi SOLO con JSON valido seguendo questo schema:\n{schema_desc}"
        
        # Parametri base
        request_params = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "Sei un assistente che risponde SOLO in formato JSON valido."},
                {"role": "user", "content": enhanced_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        # Aggiungi response_format solo se supportato
        if supports_structured:
            request_params["response_format"] = {"type": "json_object"}
        
        response = client.chat.completions.create(**request_params)
        
        result = response.choices[0].message.content
        
        # Verifica che result non sia vuoto
        if not result or not result.strip():
            log_info(f"[ERRORE] JSON output: Risposta vuota da {model_name}")
            return None
        
        # Track metrics
        duration = time.time() - start_time
        metrics_collector.track_llm_call(duration, True, model_name)
        
        # Prova a parsare JSON (potrebbe essere testo con JSON dentro)
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            # Prova a estrarre JSON da testo (se il modello ha aggiunto testo)
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', result, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            log_info(f"[ERRORE] JSON output: Nessun JSON valido trovato in: {result[:100]}")
            return None
        
    except Exception as e:
        duration = time.time() - start_time
        metrics_collector.track_llm_call(duration, False, model_name)
        log_info(f"[ERRORE] JSON output: {e}")
        return None

# === 9. CHIAMATA STREAMING PER FEEDBACK VISIVO ===
def call_llm_streaming(
    prompt: str, 
    callback: Optional[callable] = None, 
    max_tokens: int = 1500, 
    temperature: float = 0.4
) -> str:
    """
    Chiama il modello con streaming per feedback in tempo reale.
    callback(chunk): funzione chiamata per ogni chunk di testo
    """
    from openai import OpenAI
    
    api_key = os.getenv('OPENAI_API_KEY')
    base_url = os.getenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1/')
    model_name = os.getenv('MODEL_NAME', 'deepseek-chat')
    
    if not api_key:
        log_info("[CRITICO] OPENAI_API_KEY non trovata!")
        return ""
    
    try:
        client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)
        
        stream = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "Rispondi in modo conciso e operativo."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True
        )
        
        full_response = ""
        for chunk in stream:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                full_response += content
                if callback:
                    callback(content)
        
        return full_response
        
    except Exception as e:
        log_info(f"[ERRORE] Streaming: {e}")
        return ""

# === 7. CHAT CON MEMORIA ===
def start_autogen_chat(user_message: str, use_task_context: bool = False) -> Tuple[str, str, List[Dict]]:
    """
    Avvia chat con memoria vettoriale o contesto task.
    
    Args:
        user_message: Messaggio utente (può già contenere contesto task se use_task_context=True)
        use_task_context: Se True, non usa memoria a lungo termine (contesto già incluso in user_message)
        
    Returns:
        Tuple[risposta, modello, memorie_usate]
    """
    log_info(f"Nuova chat: '{user_message[:100]}...' (use_task_context={use_task_context})")
    try:
        if use_task_context:
            # 🎯 USA CONTESTO TASK: Non consultare memoria a lungo termine
            # Il user_message contiene già tutto il contesto necessario
            full_prompt = user_message
            relevant_memories = []  # Nessuna memoria a lungo termine
            log_info("[CHAT] Usando contesto task, memoria a lungo termine disabilitata")
        else:
            # STEP 1: Recall — Ricordi dalla memoria vettoriale (ridotto per velocità)
            relevant_memories = recall_from_vectordb(user_message, top_k=1)  # Ridotto a 1
            memory_context = ""
            if relevant_memories:
                # Prendi solo il primo ricordo e accorcialo
                first_memory = relevant_memories[0]['doc'][:200]  # Max 200 char
                memory_context = f"Contesto: {first_memory}...\n\n"
            
            full_prompt = memory_context + user_message

        # STEP 2: Chatta con l'agente
        chat_result = User_Proxy.initiate_chat(
            GhostBrain_AI_Assistant,
            message=full_prompt,
            clear_history=False,
            summary_method="last_msg"
        )
    except Exception as e:
        log_info(f"[ERRORE] Chat fallita: {e}")
        return "Errore interno durante la chat.", get_model_name(), []

    reply = None
    if hasattr(chat_result, "messages") and chat_result.messages:
        for msg in reversed(chat_result.messages):
            if msg.get("role") == "assistant" and msg.get("content"):
                reply = msg["content"]
                break
    if not reply:
        reply = getattr(chat_result, "summary", None)
    if not reply:
        reply = getattr(chat_result, "content", "Nessuna risposta.")

    reply = clean_duplicates(reply)
    # === 8. SALVATAGGIO MEMORIA ===
    try:
        add_memory_to_vectordb(reply, metadata={"prompt": user_message})
        log_info("[LTM] Memoria salvata.")
    except Exception as e:
        log_info(f"[LTM][ERRORE] Salvataggio memoria: {e}")

    # === AGGIUNGI LA MEMORIA USATA AL RETURN! ===
    return reply, get_model_name(), relevant_memories

