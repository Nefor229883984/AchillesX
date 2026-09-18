#!/usr/bin/env python3
"""MAX login via GitHub Actions — uses GitHub API for communication."""
import asyncio, json, time, random, os, base64, requests
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

PAT = os.environ.get("GIT_TOKEN", "")
REPO = "Nefor229883984/AchillesX"
PHONE = "9105374969"

def api_upload(filename, content, msg):
    """Upload file to repo via GitHub API."""
    b64 = base64.b64encode(content.encode()).decode()
    # Check if file exists
    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{filename}",
                     headers={"Authorization": f"token {PAT}"})
    sha = r.json().get("sha") if r.status_code == 200 else None
    data = {"message": msg, "content": b64}
    if sha:
        data["sha"] = sha
    r2 = requests.put(f"https://api.github.com/repos/{REPO}/contents/{filename}",
                      headers={"Authorization": f"token {PAT}", "Content-Type": "application/json"},
                      json=data)
    print(f"  Upload {filename}: {r2.status_code}", flush=True)

def api_download(filename):
    """Download file from repo via GitHub API."""
    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{filename}",
                     headers={"Authorization": f"token {PAT}"})
    if r.status_code == 200:
        return base64.b64decode(r.json()["content"]).decode()
    return None

def api_delete(filename):
    """Delete file from repo."""
    r = requests.get(f"https://api.github.com/repos/{REPO}/contents/{filename}",
                     headers={"Authorization": f"token {PAT}"})
    if r.status_code == 200:
        sha = r.json()["sha"]
        requests.delete(f"https://api.github.com/repos/{REPO}/contents/{filename}",
                       headers={"Authorization": f"token {PAT}", "Content-Type": "application/json"},
                       json={"message": "delete", "sha": sha})

def write_state(state, msg=""):
    content = json.dumps({"state": state, "msg": msg, "ts": time.time()})
    api_upload("login_state.json", content, f"state: {state}")
    print(f"[{state}] {msg}", flush=True)

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

        write_state("navigate", "Loading web.max.ru...")
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
        write_state("after_submit", body[:100])

        if "robot" in body.lower():
            write_state("captcha", "Solving VK captcha...")
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
            write_state("WAITING_CODE", f"SMS sent! Device: {device_id}")

            # Poll for code via GitHub API
            start = time.time()
            code = None
            while time.time() - start < 240:
                code_data = api_download("sms_code.txt")
                if code_data and len(code_data.strip()) >= 4:
                    code = code_data.strip()
                    api_delete("sms_code.txt")
                    break
                await asyncio.sleep(3)

            if not code:
                write_state("TIMEOUT", "No code in 4 min")
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
            await page.screenshot(path="screen_done.png")

            body = await page.evaluate("() => document.body.innerText.substring(0,500)")
            storage = await page.evaluate("""() => {
                const r = {};
                for (let i = 0; i < localStorage.length; i++) {
                    r[localStorage.key(i)] = localStorage.getItem(localStorage.key(i));
                }
                return r;
            }""")
            cookies = await ctx.cookies()

            api_upload("storage.json", json.dumps(storage, indent=2, default=str), "storage")
            api_upload("cookies.json", json.dumps(cookies, indent=2, default=str), "cookies")

            if "Invalid" in body:
                write_state("INVALID", "Code expired")
            elif "Code sent" in body:
                write_state("FAILED", "Still on code page")
            else:
                write_state("SUCCESS", f"Logged in! {body[:200]}")
        else:
            write_state("ERROR", body[:200])

        await browser.close()

asyncio.run(main())
