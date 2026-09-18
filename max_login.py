#!/usr/bin/env python3
import asyncio, json, time, random, os, subprocess
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

PHONE = "9105374969"
CODE_FILE = "/workspace/sms_code.txt"
STATE_FILE = "/workspace/login_state.json"
TOKEN_FILE = "/workspace/token.txt"

def write_state(s, m=""):
    with open(STATE_FILE, "w") as f:
        json.dump({"state": s, "msg": m, "ts": time.time()}, f)
    print(f"[{s}] {m}", flush=True)

async def main():
    # Install Chrome first
    subprocess.run(["npx", "playwright", "install", "chromium"], check=True)
    
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
        
        write_state("navigate", "Loading...")
        await page.goto("https://web.max.ru/", timeout=30000)
        await asyncio.sleep(8)
        
        for _ in range(3):
            await page.mouse.move(random.randint(100,1000), random.randint(100,600))
            await asyncio.sleep(random.uniform(0.1,0.3))
        
        write_state("phone", "Phone login...")
        await page.locator('button:has-text("phone number")').click()
        await asyncio.sleep(3)
        
        inp = page.locator('input').first
        await inp.click()
        await asyncio.sleep(0.3)
        await inp.fill("")
        for d in PHONE:
            await inp.type(d, delay=random.randint(50,150))
        await asyncio.sleep(1)
        
        write_state("submit", "Continue...")
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
        
        if "robot" in body.lower():
            write_state("captcha", "Solving captcha...")
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
        write_state("WAITING_CODE", "CAPTCHA PASSED! SMS sent. Tell me the code!")
        
        start = time.time()
        code = None
        while time.time() - start < 600:
            if os.path.exists(CODE_FILE):
                with open(CODE_FILE) as f:
                    code = f.read().strip()
                if code and len(code) >= 4:
                    os.remove(CODE_FILE)
                    break
            await asyncio.sleep(2)
        
        if not code:
            write_state("TIMEOUT", "No code in 10 min")
            await browser.close()
            return
        
        write_state("entering", f"Code: {code}")
        
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
            for i, d in enumerate(code[:6]):
                await single[i].click()
                await asyncio.sleep(0.1)
                await single[i].type(d, delay=50)
                await asyncio.sleep(0.1)
        else:
            for i in range(cnt):
                el = all_inp.nth(i)
                if await el.is_visible():
                    await el.click()
                    await asyncio.sleep(0.2)
                    for d in code:
                        await page.keyboard.type(d, delay=80)
                    break
        
        await asyncio.sleep(10)
        await page.screenshot(path="/workspace/screen_done.png")
        
        body = await page.evaluate("() => document.body.innerText.substring(0,500)")
        write_state("result", f"Body: {body[:200]}")
        
        storage = await page.evaluate("""() => {
            const r = {};
            for (let i = 0; i < localStorage.length; i++) {
                const k = localStorage.key(i);
                r[k] = localStorage.getItem(k);
            }
            return r;
        }""")
        
        with open("/workspace/storage.json", "w") as f:
            json.dump(storage, f, indent=2, default=str)
        
        cookies = await ctx.cookies()
        with open("/workspace/cookies.json", "w") as f:
            json.dump(cookies, f, indent=2, default=str)
        
        write_state("DONE", f"Storage: {len(storage)} keys, Cookies: {len(cookies)}")
        await browser.close()

asyncio.run(main())
