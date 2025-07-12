import asyncio
from playwright.async_api import async_playwright

async def test_browser():
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto('https://www.poundwholesale.co.uk', timeout=30000)
            print(f'Success: {page.url}')
            await browser.close()
    except Exception as e:
        print(f'Error: {e}')

if __name__ == "__main__":
    asyncio.run(test_browser())