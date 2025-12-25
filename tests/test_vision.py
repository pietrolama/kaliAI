
import asyncio
from backend.core.vision.browser_manager import BrowserManager

async def test_vision():
    print("Testing Generic Vision (Playwright)...")
    bm = BrowserManager(headless=True)
    # Usa un sito semplice che non cambia molto
    res = await bm.capture_page("https://example.com")
    
    if res['status'] == 'success':
        print(f"✅ Successo! Titolo: {res['title']}")
        print(f"📸 Screenshot salvato in: {res['image_path']}")
        print(f"📝 HTML length: {len(res['html_snippet'])}")
    else:
        print(f"❌ Errore: {res['error']}")

if __name__ == "__main__":
    asyncio.run(test_vision())
