import unittest
from backend.core.intelligence import get_scholar

class TestIntel(unittest.TestCase):
    def test_scholar_init(self):
        print("\n[TEST] Scholar Init")
        scholar = get_scholar()
        self.assertIsNotNone(scholar)
        # Non chiamiamo update_cisa_kev per non scaricare file giganti, 
        # testiamo solo l'inizializzazione e paths.
        print(f"Verified Feeds Path: {scholar.data_path}")

if __name__ == '__main__':
    unittest.main()
