#!/usr/bin/env python3
"""MAX login — passes captcha, reads SMS code from terminal stdin."""
import asyncio, json, time, random, os, sys
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

PHONE = "9105374969"

async def main():
    stealth = Stealth()
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-gpu","--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            viewport={"width":1280,"height":800},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36",
            locale="ru-RU", timezone_id="Europe/Moscow",
        )
        page = await ctx.new_page()
        await stealth.apply_stealth_async(page)
        
        print("1. Navigate...", flush=True)
        await page.goto("https://web.max.ru/", timeout=30000)
        await asyncio.sleep(8)
        
        for _ in range(3):
            await page.mouse.move(random.randint(100,1000), random.randint(100,600))
            await asyncio.sleep(random.uniform(0.1,0.3))
        
        print("2. Phone login...", flush=True)
        await page.locator('button:has-text("phone number")').click()
        await asyncio.sleep(3)
        
        print("3. Fill phone...", flush=True)
        inp = page.locator('input').first
        await inp.click()
        await asyncio.sleep(0.3)
        await inp.fill("")
        for d in PHONE:
            await inp.type(d, delay=random.randint(50,150))
        await asyncio.sleep(1)
        
        print("4. Continue...", flush=True)
        submit = page.locator('button[type="submit"]')
        box = await submit.bounding_box()
        tx, ty = box['x']+box['width']/2, box['y']+box['height']/2
        await page.mouse.move(random.randint(200,800), random.randint(200,500))
        for i in range(5):
            await page.mouse.move(
                random.randint(200,800)+(tx-random.randint(200,800))*(i+1)/5,
                random.randint(200,500)+(ty-random.randint(200,500))*(i+1)/5)
            await asyncio.sleep(random.uniform(0.05,0.15))
        await page.mouse.click(tx, ty)
        await asyncio.sleep(6)
        
        body = await page.evaluate("() => document.body.innerText.substring(0,200)")
        print(f"5. After submit: {body[:80]}", flush=True)
        
        if "robot" in body.lower():
            print("6. Solving captcha...", flush=True)
            for frame in page.frames:
                if "id.vk.ru" in frame.url or "not_robot" in frame.url:
                    cb = await frame.query_selector('input[type="checkbox"]')
                    if not cb:
                        els = await frame.query_selector_all('div,span,label,button')
                        for el in els:
                            if await el.is_visible():
                                b = await el.bounding_box()
                                if b and 20<b['width']<200 and 30<b['height']<60:
                                    cb = el; break
                    if cb:
                        b = await cb.bounding_box()
                        tx, ty = b['x']+b['width']/2, b['y']+b['height']/2
                        for i in range(8):
                            await page.mouse.move(
                                random.randint(100,1000)+(tx-random.randint(100,1000))*(i+1)/8,
                                random.randint(100,500)+(ty-random.randint(100,500))*(i+1)/8)
                            await asyncio.sleep(random.uniform(0.05,0.15))
                        await page.mouse.click(tx, ty)
                        await asyncio.sleep(8)
                        break
        
        body = await page.evaluate("() => document.body.innerText.substring(0,300)")
        print(f"7. After captcha: {body[:100]}", flush=True)
        
        if "Code sent" in body:
            print("\n" + "="*50, flush=True)
            print("CAPTCHA PASSED! SMS SENT!", flush=True)
            print("Check your phone for SMS code", flush=True)
            print("="*50, flush=True)
            print("\nEnter SMS code: ", end="", flush=True)
            
            # Read code from stdin — user types it in terminal
            code = sys.stdin.readline().strip()
            print(f"\nEntered: {code}", flush=True)
            print("Entering code into MAX...", flush=True)
            
            all_inp = page.locator('input')
            cnt = await all_inp.count()
            
            single = []
            for i in range(cnt):
                el = all_inp.nth(i)
                if await el.is_visible():
                    ml = await el.get_attribute("maxlength")
                    if ml == "1":
                        single.append(el)
            
            if len(single) >= 6:
                print(f"OTP: {len(single)} boxes", flush=True)
                for i, d in enumerate(code[:6]):
                    await single[i].click()
                    await asyncio.sleep(0.1)
                    await single[i].type(d, delay=50)
                    await asyncio.sleep(0.1)
            else:
                print("Single input", flush=True)
                for i in range(cnt):
                    el = all_inp.nth(i)
                    if await el.is_visible():
                        await el.click()
                        await asyncio.sleep(0.2)
                        for d in code:
                            await page.keyboard.type(d, delay=80)
                        break
            
            print("Waiting for login...", flush=True)
            await asyncio.sleep(10)
            await page.screenshot(path="screen_done.png")
            
            body = await page.evaluate("() => document.body.innerText.substring(0,500)")
            print(f"\n{'='*50}", flush=True)
            print(f"RESULT: {body[:300]}", flush=True)
            print(f"URL: {page.url}", flush=True)
            
            storage = await page.evaluate("""() => {
                const r = {};
                for (let i = 0; i < localStorage.length; i++) {
                    const k = localStorage.key(i);
                    r[k] = localStorage.getItem(k);
                }
                return r;
            }""")
            
            print(f"\nlocalStorage ({len(storage)} keys):", flush=True)
            for k, v in storage.items():
                print(f"  {k}: {v[:100]}", flush=True)
            
            with open("storage.json", "w") as f:
                json.dump(storage, f, indent=2, default=str)
            
            cookies = await ctx.cookies()
            with open("cookies.json", "w") as f:
                json.dump(cookies, f, indent=2, default=str)
            print(f"\nCookies: {len(cookies)}", flush=True)
            print("Saved: storage.json, cookies.json, screen_done.png", flush=True)
            
            if "Invalid" in body:
                print("\n❌ INVALID CODE", flush=True)
            elif "Code sent" in body:
                print("\n❌ Still on code page", flush=True)
            else:
                print("\n✅ LOGIN SUCCESS!", flush=True)
        else:
            print(f"ERROR: {body[:200]}", flush=True)
        
        await browser.close()

asyncio.run(main())
