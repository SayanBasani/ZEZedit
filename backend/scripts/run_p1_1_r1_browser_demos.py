"""P1.1-R1 Comprehensive Real-Browser Upload Demonstrator.

Executes all 5 mandatory real-browser upload demonstrations against Google Chrome via CDP:
- Demo 1: Single upload through real browser UI -> dashboard navigation -> library check
- Demo 2: 3-file batch upload in one file selection -> 3 distinct IDs, files, DB rows, and dashboards
- Demo 3: Mixed-validity batch upload (1 valid, 1 invalid) -> UI error banner & partial persistence
- Demo 4: Repeated upload of identical filename -> non-destructive collision & dual persistence
- Demo 5: Mobile-width viewport emulation (375x812) -> responsive layout & usable mobile upload
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
import websockets

PROJECT_ROOT = Path("D:/ZezEdit")
EVIDENCE_DIR = PROJECT_ROOT / "docs" / "reports" / "priority_1" / "p1_1_r1_evidence"
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
EVIDENCE_FILE = EVIDENCE_DIR / "p1_1_r1_evidence.json"
DB_PATH = PROJECT_ROOT / "storage" / "db" / "zezedit.db"

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
DEMO_FILES_DIR = PROJECT_ROOT / "storage" / "temp" / "browser_demo_files"
DEMO_FILES_DIR.mkdir(parents=True, exist_ok=True)


def create_synthetic_mp4(out_path: Path, duration: int = 1, width: int = 320, height: int = 240, fps: int = 25):
    ffmpeg = shutil.which("ffmpeg") or "ffmpeg"
    cmd = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", f"testsrc=duration={duration}:size={width}x{height}:rate={fps}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        str(out_path),
    ]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)


class CDPBrowser:
    def __init__(self, ws_url: str):
        self.ws_url = ws_url
        self.ws = None
        self.msg_id = 0
        self.pending_requests = {}
        self.network_requests = {}
        self.network_responses = {}
        self.response_bodies = {}
        self.console_logs = []
        self._listener_task = None

    async def connect(self):
        self.ws = await websockets.connect(self.ws_url, max_size=50 * 1024 * 1024)
        self._listener_task = asyncio.create_task(self._listen())
        await self.send("Page.enable")
        await self.send("DOM.enable")
        await self.send("Runtime.enable")
        await self.send("Network.enable")

    async def _listen(self):
        try:
            while True:
                raw = await self.ws.recv()
                msg = json.loads(raw)

                # Check if it's a response to a command
                if "id" in msg:
                    fut = self.pending_requests.pop(msg["id"], None)
                    if fut and not fut.done():
                        if "error" in msg:
                            fut.set_exception(RuntimeError(f"CDP Error: {msg['error']}"))
                        else:
                            fut.set_result(msg.get("result", {}))
                    continue

                method = msg.get("method")
                params = msg.get("params", {})

                if method == "Network.requestWillBeSent":
                    req_id = params.get("requestId")
                    req = params.get("request", {})
                    self.network_requests[req_id] = {
                        "url": req.get("url"),
                        "method": req.get("method"),
                        "headers": req.get("headers"),
                        "timestamp": params.get("timestamp"),
                    }
                elif method == "Network.responseReceived":
                    req_id = params.get("requestId")
                    res = params.get("response", {})
                    self.network_responses[req_id] = {
                        "url": res.get("url"),
                        "status": res.get("status"),
                        "statusText": res.get("statusText"),
                        "headers": res.get("headers"),
                        "mimeType": res.get("mimeType"),
                    }
                elif method == "Runtime.consoleAPICalled":
                    self.console_logs.append({
                        "type": params.get("type"),
                        "text": " ".join(str(a.get("value", a.get("description", ""))) for a in params.get("args", [])),
                    })
                elif method == "Runtime.exceptionThrown":
                    exp = params.get("exceptionDetails", {})
                    self.console_logs.append({
                        "type": "error",
                        "text": exp.get("text", "") + " " + str(exp.get("exception", {}).get("description", "")),
                    })
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[CDP Listener] Exception: {e}", file=sys.stderr)

    async def send(self, method: str, params: dict = None) -> dict:
        self.msg_id += 1
        curr_id = self.msg_id
        payload = {"id": curr_id, "method": method}
        if params is not None:
            payload["params"] = params

        loop = asyncio.get_running_loop()
        fut = loop.create_future()
        self.pending_requests[curr_id] = fut
        await self.ws.send(json.dumps(payload))
        return await fut

    async def evaluate(self, expr: str):
        res = await self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
        return res.get("result", {}).get("value")

    async def wait_for_condition(self, expr: str, timeout: float = 15.0, poll: float = 0.2):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                val = await self.evaluate(expr)
                if val:
                    return val
            except Exception:
                pass
            await asyncio.sleep(poll)
        raise TimeoutError(f"Condition '{expr}' not met within {timeout}s")

    async def capture_screenshot(self, filename: str) -> Path:
        out_path = EVIDENCE_DIR / filename
        res = await self.send("Page.captureScreenshot", {"format": "png"})
        b64_data = res.get("data")
        raw_bytes = base64.b64decode(b64_data)
        out_path.write_bytes(raw_bytes)
        print(f"  [Screenshot] Saved: {out_path.name} ({len(raw_bytes)} bytes)")
        return out_path

    async def set_file_input(self, selector: str, file_paths: list[str]):
        doc = await self.send("DOM.getDocument")
        root_id = doc["root"]["nodeId"]
        node = await self.send("DOM.querySelector", {"nodeId": root_id, "selector": selector})
        node_id = node.get("nodeId")
        if not node_id:
            raise RuntimeError(f"Could not find DOM node for selector: {selector}")
        await self.send("DOM.setFileInputFiles", {"nodeId": node_id, "files": [str(p) for p in file_paths]})

    async def close(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self.ws:
            await self.ws.close()


async def run_demos():
    print("=" * 75)
    print("ZEZEdit 2.0 — P1.1-R1 Real Browser Upload Demonstrations")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 75)

    # 1. Prepare synthetic media files
    print("\n[Phase 1] Preparing synthetic test videos in storage/temp/browser_demo_files/...")
    d1_file = DEMO_FILES_DIR / "browser_demo1_single.mp4"
    d2_a = DEMO_FILES_DIR / "browser_demo2_a.mp4"
    d2_b = DEMO_FILES_DIR / "browser_demo2_b.mp4"
    d2_c = DEMO_FILES_DIR / "browser_demo2_c.mp4"
    d3_valid = DEMO_FILES_DIR / "browser_demo3_valid.mp4"
    d3_corrupt = DEMO_FILES_DIR / "browser_demo3_corrupt.txt"
    d4_repeat1 = DEMO_FILES_DIR / "browser_demo4_repeat.mp4"
    d4_repeat2_source = DEMO_FILES_DIR / "browser_demo4_repeat_v2_source.mp4"
    d5_mobile = DEMO_FILES_DIR / "browser_demo5_mobile.mp4"

    create_synthetic_mp4(d1_file, duration=2, width=320, height=240, fps=25)
    create_synthetic_mp4(d2_a, duration=1, width=320, height=240, fps=25)
    create_synthetic_mp4(d2_b, duration=1, width=320, height=240, fps=25)
    create_synthetic_mp4(d2_c, duration=1, width=320, height=240, fps=25)
    create_synthetic_mp4(d3_valid, duration=1, width=320, height=240, fps=25)
    d3_corrupt.write_text("INVALID_TEXT_CONTENT_NOT_A_VIDEO")
    create_synthetic_mp4(d4_repeat1, duration=1, width=320, height=240, fps=25)
    create_synthetic_mp4(d4_repeat2_source, duration=3, width=320, height=240, fps=25)
    create_synthetic_mp4(d5_mobile, duration=1, width=320, height=240, fps=25)
    print("Synthetic test videos successfully created.")

    # 2. Launch Google Chrome in headless CDP mode
    print("\n[Phase 2] Launching Google Chrome via Chrome DevTools Protocol...")
    chrome_port = 9224
    chrome_proc = subprocess.Popen([
        CHROME_PATH,
        "--headless=new",
        f"--remote-debugging-port={chrome_port}",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1280,800",
        "about:blank",
    ])

    try:
        tabs = None
        for _ in range(25):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{chrome_port}/json") as r:
                    tabs = json.loads(r.read())
                    break
            except Exception:
                time.sleep(0.2)
        if not tabs:
            raise RuntimeError(f"Chrome failed to open CDP on port {chrome_port}")

        ws_url = tabs[0]["webSocketDebuggerUrl"]
        browser = CDPBrowser(ws_url)
        await browser.connect()
        print("Connected to Chrome CDP WebSocket.")

        evidence = {}

        # -------------------------------------------------------------
        # DEMO 1: Single Upload Through Browser
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print("DEMO 1: Single Upload Through Real Browser UI")
        print("=" * 60)

        await browser.send("Page.navigate", {"url": "http://127.0.0.1:8000/videos"})
        await browser.wait_for_condition("Boolean(document.querySelector('input[type=\"file\"]'))", timeout=15)
        await asyncio.sleep(1.0)

        # Pre-upload screenshot
        s1_pre = await browser.capture_screenshot("demo1_01_pre_upload.png")

        # Set single file on file input
        print(f"Setting input file: {d1_file.name} ({d1_file.stat().st_size} bytes)")
        t0 = time.time()
        await browser.set_file_input("input[type=\"file\"]", [str(d1_file)])

        # Wait for auto-navigation to /videos/med_...
        print("Waiting for upload request and dashboard navigation...")
        await browser.wait_for_condition("window.location.pathname.startsWith('/videos/med_')", timeout=20)
        curr_url = await browser.evaluate("window.location.pathname")
        med_id_1 = curr_url.split("/")[-1]
        print(f"Navigated to Video Edit Dashboard: {curr_url} (ID: {med_id_1})")

        # Wait for technical specs table or dashboard to render
        body_txt = ""
        for i in range(25):
            body_txt = await browser.evaluate("document.body.innerText") or ""
            if "Technical Video Specifications" in body_txt or "Duration" in body_txt or "Resolution" in body_txt:
                print("Dashboard content loaded successfully.")
                break
            print(f"  [Dashboard Wait {i}s] Body text snippet: {repr(body_txt[:80])}")
            await asyncio.sleep(1.0)

        s1_dash = await browser.capture_screenshot("demo1_02_dashboard.png")

        # Verify DB row
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row1 = conn.execute("SELECT * FROM media_assets WHERE id = ?", (med_id_1,)).fetchone()
            assert row1 is not None, f"Database row for {med_id_1} not found"
            assert row1["original_filename"] == "browser_demo1_single.mp4"
            assert row1["width"] == 320 and row1["height"] == 240
            assert row1["media_type"] == "video"

        # Verify physical file
        phys_path_1 = Path(row1["storage_path"])
        assert phys_path_1.exists(), f"Physical file {phys_path_1} does not exist"
        assert phys_path_1.stat().st_size == d1_file.stat().st_size

        # Navigate back to /videos to verify card in library
        await browser.send("Page.navigate", {"url": "http://127.0.0.1:8000/videos"})
        await browser.wait_for_condition(f"document.body.innerText.includes('browser_demo1_single.mp4')", timeout=15)
        await asyncio.sleep(1.0)
        s1_lib = await browser.capture_screenshot("demo1_03_library_card.png")

        evidence["DEMO_1_SINGLE_UPLOAD"] = {
            "status": "PASS",
            "media_id": med_id_1,
            "url": curr_url,
            "filename": d1_file.name,
            "file_size": d1_file.stat().st_size,
            "storage_path": str(phys_path_1),
            "physical_file_exists": phys_path_1.exists(),
            "db_record": dict(row1),
            "screenshots": [s1_pre.name, s1_dash.name, s1_lib.name],
        }
        print("DEMO 1: PASS")

        # -------------------------------------------------------------
        # DEMO 2: Three-File Batch Upload Through Browser
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print("DEMO 2: Three-File Batch Upload in One Selection")
        print("=" * 60)

        await browser.send("Page.navigate", {"url": "http://127.0.0.1:8000/videos"})
        await browser.wait_for_condition("Boolean(document.querySelector('input[type=\"file\"]'))", timeout=15)
        await asyncio.sleep(1.0)

        s2_pre = await browser.capture_screenshot("demo2_01_pre_batch.png")

        batch_files = [str(d2_a), str(d2_b), str(d2_c)]
        print(f"Setting 3 files in input: {[p.name for p in [d2_a, d2_b, d2_c]]}")
        await browser.set_file_input("input[type=\"file\"]", batch_files)

        # Wait for batch completion text or all 3 items to appear in library
        print("Waiting for batch upload to complete...")
        await browser.wait_for_condition(
            "document.body.innerText.includes('browser_demo2_a.mp4') && "
            "document.body.innerText.includes('browser_demo2_b.mp4') && "
            "document.body.innerText.includes('browser_demo2_c.mp4')",
            timeout=25,
        )
        await asyncio.sleep(1.0)
        s2_lib = await browser.capture_screenshot("demo2_02_library_all_three.png")

        # Query database for all 3
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            rows2 = conn.execute(
                "SELECT id, original_filename, storage_path, file_size_bytes FROM media_assets "
                "WHERE original_filename IN ('browser_demo2_a.mp4', 'browser_demo2_b.mp4', 'browser_demo2_c.mp4') "
                "ORDER BY created_at DESC LIMIT 3"
            ).fetchall()

        assert len(rows2) == 3, f"Expected 3 records in DB, found {len(rows2)}"
        med_ids_2 = [r["id"] for r in rows2]
        paths_2 = [Path(r["storage_path"]) for r in rows2]

        assert len(set(med_ids_2)) == 3, "All 3 media IDs must be distinct"
        assert len(set(paths_2)) == 3, "All 3 storage paths must be distinct"
        for p in paths_2:
            assert p.exists(), f"Physical file {p} must exist"

        # Open each dashboard and verify
        demo2_dashboards = []
        for r in rows2:
            mid = r["id"]
            fname = r["original_filename"]
            print(f"Opening dashboard for {fname} ({mid})...")
            clicked = await browser.evaluate(f"""(() => {{
                const cards = Array.from(document.querySelectorAll('div.rounded-2xl, div[class*="Card"]'));
                for (const c of cards) {{
                    if (c.innerText && c.innerText.includes('{fname}')) {{
                        const btn = Array.from(c.querySelectorAll('button')).find(b => b.innerText.includes('Open Video Dashboard'));
                        if (btn) {{
                            btn.click();
                            return true;
                        }}
                    }}
                }}
                const allBtns = Array.from(document.querySelectorAll('button')).filter(b => b.innerText.includes('Open Video Dashboard'));
                for (const b of allBtns) {{
                    let p = b.parentElement;
                    while (p && p !== document.body) {{
                        if (p.innerText && p.innerText.includes('{fname}')) {{
                            b.click();
                            return true;
                        }}
                        p = p.parentElement;
                    }}
                }}
                return false;
            }})()""")
            assert clicked, f"Could not find or click Open Video Dashboard button for {fname}"
            await browser.wait_for_condition("document.body.innerText.includes('Technical Video Specifications') || window.location.pathname.startsWith('/videos/med_')", timeout=15)
            await asyncio.sleep(0.5)
            s_dash = await browser.capture_screenshot(f"demo2_03_dashboard_{mid}.png")
            demo2_dashboards.append({"id": mid, "filename": fname, "screenshot": s_dash.name})

            # Click Return to Video Library
            print(f"Returning to video library from dashboard {mid}...")
            backed = await browser.evaluate("""(() => {
                const back = document.querySelector('button[title="Return to Video Library"]') ||
                             Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Back to Video Library'));
                if (back) {
                    back.click();
                    return true;
                }
                return false;
            })()""")
            assert backed, "Could not find or click Return to Video Library button"
            await browser.wait_for_condition("Boolean(document.querySelector('input[type=\"file\"]'))", timeout=15)
            await asyncio.sleep(0.5)

        evidence["DEMO_2_BATCH_UPLOAD"] = {
            "status": "PASS",
            "batch_count": 3,
            "media_ids": med_ids_2,
            "physical_paths": [str(p) for p in paths_2],
            "all_physical_files_exist": all(p.exists() for p in paths_2),
            "db_records": [dict(r) for r in rows2],
            "dashboards": demo2_dashboards,
            "screenshots": [s2_pre.name, s2_lib.name] + [d["screenshot"] for d in demo2_dashboards],
        }
        print("DEMO 2: PASS")

        # -------------------------------------------------------------
        # DEMO 3: Mixed-Validity Batch Through Browser
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print("DEMO 3: Mixed-Validity Batch (1 Valid, 1 Corrupt/Invalid)")
        print("=" * 60)

        await browser.send("Page.navigate", {"url": "http://127.0.0.1:8000/videos"})
        await browser.wait_for_condition("Boolean(document.querySelector('input[type=\"file\"]'))", timeout=15)
        await asyncio.sleep(1.0)

        s3_pre = await browser.capture_screenshot("demo3_01_pre_mixed.png")

        mixed_files = [str(d3_valid), str(d3_corrupt)]
        print(f"Setting mixed files in input: {[p.name for p in [d3_valid, d3_corrupt]]}")
        await browser.set_file_input("input[type=\"file\"]", mixed_files)

        # Wait for error reporting banner in the UI
        print("Waiting for batch processing and error banner...")
        await browser.wait_for_condition(
            "document.body.innerText.includes('Batch completed') || document.body.innerText.includes('failed')",
            timeout=20,
        )
        await asyncio.sleep(1.0)
        s3_post = await browser.capture_screenshot("demo3_02_error_banner.png")

        # Verify DB: valid file exists, corrupt file does NOT exist
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            r_valid = conn.execute(
                "SELECT * FROM media_assets WHERE original_filename = 'browser_demo3_valid.mp4' ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
            r_corrupt = conn.execute(
                "SELECT * FROM media_assets WHERE original_filename = 'browser_demo3_invalid.txt' OR original_filename LIKE '%corrupt%'"
            ).fetchall()

        assert r_valid is not None, "Valid video must be persisted in database"
        assert len(r_corrupt) == 0, "No database record must exist for invalid file"
        p_valid = Path(r_valid["storage_path"])
        assert p_valid.exists(), "Valid video file must exist on disk"

        evidence["DEMO_3_MIXED_VALIDITY"] = {
            "status": "PASS",
            "valid_media_id": r_valid["id"],
            "valid_storage_path": str(p_valid),
            "valid_file_exists": p_valid.exists(),
            "invalid_db_records_count": len(r_corrupt),
            "screenshots": [s3_pre.name, s3_post.name],
        }
        print("DEMO 3: PASS")

        # -------------------------------------------------------------
        # DEMO 4: Repeated Browser Upload (Same Filename, Non-Destructive)
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print("DEMO 4: Repeated Browser Upload of Identical Filename")
        print("=" * 60)

        # Upload first file
        await browser.send("Page.navigate", {"url": "http://127.0.0.1:8000/videos"})
        await browser.wait_for_condition("Boolean(document.querySelector('input[type=\"file\"]'))", timeout=15)
        await asyncio.sleep(0.5)

        s4_pre = await browser.capture_screenshot("demo4_01_pre_repeat.png")
        print(f"Uploading first instance: {d4_repeat1.name} (1s duration, {d4_repeat1.stat().st_size} bytes)")
        await browser.set_file_input("input[type=\"file\"]", [str(d4_repeat1)])

        # Wait for auto-navigation to dashboard
        await browser.wait_for_condition("window.location.pathname.startsWith('/videos/med_')", timeout=20)
        url_rep_1 = await browser.evaluate("window.location.pathname")
        med_rep_1 = url_rep_1.split("/")[-1]
        print(f"First upload navigated to: {url_rep_1} (ID: {med_rep_1})")

        # Return to library
        print("Returning to library from first upload...")
        backed1 = await browser.evaluate("""(() => {
            const back = document.querySelector('button[title="Return to Video Library"]') ||
                         Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Back to Video Library'));
            if (back) {
                back.click();
                return true;
            }
            return false;
        })()""")
        if not backed1:
            await browser.send("Page.navigate", {"url": "http://127.0.0.1:8000/videos"})
        await browser.wait_for_condition("Boolean(document.querySelector('input[type=\"file\"]'))", timeout=15)
        await asyncio.sleep(0.5)
        s4_after1 = await browser.capture_screenshot("demo4_02_after_first.png")

        # Prepare second file with identical filename: copy d4_repeat2_source to a temp folder named browser_demo4_repeat.mp4
        rep2_dir = DEMO_FILES_DIR / "subfolder_repeat2"
        rep2_dir.mkdir(parents=True, exist_ok=True)
        d4_repeat2 = rep2_dir / "browser_demo4_repeat.mp4"
        shutil.copyfile(d4_repeat2_source, d4_repeat2)
        print(f"Uploading second instance with identical filename: {d4_repeat2.name} (3s duration, {d4_repeat2.stat().st_size} bytes)")

        await browser.set_file_input("input[type=\"file\"]", [str(d4_repeat2)])
        await browser.wait_for_condition(f"window.location.pathname.startsWith('/videos/med_') && window.location.pathname != '{url_rep_1}'", timeout=20)
        url_rep_2 = await browser.evaluate("window.location.pathname")
        med_rep_2 = url_rep_2.split("/")[-1]
        print(f"Second upload navigated to: {url_rep_2} (ID: {med_rep_2})")

        # Return to library
        print("Returning to library from second upload...")
        backed2 = await browser.evaluate("""(() => {
            const back = document.querySelector('button[title="Return to Video Library"]') ||
                         Array.from(document.querySelectorAll('button')).find(b => b.innerText.includes('Back to Video Library'));
            if (back) {
                back.click();
                return true;
            }
            return false;
        })()""")
        if not backed2:
            await browser.send("Page.navigate", {"url": "http://127.0.0.1:8000/videos"})
        await browser.wait_for_condition("Boolean(document.querySelector('input[type=\"file\"]'))", timeout=15)
        await asyncio.sleep(1.0)
        s4_after2 = await browser.capture_screenshot("demo4_03_after_second.png")

        # Verify DB rows
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row_rep1 = conn.execute("SELECT * FROM media_assets WHERE id = ?", (med_rep_1,)).fetchone()
            row_rep2 = conn.execute("SELECT * FROM media_assets WHERE id = ?", (med_rep_2,)).fetchone()

        assert row_rep1 is not None and row_rep2 is not None
        assert med_rep_1 != med_rep_2, "Distinct media IDs required"
        p_rep1 = Path(row_rep1["storage_path"])
        p_rep2 = Path(row_rep2["storage_path"])
        assert p_rep1 != p_rep2, "Distinct storage paths required"
        assert p_rep1.exists() and p_rep2.exists(), "Both physical files must exist simultaneously"
        assert p_rep1.stat().st_size == d4_repeat1.stat().st_size
        assert p_rep2.stat().st_size == d4_repeat2.stat().st_size

        evidence["DEMO_4_REPEATED_UPLOAD"] = {
            "status": "PASS",
            "filename": "browser_demo4_repeat.mp4",
            "first_upload": {
                "id": med_rep_1,
                "url": url_rep_1,
                "path": str(p_rep1),
                "size": p_rep1.stat().st_size,
            },
            "second_upload": {
                "id": med_rep_2,
                "url": url_rep_2,
                "path": str(p_rep2),
                "size": p_rep2.stat().st_size,
            },
            "both_files_exist": p_rep1.exists() and p_rep2.exists(),
            "screenshots": [s4_pre.name, s4_after1.name, s4_after2.name],
        }
        print("DEMO 4: PASS")

        # -------------------------------------------------------------
        # DEMO 5: Mobile-Width Viewport Emulation
        # -------------------------------------------------------------
        print("\n" + "=" * 60)
        print("DEMO 5: Mobile-Width Viewport Emulation (375x812)")
        print("=" * 60)

        # Emulate iPhone 12/13/14 viewport: 375x812, deviceScaleFactor 2
        await browser.send("Emulation.setDeviceMetricsOverride", {
            "width": 375,
            "height": 812,
            "deviceScaleFactor": 2,
            "mobile": True,
        })
        await browser.send("Page.navigate", {"url": "http://127.0.0.1:8000/videos"})
        await browser.wait_for_condition("Boolean(document.querySelector('input[type=\"file\"]'))", timeout=15)
        await asyncio.sleep(1.0)

        s5_mob_pre = await browser.capture_screenshot("demo5_01_mobile_pre_upload.png")

        # Verify dropzone and upload button visibility in mobile DOM
        btn_visible = await browser.evaluate("Boolean(document.querySelector('button') && (document.body.innerText.includes('Upload New Video') || document.body.innerText.includes('browse files')))")
        assert btn_visible, "Upload button must be visible in mobile viewport"

        # Execute upload in mobile viewport
        print(f"Uploading via mobile viewport: {d5_mobile.name}")
        await browser.set_file_input("input[type=\"file\"]", [str(d5_mobile)])

        # Wait for navigation to dashboard
        await browser.wait_for_condition("window.location.pathname.startsWith('/videos/med_')", timeout=20)
        url_mob = await browser.evaluate("window.location.pathname")
        med_mob = url_mob.split("/")[-1]
        print(f"Mobile upload navigated to: {url_mob} (ID: {med_mob})")

        # Wait for dashboard to load
        for _ in range(20):
            body_m = await browser.evaluate("document.body.innerText") or ""
            if "Technical Video Specifications" in body_m or "Duration" in body_m or "Resolution" in body_m:
                print("Mobile dashboard loaded successfully.")
                break
            await asyncio.sleep(1.0)
        await asyncio.sleep(1.0)
        s5_mob_dash = await browser.capture_screenshot("demo5_02_mobile_dashboard.png")

        # Clear emulation
        await browser.send("Emulation.clearDeviceMetricsOverride")

        # Verify DB & physical file
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            row_mob = conn.execute("SELECT * FROM media_assets WHERE id = ?", (med_mob,)).fetchone()
        assert row_mob is not None
        p_mob = Path(row_mob["storage_path"])
        assert p_mob.exists()

        evidence["DEMO_5_MOBILE_VIEWPORT"] = {
            "status": "PASS",
            "viewport": {"width": 375, "height": 812, "mobile": True},
            "upload_button_visible": btn_visible,
            "media_id": med_mob,
            "url": url_mob,
            "storage_path": str(p_mob),
            "file_exists": p_mob.exists(),
            "screenshots": [s5_mob_pre.name, s5_mob_dash.name],
        }
        print("DEMO 5: PASS")

        # Close CDP browser session
        await browser.close()

    finally:
        chrome_proc.terminate()
        chrome_proc.wait()

    # Save evidence JSON
    with open(EVIDENCE_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                "task": "P1.1-R1",
                "title": "Real Browser Upload Acceptance and Scope Verification",
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "all_passed": all(e["status"] == "PASS" for e in evidence.values()),
                "demo_count": len(evidence),
                "demos": evidence,
            },
            f,
            indent=2,
        )

    print("\n" + "=" * 75)
    print(f"All {len(evidence)} P1.1-R1 Real-Browser Demonstrations Complete: ALL PASSED")
    print(f"Evidence recorded at: {EVIDENCE_FILE}")
    print("=" * 75)


if __name__ == "__main__":
    asyncio.run(run_demos())
