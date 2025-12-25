
import unittest
import time
from backend.core.execution import get_persistent_executor

class TestTheHands(unittest.TestCase):
    def setUp(self):
        self.executor = get_persistent_executor()
        self.executor.start()

    def test_state_persistence(self):
        print("\n[TEST] Testing Variable Persistence...")
        # Step 1: Define variable
        res1 = self.executor.execute_code("SECRET_VALUE = 1337")
        self.assertEqual(res1['status'], 'success')
        
        # Step 2: Retrieve variable
        res2 = self.executor.execute_code("print(SECRET_VALUE)")
        self.assertEqual(res2['status'], 'success')
        self.assertIn("1337", res2['output'])
        print(f"✅ State Persisted: {res2['output'].strip()}")

    def test_complex_logic(self):
        print("\n[TEST] Testing Complex Logic...")
        code = """
def factorial(n):
    return 1 if n == 0 else n * factorial(n-1)
print(factorial(5))
"""
        res = self.executor.execute_code(code)
        self.assertEqual(res['status'], 'success')
        self.assertIn("120", res['output'])
        print(f"✅ Calculation Correct: {res['output'].strip()}")

    def test_error_handling(self):
        print("\n[TEST] Testing Error Handling...")
        res = self.executor.execute_code("print(1/0)")
        self.assertEqual(res['status'], 'error')
        self.assertIn("ZeroDivisionError", res['error'])
        print(f"✅ Error Caught: {res['error'].splitlines()[-1]}")

if __name__ == '__main__':
    unittest.main()
