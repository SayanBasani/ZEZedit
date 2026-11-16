"""
ZEZEdit 2.0 - P0.8 Real Windows Production Frontend Serving & SPA Routing Demonstrations
Executes all required demonstration groups (A through F) against the real Windows production application,
verifying real static assets, SPA deep links, API isolation, security confinement, and zero-Vite independence.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def run_command(cmd_list, cwd=PROJECT_ROOT):
    start_t = time.time()
    res = subprocess.run(cmd_list, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)
    duration = round(time.time() - start_t, 2)
    return res.returncode, res.stdout, res.stderr, duration


def http_request(url, method="GET", headers=None, data=None, timeout=10):
    headers = headers or {}
    if "User-Agent" not in headers:
        headers["User-Agent"] = "ZezEdit-P08-Demo"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    start_t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read()
            duration = round(time.time() - start_t, 3)
            return resp.status, dict(resp.headers), content, duration
    except urllib.error.HTTPError as e:
        content = e.read()
        duration = round(time.time() - start_t, 3)
        return e.code, dict(e.headers), content, duration
    except Exception as e:
        duration = round(time.time() - start_t, 3)
        return 0, {}, str(e).encode("utf-8"), duration


def is_port_listening(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        try:
            s.connect((host, port))
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False


def run_all_demos():
    print("=" * 80)
    print("ZEZEDIT 2.0 — P0.8 PRODUCTION FRONTEND SERVING & SPA ROUTING DEMONSTRATIONS")
    print("=" * 80)

    start_script = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    stop_script = PROJECT_ROOT / "Stop-ZEZEdit.ps1"
    evidence = {}

    # Ensure any previous instance is cleanly stopped
    run_command(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(stop_script)])
    time.sleep(1)

    # -------------------------------------------------------------------------
    # DEMO GROUP A: Production Startup
    # -------------------------------------------------------------------------
    print("\n--- DEMO GROUP A: Production Startup via Windows Launcher ---")
    start_cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(start_script), "-NoBrowser"]
    rc_start, out_start, err_start, dur_start = run_command(start_cmd)
    print(f"Command: Start-ZEZEdit.ps1 -NoBrowser (Exit Code: {rc_start}, Duration: {dur_start}s)")
    assert rc_start == 0, f"Startup failed with exit code {rc_start}: {err_start}"

    # Read process metadata
    meta_file = PROJECT_ROOT / "storage" / "temp" / "zezedit_process.json"
    proc_info = {}
    if meta_file.exists():
        proc_info = json.loads(meta_file.read_text(encoding="utf-8"))
    print(f"Server Process Ownership: PID={proc_info.get('pid')}, Port={proc_info.get('port')}, Role={proc_info.get('role')}")

    # Verify root endpoint
    status_a, headers_a, body_a, dur_a = http_request("http://127.0.0.1:8000/")
    body_text_a = body_a.decode("utf-8", errors="replace")
    print(f"Root URL HTTP {status_a} ({dur_a}s), Content-Type: {headers_a.get('content-type')}")
    assert status_a == 200
    assert "text/html" in headers_a.get("content-type", "")
    assert "<!doctype html>" in body_text_a.lower() or "<div id=\"root\">" in body_text_a
    print("FastAPI successfully serves production frontend HTML at root!")

    # Verify Vite dev server port 5173 is closed
    vite_alive = is_port_listening(5173)
    print(f"Vite dev server port 5173 is listening: {vite_alive} (Expected: False)")
    assert vite_alive is False, "Vite dev server is unexpectedly running on port 5173!"

    evidence["group_a"] = {
        "status": "PASSED",
        "pid": proc_info.get("pid"),
        "root_status": status_a,
        "content_type": headers_a.get("content-type"),
        "vite_dev_server_active": vite_alive,
        "duration_seconds": dur_start,
    }

    # -------------------------------------------------------------------------
    # DEMO GROUP B: Frontend Navigation & Deep Links
    # -------------------------------------------------------------------------
    print("\n--- DEMO GROUP B: Frontend Navigation & Deep Links ---")
    routes_to_test = [
        ("/", "Root Landing Page"),
        ("/videos", "Video Library View"),
        ("/videos/med_5e0235303b02", "Real Video Dashboard Route"),
        ("/videos/med_5e0235303b02/editor", "Nested Candidate Editor Deep Link"),
        ("/studio/med_5e0235303b02", "Studio Deep Link"),
        ("/projects", "Projects View"),
        ("/settings", "Settings Manager View"),
        ("/processes", "Processes / Working Queue View"),
        ("/queue", "Alternative Queue Route"),
        ("/ai-providers", "AI Provider Manager View"),
        ("/characters", "Character Studio View"),
    ]

    group_b_results = {}
    for route, label in routes_to_test:
        url = f"http://127.0.0.1:8000{route}"
        st, hd, bd, dur = http_request(url)
        txt = bd.decode("utf-8", errors="replace")
        print(f"Route: {route:<35} -> HTTP {st} ({dur}s), HTML: {'<div id=\"root\">' in txt}")
        assert st == 200, f"Route {route} failed with {st}"
        assert "text/html" in hd.get("content-type", "")
        assert ("<div id=\"root\">" in txt) or ("<!doctype html>" in txt.lower())
        group_b_results[route] = {"status": st, "content_type": hd.get("content-type"), "duration_s": dur}

    # Test refresh idempotency on nested route (3 consecutive refreshes)
    refresh_target = "http://127.0.0.1:8000/videos/med_5e0235303b02"
    for r_idx in range(1, 4):
        st_ref, hd_ref, _, dur_ref = http_request(refresh_target)
        print(f"Refresh #{r_idx} on /videos/med_5e0235303b02 -> HTTP {st_ref} ({dur_ref}s)")
        assert st_ref == 200

    evidence["group_b"] = {
        "status": "PASSED",
        "routes_verified": group_b_results,
        "refresh_verified": True,
    }

    # -------------------------------------------------------------------------
    # DEMO GROUP C: Static Assets & Missing Asset 404s
    # -------------------------------------------------------------------------
    print("\n--- DEMO GROUP C: Static Assets & Missing Asset 404s ---")
    # Extract asset paths from root HTML
    js_match = re.search(r'src=["\'](/assets/[^"\']+\.js)["\']', body_text_a)
    css_match = re.search(r'href=["\'](/assets/[^"\']+\.css)["\']', body_text_a)

    js_path = js_match.group(1) if js_match else "/assets/index-C8H2aI7o.js"
    css_path = css_match.group(1) if css_match else "/assets/index-CS5Ed-X8.css"

    # 1. Real JS Bundle
    st_js, hd_js, bd_js, dur_js = http_request(f"http://127.0.0.1:8000{js_path}")
    print(f"JS Asset ({js_path}): HTTP {st_js}, Length: {len(bd_js)} bytes, Type: {hd_js.get('content-type')}")
    assert st_js == 200
    assert "javascript" in hd_js.get("content-type", "").lower() or "text/javascript" in hd_js.get("content-type", "").lower()
    assert len(bd_js) > 50000
    assert not bd_js.startswith(b"<!doctype html>")

    # 2. Real CSS Bundle
    st_css, hd_css, bd_css, dur_css = http_request(f"http://127.0.0.1:8000{css_path}")
    print(f"CSS Asset ({css_path}): HTTP {st_css}, Length: {len(bd_css)} bytes, Type: {hd_css.get('content-type')}")
    assert st_css == 200
    assert "text/css" in hd_css.get("content-type", "").lower()
    assert len(bd_css) > 10000
    assert not bd_css.startswith(b"<!doctype html>")

    # 3. Missing Static Assets MUST return 404, NEVER fallback to HTML
    missing_assets = [
        "/assets/missing-chunk-99999.js",
        "/assets/missing-theme.css",
        "/missing-app.js",
        "/missing-style.css",
        "/missing-logo.png",
        "/missing-font.woff2",
    ]
    for ma in missing_assets:
        st_ma, hd_ma, bd_ma, _ = http_request(f"http://127.0.0.1:8000{ma}")
        print(f"Missing Asset ({ma:<32}): HTTP {st_ma}, Type: {hd_ma.get('content-type')}")
        assert st_ma == 404, f"Missing asset {ma} returned {st_ma} instead of 404"
        assert "text/html" not in hd_ma.get("content-type", ""), f"Missing asset {ma} returned HTML!"
        assert b"<!doctype html>" not in bd_ma.lower()

    evidence["group_c"] = {
        "status": "PASSED",
        "js_bundle": {"path": js_path, "status": st_js, "bytes": len(bd_js), "type": hd_js.get("content-type")},
        "css_bundle": {"path": css_path, "status": st_css, "bytes": len(bd_css), "type": hd_css.get("content-type")},
        "missing_assets_verified_404": True,
    }

    # -------------------------------------------------------------------------
    # DEMO GROUP D: API Isolation & Route Protection
    # -------------------------------------------------------------------------
    print("\n--- DEMO GROUP D: API Isolation & Route Protection ---")
    api_endpoints = [
        ("/health", 200, "Authoritative Health Endpoint"),
        ("/api/v1/health", 200, "API Health Endpoint"),
        ("/api/v1/projects", 200, "Projects Listing"),
        ("/api/v1/jobs", 200, "Jobs Queue Listing"),
        ("/api/v1/media", 200, "Media Assets Listing"),
        ("/api/v1/system/info", 200, "System Info Diagnostic"),
        ("/api/v1/system/diagnostics", 200, "System Diagnostics"),
        ("/api/v1/media/med_5e0235303b02", 200, "Specific Media Asset Metadata"),
        ("/api/v1/missing_endpoint_xyz", 404, "Unknown API Route (Must return JSON 404)"),
    ]

    group_d_results = {}
    for ep, exp_st, ep_label in api_endpoints:
        st_ep, hd_ep, bd_ep, dur_ep = http_request(f"http://127.0.0.1:8000{ep}")
        print(f"API {ep:<35} -> HTTP {st_ep} (Expected {exp_st}), Type: {hd_ep.get('content-type')}")
        assert st_ep == exp_st, f"Endpoint {ep} returned {st_ep} instead of {exp_st}"
        assert "application/json" in hd_ep.get("content-type", ""), f"Endpoint {ep} returned non-JSON: {hd_ep.get('content-type')}"
        assert b"<!doctype html>" not in bd_ep.lower()
        group_d_results[ep] = {"status": st_ep, "content_type": hd_ep.get("content-type")}

    evidence["group_d"] = {
        "status": "PASSED",
        "api_endpoints_verified": group_d_results,
    }

    # -------------------------------------------------------------------------
    # DEMO GROUP E: Security, Path Safety & Sensitive File Protection
    # -------------------------------------------------------------------------
    print("\n--- DEMO GROUP E: Security & Path Safety ---")
    security_probes = [
        ("/..%2f..%2f..%2fWindows%2fwin.ini", [400, 403, 404], "URL Encoded Traversal"),
        ("/....//....//....//etc/passwd", [400, 403, 404], "Multi-Dot Traversal"),
        ("/..\\..\\..\\Windows\\System32\\cmd.exe", [400, 403, 404], "Backslash Traversal"),
        ("/.env", [403, 404], "Direct .env Probe"),
        ("/storage/db/zezedit.db", [403, 404], "Direct SQLite Database Probe"),
        ("/backend/app/main.py", [403, 404], "Backend Source Code Probe"),
        ("/storage/logs/launcher_stdout.log", [403, 404], "Server Log File Probe"),
        ("/storage/backups/", [403, 404], "Database Backup Directory Probe"),
        ("/.git/config", [403, 404], "Git Repository Config Probe"),
    ]

    group_e_results = {}
    for target, valid_codes, desc in security_probes:
        st_sec, hd_sec, bd_sec, _ = http_request(f"http://127.0.0.1:8000{target}")
        print(f"Security Probe ({desc:<30}): {target:<35} -> HTTP {st_sec} (Blocked)")
        assert st_sec in valid_codes, f"Target {target} returned {st_sec}, which is not in {valid_codes}"
        assert b"ZEZEDIT_" not in bd_sec
        assert b"SQLite format" not in bd_sec
        assert b"def create_app" not in bd_sec
        group_e_results[target] = {"status": st_sec, "blocked": True}

    evidence["group_e"] = {
        "status": "PASSED",
        "security_probes_verified": group_e_results,
    }

    # -------------------------------------------------------------------------
    # DEMO GROUP F: Production Independence (Zero Vite Dependency)
    # -------------------------------------------------------------------------
    print("\n--- DEMO GROUP F: Production Independence (Zero Vite Dependency) ---")
    # Verify port 5173 is closed
    assert not is_port_listening(5173), "Port 5173 must not be open"
    print("Confirmed Vite development port 5173 is CLOSED.")

    # Fresh HTTP session simulating browser cold load
    fresh_st, fresh_hd, fresh_bd, fresh_dur = http_request("http://127.0.0.1:8000/videos/med_5e0235303b02", headers={"Connection": "close"})
    print(f"Cold-Session Load on /videos/med_5e0235303b02: HTTP {fresh_st} ({fresh_dur}s)")
    assert fresh_st == 200
    assert "text/html" in fresh_hd.get("content-type", "")

    # Clean shutdown
    print("\nShutting down ZEZEdit server cleanly...")
    stop_cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(stop_script)]
    rc_stop, out_stop, err_stop, dur_stop = run_command(stop_cmd)
    print(f"Stop command exit code: {rc_stop} (Duration: {dur_stop}s)")
    if rc_stop != 0:
        print(f"Stop command output: {out_stop}")
        print(f"Stop command error: {err_stop}")
    assert rc_stop == 0

    time.sleep(1)
    port8000_alive = is_port_listening(8000)
    print(f"Port 8000 listening after stop: {port8000_alive} (Expected: False)")
    assert port8000_alive is False, "Port 8000 was not closed after stop!"

    evidence["group_f"] = {
        "status": "PASSED",
        "vite_port_closed": True,
        "cold_session_verified": True,
        "clean_shutdown_verified": True,
    }

    print("\n" + "=" * 80)
    print("ALL P0.8 DEMONSTRATION CASES COMPLETED SUCCESSFULLY!")
    print(json.dumps(evidence, indent=2))
    print("=" * 80)


if __name__ == "__main__":
    run_all_demos()
