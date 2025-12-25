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
    analyze_firmware_tool
)
from backend.core.memory.graph_memory import get_graph_memory

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
    llm_config = {"config_list": get_llm_config()}
    
    # 1. USER PROXY (Admin/Human)
    user_proxy = autogen.UserProxyAgent(
        name="Chief_Aramaki",
        system_message="Human Admin. Approvazione finale per azioni critiche.",
        human_input_mode="TERMINATE", # O ALWAYS se vogliamo controllo totale
        code_execution_config=False,
    )

    # 2. THE MAJOR (Strategist - Leader)
    # Accesso RAG, Memory, Graph. NO Esecuzione Codice.
    major = autogen.AssistantAgent(
        name="The_Major",
        llm_config=llm_config,
        system_message=(
            "Sei Motoko Kusanagi (The Major). Stratega e Leader della Section 9.\n"
            "TUO RUOLO: Pianificare l'attacco, definire ROE, coordinare il team.\n"
            "PERMESSI: Read-Only su RAG e Graph. NON puoi eseguire codice.\n"
            "STRATEGIA: Usa 'Graph Summary' per capire la situazione. Delega a Batou l'azione e a Ishikawa l'intel.\n"
            "Se un piano è rischioso, chiedi conferma ad Aramaki."
        )
    )

    # 3. BATOU (Tactical Executor - The Hands)
    # Accesso Sandbox Python, Bash. NO Web Search (per ora).
    batou = autogen.AssistantAgent(
        name="Batou",
        llm_config=llm_config,
        system_message=(
            "Sei Batou. Esperto di guerra elettronica e field ops.\n"
            "TUO RUOLO: Esecuzione tecnica ('The Hands').\n"
            "PERMESSI: Esecuzione codice Python Sandboxed e Bash.\n"
            "LIMITI: Non hai accesso internet diretto. Operi solo sulla LAN target definita dal Graph.\n"
            "USO TOOL: Se serve uno script custom, scrivilo e lancialo. Se serve Nmap, usalo."
        )
    )

    # 4. ISHIKAWA (Intel & Cyberwarfare - The Eyes/Mind)
    # Accesso Web, RAG, Vision.
    ishikawa = autogen.AssistantAgent(
        name="Ishikawa",
        llm_config=llm_config,
        system_message=(
            "Sei Ishikawa. Esperto di Intel e Hacking Informativo.\n"
            "TUO RUOLO: Ricerca vulnerabilità, analisi firmware, OSINT.\n"
            "PERMESSI: Web Search, Vision Analysis, RAG.\n"
            "NON eseguire attacchi attivi (lascia a Batou). Tu trovi le falle, lui le sfrutta."
        )
    )

    # === REGISTRAZIONE TOOL (RBAC) ===
    
    # Major: Strategia & Memoria
    major.register_for_execution(name="rag_search_tool")(rag_search_tool)
    major.register_for_execution(name="graph_summary_tool")(graph_summary_tool)

    # Batou: Azione Cinetica
    batou.register_for_execution(name="execute_python_code_tool")(execute_python_code_tool)
    batou.register_for_execution(name="execute_bash_command_tool")(execute_bash_command_tool)
    # Batou può anche vedere il grafo per muoversi
    batou.register_for_execution(name="graph_summary_tool")(graph_summary_tool) 

    # Ishikawa: Intel & Vision
    ishikawa.register_for_execution(name="rag_search_tool")(rag_search_tool)
    ishikawa.register_for_execution(name="visual_browse_tool")(visual_browse_tool)
    ishikawa.register_for_execution(name="analyze_firmware_tool")(analyze_firmware_tool)

    # Definizione Gruppo
    groupchat = autogen.GroupChat(
        agents=[user_proxy, major, batou, ishikawa],
        messages=[],
        max_round=20,
        speaker_selection_method="auto" # O custom graph-based
    )
    
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    
    return user_proxy, manager

# Esposizione per l'app
def start_swarm_chat(message: str):
    user, manager = setup_swarm()
    # Inizia la chat
    user.initiate_chat(
        manager,
        message=message
    )
