import os
import base64
import logging
import time
from typing import Optional, Dict, Any
# from backend.core.ghostbrain_autogen import llm_config # REMOVED to avoid circular import
from tools.monitoring import metrics_collector

logger = logging.getLogger('VisionAnalyzer')

class VisionAnalyzer:
    """
    Analisi visiva (The Eyes - Cortex).
    Invia screenshot a modello Multimodal (DeepSeek-Janus / GPT-4V / Qwen-VL).
    """
    def __init__(self):
        # Load config directly from env to avoid circular dependency
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.base_url = os.getenv('OPENAI_BASE_URL', 'https://api.deepseek.com/v1/')
        self.model = os.getenv('MODEL_NAME', 'deepseek-chat') 
        # NOTA: Se il modello di default non supporta vision, andrebbe sovrascritto 
        # con un modello specifico (es. gpt-4-vision-preview o deepseek-janus)
        # Per ora usiamo il modello configurato assumendo endpoint compatibile.

    def analyze_image(self, image_b64: str, prompt: str = "Descrivi cosa vedi in questa interfaccia. Cerca vulnerabilità, form di login o versioni software.") -> str:
        """
        Invia immagine (b64) e prompt al modello vision.
        """
        from openai import OpenAI
        
        if not self.api_key:
            return "[VISION] Errore: API Key mancate."

        try:
            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            start_time = time.time()
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_b64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=500
            )
            
            duration = time.time() - start_time
            result = response.choices[0].message.content
            metrics_collector.track_llm_call(duration, True, self.model)
            
            return result

        except Exception as e:
            logger.error(f"Errore Vision API: {e}")
            return f"[VISION] Errore analisi: {str(e)}"

# Singleton
_vision_instance = VisionAnalyzer()

def analyze_screenshot(image_b64: str, prompt: str = None) -> str:
    return _vision_instance.analyze_image(image_b64, prompt) if prompt else _vision_instance.analyze_image(image_b64)
