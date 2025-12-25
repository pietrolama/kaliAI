import unittest
from backend.core.execution.python_sandbox import execute_python_sandboxed

class TestSandbox(unittest.TestCase):
    def test_safe_execution(self):
        print("\n[TEST] Safe Execution")
        code = "print('Hello from Podman')"
        result = execute_python_sandboxed(code)
        print(f"Result: {result}")
        self.assertIn("Hello from Podman", result)
        self.assertNotIn("SECURITY BLOCK", result)

    def test_unsafe_import(self):
        print("\n[TEST] Unsafe Import (subprocess)")
        code = "import subprocess"
        result = execute_python_sandboxed(code)
        print(f"Result: {result}")
        self.assertIn("SECURITY BLOCK", result)
        self.assertIn("Prohibited module import", result)

    def test_unsafe_path(self):
        print("\n[TEST] Unsafe Path (/etc/passwd)")
        code = "print(open('/etc/passwd').read())"
        result = execute_python_sandboxed(code)
        print(f"Result: {result}")
        self.assertIn("SECURITY BLOCK", result)
        self.assertIn("Prohibited path string", result)

if __name__ == '__main__':
    unittest.main()
