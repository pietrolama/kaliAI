
import logging
import sys
from backend.agents.swarm import setup_swarm

# Setup logging to console
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s [%(name)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('DEBUG_SWARM')

def test_swarm_execution():
    print("[-] Setting up Swarm...")
    try:
        user, manager, groupchat = setup_swarm()
        print("[+] Swarm Setup OK.")
    except Exception as e:
        print(f"[!] Swarm Setup FAILED: {e}")
        return

    print("[-] Initiating Chat (Simple Query)...")
    
    # Simple query that SHOULD NOT require heavy tools
    message = "Major, report status. Do not use tools. Just reply."
    
    try:
        # Set a timeout signal test? No, just run it.
        print("[-] Calling initiate_chat...")
        user.initiate_chat(manager, message=message)
        print("[+] initiate_chat returned.")
    except Exception as e:
        print(f"[!] Chat Execution FAILED: {e}")
        import traceback
        traceback.print_exc()

    print("[-] Checking history...")
    print(f"Total Messages: {len(groupchat.messages)}")
    for msg in groupchat.messages:
        role = msg.get('name', msg.get('role'))
        content = msg.get('content', '')[:50]
        print(f" -> [{role}]: {content}...")

if __name__ == "__main__":
    test_swarm_execution()
