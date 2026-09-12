import asyncio
import json
import time
import os
import urllib.request
import websockets
import subprocess

ARTIFACTS_DIR = "/home/davidalujones/.gemini/antigravity/brain/23f511ed-0b21-4a49-bbe3-0e7f15a457c4"

async def eval_js(ws, expr):
    req_id = int(time.time() * 1000) % 100000
    await ws.send(json.dumps({
        "id": req_id,
        "method": "Runtime.evaluate",
        "params": {
            "expression": expr,
            "returnByValue": True
        }
    }))
    while True:
        resp = await ws.recv()
        data = json.loads(resp)
        if data.get("id") == req_id:
            return data.get("result", {}).get("result", {}).get("value")

def capture_screen(filename):
    out_path = os.path.join(ARTIFACTS_DIR, filename)
    subprocess.run("adb -s 100.115.92.2:5555 shell input keyevent KEYCODE_WAKEUP", shell=True)
    subprocess.run(f"adb -s 100.115.92.2:5555 exec-out screencap -p > '{out_path}'", shell=True, check=True)
    print(f"Captured: {filename}")
    return out_path

async def main():
    with urllib.request.urlopen("http://127.0.0.1:9222/json") as r:
        pages = json.loads(r.read().decode())
    target = next(p for p in pages if "index.html" in p["url"])
    ws_url = target["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        # 1. Live Cyberpunk Theme
        print("1. Testing Live Cyberpunk Theme...")
        await eval_js(ws, "setTheme('theme-cyberpunk')")
        await asyncio.sleep(0.8)
        capture_screen("screen_live_cyberpunk.png")

        # 2. Live Gold Theme
        print("2. Testing Live Gold Theme...")
        await eval_js(ws, "setTheme('theme-gold')")
        await asyncio.sleep(0.8)
        capture_screen("screen_live_gold.png")

        # 3. Clean Offline Normal Empty State
        print("3. Testing Clean Offline Normal Empty State...")
        await eval_js(ws, "if (isServersRunning) toggleMasterPower()")
        await asyncio.sleep(0.8)
        capture_screen("screen_offline_empty_states.png")

        # Turn servers back on
        await eval_js(ws, "if (!isServersRunning) toggleMasterPower()")
        await asyncio.sleep(0.5)

        # 4. Run Genuine Speed Test
        print("4. Testing Network Speedometer...")
        await eval_js(ws, "selectTab('speed')")
        await asyncio.sleep(0.5)
        await eval_js(ws, "startSpeedTest()")
        await asyncio.sleep(1.8)
        capture_screen("screen_speedometer_live.png")

        # 5. Navigate to Web File Explorer & GalaxSee Gallery
        print("5. Testing Web File Explorer & GalaxSee Gallery...")
        await eval_js(ws, "window.location.href = 'file:///android_asset/www/file_manager.html'")
        await asyncio.sleep(1.2)

    # Re-connect to new page url
    await asyncio.sleep(0.5)
    with urllib.request.urlopen("http://127.0.0.1:9222/json") as r:
        pages = json.loads(r.read().decode())
    target = next(p for p in pages if "file_manager.html" in p["url"])
    ws_url = target["webSocketDebuggerUrl"]

    async with websockets.connect(ws_url) as ws:
        # Load GalaxSee Photos
        print("6. Viewing GalaxSee Photos...")
        await eval_js(ws, "setCategory('pictures')")
        await asyncio.sleep(2.0)
        capture_screen("screen_galaxsee_gallery.png")

        # 7. Open Right-Click Context Menu on Photo Card
        print("7. Opening Right-Click Context Menu...")
        await eval_js(ws, """
            const card = document.querySelector('.file-card');
            if (allData && allData.files && allData.files.length > 0) {
                openContextMenu({ clientX: 380, clientY: 450, preventDefault: ()=>{}, stopPropagation: ()=>{} }, allData.files[0]);
            }
        """)
        await asyncio.sleep(1.0)
        capture_screen("screen_galaxsee_context_menu.png")

        # 8. Click 'Set photo as desktop wallpaper'
        print("8. Clicking Set photo as desktop wallpaper...")
        await eval_js(ws, "onContextSetWallpaper()")
        await asyncio.sleep(1.0)
        capture_screen("screen_wallpaper_toast.png")

        # 9. Test In-Browser Lightbox with 'Set as Wallpaper' button
        print("9. Testing Image Lightbox with Set as Wallpaper button...")
        await eval_js(ws, """
            if (allData && allData.files && allData.files.length > 0) {
                const f = allData.files[0];
                openPreview(f.name, '/api/files/preview?path=' + encodeURIComponent(f.path), 'image', f);
            }
        """)
        await asyncio.sleep(1.0)
        capture_screen("screen_lightbox_wallpaper_btn.png")

    print("All UI verification tests completed successfully!")

asyncio.run(main())
