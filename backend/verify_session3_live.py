import json
import sys
import time
import urllib.request

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(line_buffering=True)

base_url = "http://127.0.0.1:8000/api/v1"
asset_id = "med_51dc0e4b43f8"
proj_id = "proj_0f8238e5761d"

print("1. Checking current media asset...")
req = urllib.request.Request(f"{base_url}/media/{asset_id}")
with urllib.request.urlopen(req) as res:
    data = json.loads(res.read())
    print(f"Asset: {data['original_filename']}, duration: {data['duration_seconds']}s, size: {data['file_size_bytes']} bytes")

print("2. Triggering analysis run...")
req = urllib.request.Request(
    f"{base_url}/projects/{proj_id}/media/{asset_id}/analysis",
    data=json.dumps({"profile": "fast", "force_reanalysis": True}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req) as res:
    run_resp = json.loads(res.read())
    run_id = run_resp["id"]
    print(f"Started run: {run_id}, job_id: {run_resp.get('job_id')}, status: {run_resp['status']}")

print("3. Polling telemetry until completed...")
start_t = time.time()
while time.time() - start_t < 180:
    time.sleep(2)
    t_req = urllib.request.Request(f"{base_url}/projects/{proj_id}/media/{asset_id}/analysis/{run_id}/telemetry")
    with urllib.request.urlopen(t_req) as t_res:
        telem = json.loads(t_res.read())
        stage = telem.get("current_stage")
        pct = telem.get("progress_pct")
        status = telem.get("status")
        details = telem.get("stage_details") or {}
        elapsed = details.get("elapsed_seconds", 0)
        print(f"[{round(time.time() - start_t, 1)}s] Status: {status} | Stage: {stage} ({pct}%) | Pipeline Elapsed: {elapsed}s")
        if status in ("completed", "failed", "cancelled"):
            print("Finished run details:")
            print(f"  - Segments: {details.get('segment_count')}")
            print(f"  - Turns: {details.get('turn_count')}")
            print(f"  - Scenes: {details.get('scene_count')}")
            print(f"  - Frames: {details.get('frame_count')}")
            print(f"  - Timings: {details.get('timings')}")
            break

print("4. Testing cache endpoint...")
c_req = urllib.request.Request(f"{base_url}/projects/{proj_id}/media/{asset_id}/analysis/{run_id}/cache")
with urllib.request.urlopen(c_req) as c_res:
    cache_info = json.loads(c_res.read())
    print("Cache Info:", json.dumps(cache_info, indent=2))

print("5. Triggering second run (should be instant cache hit)...")
t0 = time.time()
req2 = urllib.request.Request(
    f"{base_url}/projects/{proj_id}/media/{asset_id}/analysis",
    data=json.dumps({"profile": "fast", "force_reanalysis": False}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(req2) as res2:
    run2_resp = json.loads(res2.read())
    cache_hit_time = round(time.time() - t0, 3)
    print(f"Second run response in {cache_hit_time}s: run_id={run2_resp['id']} (same: {run2_resp['id'] == run_id}), status={run2_resp['status']}")
