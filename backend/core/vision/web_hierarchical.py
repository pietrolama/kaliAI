import logging
import shutil
from typing import Dict, Any
from backend.core.vision.browser_manager import browse_url
from backend.core.vision.vision_analyzer import analyze_screenshot
from backend.core.execution.python_sandbox import execute_python_sandboxed

logger = logging.getLogger('HierarchicalWeb')

class HierarchicalWebExplorer:
    """
    Gestisce l'esplorazione web a cascata (Waterfall).
    Efficienza > Costo Computazionale.
    """
    
    def explore_url(self, url: str) -> Dict[str, Any]:
        """
        Orchestra l'analisi a livelli:
        1. Light (Curl/Headers)
        2. Medium (Playwright Headless)
        3. Heavy (Vision AI)
        """
        if not url.startswith("http"):
            url = f"http://{url}"

        logger.info(f"[EYES] Inizio analisi gerarchica: {url}")
        
        # LEVEL 1: LIGHT (Curl)
        # Usiamo il sandbox bash/python per fare una richiesta leggera
        # Per semplicità qui usiamo requests in python sandboxato se possibile, 
        # o subprocess locale se autorizzato. Dato che siamo backend, usiamo requests diretto 
        # MA con timeout stretto.
        level1_data = self._level_1_light(url)
        
        if level1_data['status'] == 'success' and not self._needs_escalation(level1_data):
             return {
                 "level": 1,
                 "method": "light_fingerprint",
                 "data": level1_data
             }
        
        logger.info("[EYES] Level 1 insufficiente (JS detected/Auth required). Escalating to Level 2.")

        # LEVEL 2: MEDIUM (Playwright)
        # Usa il BrowserManager esistente
        level2_data = browse_url(url)
        
        if level2_data['status'] == 'error':
            return {"level": 2, "error": level2_data['error']}
            
        if not self._needs_visual_analysis(level2_data):
             return {
                 "level": 2,
                 "method": "headless_dom",
                 "data": level2_data
             }

        logger.info("[EYES] Level 2 insufficiente (Complex UI/Canvas/Obfuscation). Escalating to Level 3.")

        # LEVEL 3: HEAVY (Vision)
        # Usa VisionAnalyzer sullo screenshot catturato al livello 2
        vision_analysis = analyze_screenshot(level2_data['image'])
        
        return {
            "level": 3,
            "method": "vision_ai",
            "data": {
                **level2_data,
                "ai_analysis": vision_analysis
            }
        }

    def _level_1_light(self, url: str) -> Dict[str, Any]:
        """Esegue fingerprint leggero."""
        # TODO: Implementare check reale con requests/subprocess curl
        # Per ora stub: se risponde 200 e ha poco JS return success logic
        # Qui simuliamo che fallisca spesso sui target moderni per forzare Level 2
        return {"status": "needs_escalation"} 

    def _needs_escalation(self, data: Dict) -> bool:
        """Determina se serve il browser completo."""
        # Se non ho body o status != 200 -> escalate
        if data.get('status') != 'success': return True
        # Se trovo <script> complessi -> escalate
        return True 

    def _needs_visual_analysis(self, data: Dict) -> bool:
        """Determina se serve l'IA visiva."""
        # Logica euristica:
        # - HTML molto corto ma screenshot non bianco (es. Canvas app / React root)
        # - Form di login rilevati nel DOM
        # - Parole chiave "Captcha", "Challenge"
        html = data.get('html_snippet', "").lower()
        if "login" in html or "password" in html or "captcha" in html:
            return True
        if len(html) < 500: # DOM sospettosamente vuoto
            return True
        return False

# Singleton
_hierarchical_explorer = HierarchicalWebExplorer()

def intelligent_browse_tool(url: str) -> str:
    """
    Tool Esposto agli Agenti.
    Restituisce report completo usando la strategia più efficiente.
    """
    result = _hierarchical_explorer.explore_url(url)
    
    report = f"TARGET: {url}\n"
    report += f"ANALYSIS LEVEL: {result['level']} ({result.get('method')})\n"
    
    if result['level'] == 3:
         report += f"\n[VISION AI REPORT]\n{result['data']['ai_analysis']}\n"
    elif result['level'] == 2:
         report += f"\n[DOM EXTRACT]\nTitle: {result['data']['title']}\n"
    
    return report
