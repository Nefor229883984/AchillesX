#!/usr/bin/env python3
"""Run in GitHub Codespace — fresh IP, VK captcha will pass!"""
import asyncio, json, time, random, os, subprocess

async def main():
    # Install deps
    subprocess.run(["pip", "install", "playwright", "playwright-stealth"], check=True)
    subprocess.run(["npx", "playwright", "install", "chromium"], check=True)
    
    from playwright.async_api import async_playwright
    from playwright_stealth import Stealth
    
    PHONE = "9105374969"
    
    def git_save(filename, content, msg):
        with open(filename, "w") as f:
            f.write(content)
        subprocess.run(["git", "add", filename], capture_output=True)
        subprocess.run(["git", "commit", "-m", msg], capture_output=True)
        subprocess.run(["git", "push"], capture_output=True)
    
    def git_pull():
        subprocess.run(["git", "pull"], capture_output=True)
    
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
        
        git_save("login_state.json", json.dumps({"state":"navigate","ts":time.time()}), "navigate")
        await page.goto("https://web.max.ru/", timeout=30000)
        await asyncio.sleep(8)
        
        for _ in range(3):
            await page.mouse.move(random.randint(100,1000), random.randint(100,600))
            await asyncio.sleep(random.uniform(0.1,0.3))
        
        await page.locator('button:has-text("phone number")').click()
        await asyncio.sleep(3)
        
        inp = page.locator('input').first
        await inp.click()
        await asyncio.sleep(0.3)
        await inp.fill("")
        for d in PHONE:
            await inp.type(d, delay=random.randint(50,150))
        await asyncio.sleep(1)
        
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
            git_save("login_state.json", json.dumps({"state":"captcha","ts":time.time()}), "captcha")
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
        
        if "Code sent" in body:
            storage = await page.evaluate("""() => {
                const r = {};
                for (let i = 0; i < localStorage.length; i++) {
                    r[localStorage.key(i)] = localStorage.getItem(localStorage.key(i));
                }
                return r;
            }""")
            device_id = storage.get("__oneme_device_id", "")
            
            git_save("login_state.json", json.dumps({
                "state":"WAITING_CODE",
                "device_id": device_id,
                "phone": PHONE,
                "msg": "SMS sent from Codespace! Waiting for code in sms_code.txt",
                "ts": time.time()
            }), "WAITING_CODE — SMS sent!")
            
            # Poll for code via git pull
            start = time.time()
            code = None
            while time.time() - start < 300:
                git_pull()
                if os.path.exists("sms_code.txt"):
                    with open("sms_code.txt") as f:
                        code = f.read().strip()
                    if code and len(code) >= 4:
                        subprocess.run(["rm", "sms_code.txt"])
                        subprocess.run(["git", "add", "-A"], capture_output=True)
                        subprocess.run(["git", "commit", "-m", "consumed"], capture_output=True)
                        subprocess.run(["git", "push"], capture_output=True)
                        break
                await asyncio.sleep(3)
            
            if not code:
                git_save("login_state.json", json.dumps({"state":"TIMEOUT","ts":time.time()}), "timeout")
                await browser.close()
                return
            
            git_save("login_state.json", json.dumps({"state":"entering","code":code,"ts":time.time()}), f"entering {code}")
            
            # Enter code
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
            await page.screenshot(path="screen_done.png")
            subprocess.run(["git", "add", "screen_done.png"], capture_output=True)
            
            body = await page.evaluate("() => document.body.innerText.substring(0,500)")
            storage = await page.evaluate("""() => {
                const r = {};
                for (let i = 0; i < localStorage.length; i++) {
                    r[localStorage.key(i)] = localStorage.getItem(localStorage.key(i));
                }
                return r;
            }""")
            cookies = await ctx.cookies()
            
            git_save("storage.json", json.dumps(storage, indent=2, default=str), "storage")
            git_save("cookies.json", json.dumps(cookies, indent=2, default=str), "cookies")
            
            if "Invalid" in body:
                git_save("login_state.json", json.dumps({"state":"INVALID","ts":time.time()}), "invalid")
            elif "Code sent" in body:
                git_save("login_state.json", json.dumps({"state":"FAILED","ts":time.time()}), "failed")
            else:
                git_save("login_state.json", json.dumps({"state":"SUCCESS","msg":body[:200],"ts":time.time()}), "SUCCESS!")
        else:
            git_save("login_state.json", json.dumps({"state":"ERROR","msg":body[:200],"ts":time.time()}), "error")
        
        await browser.close()

asyncio.run(main())
