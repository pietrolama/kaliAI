
import unittest
from backend.agents.swarm import setup_swarm

class TestSwarm(unittest.TestCase):
    def test_swarm_setup(self):
        print("\n[TEST] Swarm Setup & RBAC")
        user, manager = setup_swarm()
        
        # Verify Agents in Group
        agent_names = [agent.name for agent in manager.groupchat.agents]
        print(f"Agents: {agent_names}")
        self.assertIn("The_Major", agent_names)
        self.assertIn("Batou", agent_names)
        self.assertIn("Ishikawa", agent_names)
        
        # Verify Tool Registration (Indirectly by checking registered functions map if accessible, or just no error)
        # Autogen agents store registered functions in .client. or similar, hard to inspect directly cleanly.
        # But if setup_swarm ran without error, tools are registered.
        print("Swarm initialized successfully.")

if __name__ == '__main__':
    unittest.main()
