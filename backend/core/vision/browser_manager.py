import os
import asyncio
import logging
from playwright.async_api import async_playwright
import base64

logger = logging.getLogger('BrowserManager')

class BrowserManager:
    """
    Gestisce l'automazione browser (The Eyes).
    Usa Playwright per navigare, fare screenshot e estrarre DOM.
    """
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.output_dir = os.path.join(os.getcwd(), "static", "vision_cache")
        os.makedirs(self.output_dir, exist_ok=True)

    async def capture_page(self, url: str) -> dict:
        """
        Naviga a un URL e cattura:
        - Screenshot (base64)
        - HTML Content
        - Titolo
        """
        async with async_playwright() as p:
            # Lancia browser (Chromium)
            browser = await p.chromium.launch(headless=self.headless, args=['--no-sandbox'])
            context = await browser.new_context(
                viewport={'width': 1280, 'height': 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()

            try:
                logger.info(f"Navigazione a: {url}")
                await page.goto(url, timeout=30000, wait_until="networkidle")
                
                # Cattura dati
                title = await page.title()
                content = await page.content()
                screenshot_bytes = await page.screenshot(type='jpeg', quality=80)
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                # Salva file per debug locale
                filename = f"capture_{base64.urlsafe_b64encode(url.encode()).decode()[:10]}.jpg"
                with open(os.path.join(self.output_dir, filename), "wb") as f:
                    f.write(screenshot_bytes)

                return {
                    "status": "success",
                    "url": url,
                    "title": title,
                    "image": screenshot_b64,
                    "html_snippet": content[:5000],  # Primi 5k char per RAG 
                    "image_path": os.path.join("vision_cache", filename)
                }

            except Exception as e:
                logger.error(f"Errore navigazione: {e}")
                return {
                    "status": "error",
                    "url": url,
                    "error": str(e)
                }
            finally:
                await browser.close()

# Wrapper sincrono per l'integrazione con tool esistenti
def browse_url(url: str):
    return asyncio.run(BrowserManager().capture_page(url))
