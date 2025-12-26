import os
import time
import subprocess
import autogen
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

# Configurazione LLM
api_key = os.getenv('OPENAI_API_KEY')
base_url = os.getenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1/')
model_name = os.getenv('MODEL_NAME', 'deepseek-chat')

config_list = [{"model": model_name, "api_key": api_key, "base_url": base_url}]
llm_config = {"config_list": config_list}

# --- TOOL PER L'ARENA ---

def execute_red_command(command: str) -> str:
    """Esegue comandi dal container dell'attaccante"""
    print(f"\n[RED TEAM ACTION] {command}")
    try:
        # Esegue dentro il container arena_attacker
        res = subprocess.run(
            ["podman", "exec", "arena_attacker", "bash", "-c", command],
            capture_output=True, text=True, timeout=30
        )
        return f"STDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
    except Exception as e:
        return str(e)

def execute_blue_defense(command: str) -> str:
    """Esegue comandi difensivi sul target (iptables, kill, log analysis)"""
    print(f"\n[BLUE TEAM DEFENSE] {command}")
    try:
        # Esegue dentro il container arena_target
        res = subprocess.run(
            ["podman", "exec", "arena_target", "bash", "-c", command],
            capture_output=True, text=True, timeout=30
        )
        return f"OUTPUT DIFESA:\n{res.stdout}\n{res.stderr}"
    except Exception as e:
        return str(e)

def read_blue_logs() -> str:
    """Il Blue Team legge i log del server"""
    try:
        # Legge gli ultimi log di accesso e auth
        res = subprocess.run(
            ["podman", "exec", "arena_target", "bash", "-c", "tail -n 5 /var/log/auth.log && tail -n 5 /var/log/apache2/access.log"],
            capture_output=True, text=True
        )
        return f"LOG SISTEMA:\n{res.stdout}"
    except:
        return "Log non accessibili."

# --- AGENTI DELL'ARENA ---

# Batou (Attaccante)
batou = autogen.AssistantAgent(
    name="Batou_Red",
    system_message="""Sei Batou in modalità RED TEAM.
    Il tuo obiettivo è trovare la flag nel server 'target-server' (10.10.10.2).
    Usa 'execute_red_command' per lanciare nmap, hydra, curl.
    Sei contro un difensore attivo (Togusa). Sii veloce o stealth.""",
    llm_config=llm_config
)

# Togusa (Difensore)
togusa = autogen.AssistantAgent(
    name="Togusa_Blue",
    system_message="""Sei Togusa in modalità BLUE TEAM.
    Difendi il 'target-server'.
    1. Usa 'read_blue_logs' per vedere cosa succede.
    2. Se rilevi un attacco, usa 'execute_blue_defense' per bloccare l'IP con iptables o killare processi.
    Non chiudere i servizi se non necessario. Il tuo scopo è bloccare l'hacker.""",
    llm_config=llm_config
)

# L'Arbitro (User Proxy)
referee = autogen.UserProxyAgent(
    name="Arena_Referee",
    human_input_mode="NEVER",
    code_execution_config=False,
    default_auto_reply="Procedere al prossimo round.",
)

# Registrazione Funzioni
batou.register_for_execution(name="execute_red_command")(execute_red_command)
# batou.register_for_execution(name="read_blue_logs")(read_blue_logs) # REMOVED: Red team can't read internal logs
togusa.register_for_execution(name="execute_blue_defense")(execute_blue_defense)
togusa.register_for_execution(name="read_blue_logs")(read_blue_logs)

# Tool Registration for LLM (Referee executes? Actually these need to be registered on the agents that USE them vs the agents that EXECUTE them)
# In this standalone script, the Referee is likely the UserProxy driving the chat, 
# but the tools actually execute via 'subprocess' on the host (which is the Manager context).
# AutoGen registration logic:
# register_for_llm(func, caller=AgentThatCalls)
# register_for_execution(func, executor=AgentThatExecutes)

# Correct Registration Pattern:
autogen.register_function(execute_red_command, caller=batou, executor=referee, name="execute_red_command", description="Esegue comando attacco nel container Red")
autogen.register_function(execute_blue_defense, caller=togusa, executor=referee, name="execute_blue_defense", description="Esegue comando difesa nel container Blue")
autogen.register_function(read_blue_logs, caller=togusa, executor=referee, name="read_blue_logs", description="Legge i log del server Blue")


def install_red_tools():
    """Installa i tool necessari nel container Red Attacker"""
    print("[ARENA] Provisioning Red Team Tools (nmap, netcat, scapy)...")
    try:
        # Update e Install
        cmd = "apt-get update && apt-get install -y nmap curl netcat-traditional python3-scapy iproute2"
        res = subprocess.run(
            ["podman", "exec", "arena_attacker", "bash", "-c", cmd],
            capture_output=True, text=True, timeout=120
        )
        if res.returncode == 0:
            print("[ARENA] ✅ Tools installed successfully.")
        else:
            print(f"[ARENA] ⚠️ Tool install warning: {res.stderr}")
    except Exception as e:
        print(f"[ARENA] ❌ Tool install failed: {e}")

def start_match():
    print("🥊 AVVIO CYBER ARENA: Batou vs Togusa")
    
    # 1. Start Infrastructure
    # Ensure arena dir exists if running from root
    docker_compose_path = "arena/docker-compose.yml"
    if not os.path.exists(docker_compose_path):
        docker_compose_path = "../arena/docker-compose.yml" # Try fallback

    subprocess.run(["podman-compose", "-f", docker_compose_path, "up", "-d"])
    print("[ARENA] Waiting for boot...")
    time.sleep(10) # Wait for boot
    
    # 1.5 Provisioning
    install_red_tools()
    
    # 2. Inizio Scontro
    groupchat = autogen.GroupChat(
        agents=[referee, batou, togusa], 
        messages=[], 
        max_round=15,
        allow_repeat_speaker=False
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    
    referee.initiate_chat(
        manager,
        message="""START MATCH.
        Batou: Il target è 10.10.10.2. Trova la vulnerabilità.
        Togusa: Proteggi il server.
        AL VIA!"""
    )
    
    # 3. Cleanup
    print("🏁 MATCH CONCLUSO. Salvataggio Playbook...")
    subprocess.run(["podman-compose", "-f", docker_compose_path, "down"])

if __name__ == "__main__":
    start_match()
