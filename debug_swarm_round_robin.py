
import logging
import sys
import autogen
from backend.agents.swarm import setup_swarm

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def test_round_robin():
    print("[-] Setting up Swarm (Round Robin Forced)...")
    
    # Manually re-implement setup to force round_robin
    from backend.agents.swarm import get_llm_config, rag_search_tool, execute_python_code_tool, execute_bash_command_tool, graph_summary_tool
    
    llm_config = {"config_list": get_llm_config()}
    
    # Recreate agents roughly as in swarm.py
    user_proxy = autogen.UserProxyAgent(name="Chief_Aramaki", system_message="Admin", human_input_mode="NEVER", code_execution_config=False)
    major = autogen.AssistantAgent(name="The_Major", system_message="Leader", llm_config=llm_config)
    batou = autogen.AssistantAgent(name="Batou", system_message="Tactical", llm_config=llm_config)
    ishikawa = autogen.AssistantAgent(name="Ishikawa", system_message="Intel", llm_config=llm_config)
    
    # Force Round Robin
    groupchat = autogen.GroupChat(
        agents=[user_proxy, major, batou, ishikawa],
        messages=[],
        max_round=5, # Short round
        speaker_selection_method="round_robin" 
    )
    
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)
    
    print("[-] Initiating Chat...")
    user_proxy.initiate_chat(manager, message="Identify yourself and your role.")
    
    print("[+] Chat Completed.")

if __name__ == "__main__":
    test_round_robin()
