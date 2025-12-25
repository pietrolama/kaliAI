import os
from dotenv import load_dotenv

# Carica variabili ambiente
load_dotenv()

PROJECT_ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))


class Config:
    """Gestione centralizzata della configurazione."""
    
    def __init__(self):
        # API Configuration
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.OPENAI_BASE_URL = os.getenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1/')
        self.MODEL_NAME = os.getenv('MODEL_NAME', 'deepseek-chat')
        
        # Sandbox Configuration
        self.USE_DOCKER_SANDBOX = os.getenv("USE_DOCKER_SANDBOX", "false").lower() == "true"
        
        # Execution Configuration
        self.MAX_STEP_RETRIES = int(os.getenv('MAX_STEP_RETRIES', '3'))
        self.COMMAND_TIMEOUT = int(os.getenv('COMMAND_TIMEOUT', '120'))  # Aumentato per scan complessi
        self.LLM_TIMEOUT = int(os.getenv('LLM_TIMEOUT', '60'))
        
        # Paths
        self.DATA_PATH = os.path.join(PROJECT_ROOT, 'data')
        self.SESSION_PATH = os.path.join(self.DATA_PATH, 'session')
        
        self.CHROMA_DB_PATH = os.path.join(self.DATA_PATH, 'chroma_vector_db')
        self.STATIC_PATH = os.path.join(PROJECT_ROOT, 'frontend', 'static')
        self.KALI_KB_PATH = os.path.join(self.DATA_PATH, 'kaliAI.md')
        self.BASE_TEST_DIR = os.path.join(PROJECT_ROOT, 'test_env')
        
        self.CHAT_HISTORY_PATH = os.path.join(self.SESSION_PATH, 'chat_history.json')
        self.CONTEXTUAL_MEMORY_PATH = os.path.join(self.SESSION_PATH, 'contextual_memory.json')
        
        # Performance
        self.CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
        self.CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', '1000'))
        
        # Memory Configuration
        self.MEMORY_TOP_K = int(os.getenv('MEMORY_TOP_K', '3'))
        self.EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
        
        # LLM Parameters
        self.DEFAULT_MAX_TOKENS = int(os.getenv('DEFAULT_MAX_TOKENS', '2000'))
        self.DEFAULT_TEMPERATURE = float(os.getenv('DEFAULT_TEMPERATURE', '0.3'))
        
        # Crea directory necessarie
        os.makedirs(self.BASE_TEST_DIR, exist_ok=True)
        os.makedirs(self.SESSION_PATH, exist_ok=True)
        os.makedirs(self.STATIC_PATH, exist_ok=True)
        
    def validate(self):
        """Valida la configurazione."""
        errors = []
        
        if not self.OPENAI_API_KEY:
            errors.append("OPENAI_API_KEY mancante nelle variabili ambiente!")
        
        if not os.path.exists(self.KALI_KB_PATH):
            # Non bloccare se non esiste, potrebbe essere creato dopo
            pass
        
        if errors:
            raise ValueError(f"Errori di configurazione:\n" + "\n".join(f"- {e}" for e in errors))
        
        return True
    
    def get_llm_config(self):
        """Ritorna configurazione LLM per autogen."""
        return [{
            "model": self.MODEL_NAME,
            "api_key": self.OPENAI_API_KEY,
            "base_url": self.OPENAI_BASE_URL
        }]
    
    def __repr__(self):
        return (
            f"Config(model={self.MODEL_NAME}, "
            f"base_url={self.OPENAI_BASE_URL}, "
            f"docker={self.USE_DOCKER_SANDBOX})"
        )


# Istanza globale
config = Config()
