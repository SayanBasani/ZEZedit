import urllib.request
import json
import sqlite3

base_url = 'http://127.0.0.1:8000/api/v1/projects/proj_0f8238e5761d/media/med_51dc0e4b43f8/candidates/cand_d8db654e1441/edit'

# 1. GET initial edit
req = urllib.request.Request(base_url)
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print('Initial edit state:', data)

# 2. PUT edit update
update_payload = {
    'edited_start_time': 14.0,
    'edited_end_time': 28.0,
    'aspect_ratio': '9:16',
    'framing_mode': 'manual',
    'manual_crop_x_pct': 55.0,
    'manual_crop_y_pct': 48.0,
    'manual_crop_zoom': 1.15
}
put_req = urllib.request.Request(
    base_url,
    data=json.dumps(update_payload).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='PUT'
)
with urllib.request.urlopen(put_req) as resp:
    put_data = json.loads(resp.read().decode())
    print('Updated edit state:', put_data)

# 3. Verify original candidate in DB is pristine
conn = sqlite3.connect('D:/ZezEdit/storage/db/zezedit.db')
c = conn.cursor()
c.execute('SELECT start_time, end_time, duration FROM shorts_candidates WHERE id = ?', ('cand_d8db654e1441',))
print('Pristine candidate in DB:', c.fetchone())

# 4. POST reset to original
reset_req = urllib.request.Request(f'{base_url}/reset', data=b'', method='POST')
with urllib.request.urlopen(reset_req) as resp:
    reset_data = json.loads(resp.read().decode())
    print('Reset edit state:', reset_data)
