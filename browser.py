import pathfix  # noqa — must be first

import asyncio
from playwright.async_api import async_playwright


async def fetch_with_browser(url: str, timeout: int = 25000) -> str:
    """Fetch a JS-rendered page with headless Chromium. Returns HTML or empty string."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page = await context.new_page()

        async def block_resources(route):
            if route.request.resource_type in ("image", "font", "media", "stylesheet"):
                await route.abort()
            else:
                await route.continue_()

        await page.route("**/*", block_resources)

        html = ""
        try:
            await page.goto(url, timeout=timeout, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            html = await page.content()
        except Exception as e:
            print(f"    Browser fetch failed: {type(e).__name__}: {e}")
        finally:
            await browser.close()

        return html


if __name__ == "__main__":
    async def test():
        print("Testing browser fetch on Chevening...")
        html = await fetch_with_browser("https://www.chevening.org/scholarships/")
        if html:
            print(f"SUCCESS — received {len(html):,} characters of HTML")
        else:
            print("FAILED — empty response")
    asyncio.run(test())
