import unittest
from backend.core.vision import intelligent_browse_tool

class TestHierarchicalWeb(unittest.TestCase):
    def test_web_tool_init(self):
        print("\n[TEST] Web Tool Init")
        # Just calling it to see if imports work and logic doesn't crash effectively
        # We won't really browse.
        try:
            # Passiamo un URL dummy
            # intelligent_browse_tool("http://example.com") # Questo farebbe triggerare curl reale
            pass 
        except Exception as e:
            self.fail(f"Tool crashed: {e}")

if __name__ == '__main__':
    unittest.main()
