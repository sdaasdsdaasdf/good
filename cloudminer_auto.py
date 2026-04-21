import asyncio
import re
import os
from pathlib import Path
from playwright.async_api import async_playwright

FILE_PATH = Path("mails.txt")
BASE_URL = os.environ.get("URL_SECRET", "").rstrip("/")

def load_accounts():
    accounts = []
    if not FILE_PATH.exists():
        print("❌ mails.txt not found!")
        return accounts
    with open(FILE_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "," in line:
                name, email = [x.strip() for x in line.split(",", 1)]
                accounts.append((name, email))
    return accounts

async def claim_for_account(page, email: str):
    print(f"\n🔄 Processing: {email}")
    try:
        await page.goto(f"{BASE_URL}/auth", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
        await page.locator("#email").fill(email)
        await page.locator("#password").fill(email)
        await page.get_by_role("button").filter(has_text=re.compile(r"Claim|Login|Sign in", re.I)).first.click()
        print("   ✅ Login clicked")
        await page.wait_for_timeout(4000)

        claim_btn = page.locator("button:has(svg.lucide-coins)").first
        try:
            await claim_btn.wait_for(state="visible", timeout=15000)
            await claim_btn.scroll_into_view_if_needed()
            await page.wait_for_timeout(1000)
            coin_text = await claim_btn.inner_text()
            await claim_btn.click()
            print(f"   ✅ Claim clicked: '{coin_text.strip()}'")
            await page.wait_for_timeout(4000)
        except Exception:
            print("   ⚠️  Primary selector failed, trying fallback scroll...")
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await page.wait_for_timeout(1000)
            fallback_btn = page.locator("button").filter(
                has_text=re.compile(r"Claim\s+\d+\s+coins", re.I)
            ).first
            if await fallback_btn.count() > 0:
                await fallback_btn.scroll_into_view_if_needed()
                await page.wait_for_timeout(500)
                await fallback_btn.click()
                print("   ✅ Claim clicked via fallback")
                await page.wait_for_timeout(4000)
            else:
                print("   ⚠️  Claim button not found, skipping...")

        available_coins_text = await page.locator("div.flex.items-center.justify-between").inner_text(timeout=8000)
        match = re.search(r"(\d[\d,]*)\s*coins", available_coins_text)
        if match:
            coins = int(match.group(1).replace(",", ""))
            print(f"   💰 Available Coins: {coins}")
            if coins > 0:
                max_btn = page.locator("button").filter(has_text="MAX").first
                if await max_btn.is_visible():
                    await max_btn.click()
                    print("   ✅ MAX button clicked")
                    await page.wait_for_timeout(1500)
                convert_btn = page.locator("button").filter(
                    has_text=re.compile(r"Convert to DOGE", re.I)
                ).first
                if await convert_btn.is_visible():
                    await convert_btn.click()
                    print("   ✅ Convert to DOGE clicked")
                    await page.wait_for_timeout(5000)
                else:
                    print("   ⚠️  Convert to DOGE button not found")
            else:
                print("   ⚠️  No coins available")
        else:
            print("   ⚠️  Could not read Available Coins")
    except Exception as e:
        print(f"   ❌ Error with {email}: {e}")

async def main():
    if not BASE_URL:
        print("❌ URL_SECRET environment variable is not set!")
        return
    accounts = load_accounts()
    if not accounts:
        return
    print(f"🌐 Target URL: {BASE_URL}")
    print(f"🚀 Starting automation for {len(accounts)} accounts...\n")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        for i, (name, email) in enumerate(accounts, 1):
            print(f"\n📍 Account {i}/{len(accounts)} — {name}")
            context = await browser.new_context()
            page = await context.new_page()
            await claim_for_account(page, email)
            await context.close()
            await asyncio.sleep(2)
        await browser.close()
    print("\n" + "=" * 70)
    print("🎉 ALL ACCOUNTS PROCESSED!")

if __name__ == "__main__":
    asyncio.run(main())
