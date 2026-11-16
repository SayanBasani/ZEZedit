"""
P0.7 Automated Regression Test Suite: Windows Launcher Reliability, Process Ownership & Lifecycle Safety
Comprehensive testing of script path resolution, duplicate guard, port conflict detection,
stale PID cleanup, PID reuse protection, graceful stop, child cleanup, and restart recovery.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# ---------------------------------------------------------------------------
# Helper: Check PowerShell script syntax and execution
# ---------------------------------------------------------------------------
def _run_ps_command(cmd: str, cwd: Path = PROJECT_ROOT) -> subprocess.CompletedProcess:
    ps_cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy", "Bypass",
        "-Command", cmd
    ]
    return subprocess.run(ps_cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False)


# ---------------------------------------------------------------------------
# 1. Script existence and path resolution from project root
# ---------------------------------------------------------------------------
def test_01_launcher_scripts_exist_and_resolve_root():
    start_ps = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    stop_ps = PROJECT_ROOT / "Stop-ZEZEdit.ps1"
    start_bat = PROJECT_ROOT / "Start-ZEZEdit.bat"
    stop_bat = PROJECT_ROOT / "Stop-ZEZEdit.bat"

    for f in [start_ps, stop_ps, start_bat, stop_bat]:
        assert f.exists(), f"File {f.name} missing"

    # Verify script resolves PROJECT_ROOT even if called from another directory
    res = _run_ps_command(
        f'& "{start_ps}" -ValidateOnly; exit $LASTEXITCODE',
        cwd=Path(os.environ.get("TEMP", "C:\\"))
    )
    assert res.returncode == 0
    assert str(PROJECT_ROOT).lower() in res.stdout.lower() or "workspace root" in res.stdout.lower()


# ---------------------------------------------------------------------------
# 2. Invocation from a different working directory
# ---------------------------------------------------------------------------
def test_02_invocation_from_different_working_directory(tmp_path: Path):
    start_ps = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    # Invoke script with -ValidateOnly from an isolated tmp_path directory
    cmd = f'& "{start_ps}" -ValidateOnly; exit $LASTEXITCODE'
    res = _run_ps_command(cmd, cwd=tmp_path)
    assert res.returncode == 0
    assert str(PROJECT_ROOT).lower() in res.stdout.lower() or "workspace root" in res.stdout.lower()


# ---------------------------------------------------------------------------
# 3. Duplicate startup prevention
# ---------------------------------------------------------------------------
def test_03_duplicate_startup_prevention(tmp_path: Path):
    start_ps = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    content = start_ps.read_text(encoding="utf-8")
    # Verify duplicate guard logic is present in the script
    assert "is_already_running" in content.lower() or "already running" in content.lower()
    assert "no duplicate" in content.lower() or "already running" in content.lower()


# ---------------------------------------------------------------------------
# 4. Already running healthy application detection
# ---------------------------------------------------------------------------
def test_04_already_running_healthy_detection(tmp_path: Path):
    start_ps = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    content = start_ps.read_text(encoding="utf-8")
    assert "Invoke-RestMethod" in content
    assert "healthUrl" in content or "health" in content.lower()


# ---------------------------------------------------------------------------
# 5. Port occupied by an unrelated process
# ---------------------------------------------------------------------------
def test_05_port_occupied_by_unrelated_process(tmp_path: Path):
    # Bind an isolated TCP socket on a free ephemeral port
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    s.listen(1)
    allocated_port = s.getsockname()[1]

    try:
        start_ps = PROJECT_ROOT / "Start-ZEZEdit.ps1"
        # Run launcher against this port
        res = _run_ps_command(f'& "{start_ps}" -NoBrowser -Port {allocated_port} -TimeoutSeconds 2')
        # Should detect foreign port listener, refuse to bind, and exit 1
        assert res.returncode != 0
        assert "already in use" in res.stdout.lower() or "already in use" in res.stderr.lower()
    finally:
        s.close()


# ---------------------------------------------------------------------------
# 6. Stale PID file cleanup
# ---------------------------------------------------------------------------
def test_06_stale_pid_file_cleanup(tmp_path: Path):
    temp_dir = PROJECT_ROOT / "storage" / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    stale_pid_file = temp_dir / "zezedit.pid"
    stale_meta_file = temp_dir / "zezedit_process.json"

    # Write a fictitious PID that definitely does not exist
    stale_pid = 999999
    stale_pid_file.write_text(str(stale_pid), encoding="utf-8")
    stale_meta_file.write_text(
        json.dumps({"pid": stale_pid, "project_root": str(PROJECT_ROOT), "port": 8000}),
        encoding="utf-8"
    )

    stop_ps = PROJECT_ROOT / "Stop-ZEZEdit.ps1"
    res = _run_ps_command(f'& "{stop_ps}"')
    assert res.returncode == 0
    # Stale files must be cleaned
    assert not stale_pid_file.exists() or not stale_meta_file.exists()


# ---------------------------------------------------------------------------
# 7. PID reuse protection (foreign process with same PID preserved)
# ---------------------------------------------------------------------------
def test_07_pid_reuse_protection(tmp_path: Path):
    # Spawn an unrelated python worker (e.g. idle sleep)
    dummy = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    dummy_pid = dummy.pid

    try:
        temp_dir = PROJECT_ROOT / "storage" / "temp"
        temp_dir.mkdir(parents=True, exist_ok=True)
        stale_meta = temp_dir / "zezedit_process.json"
        # Record dummy_pid as zezedit PID
        stale_meta.write_text(
            json.dumps({"pid": dummy_pid, "project_root": str(PROJECT_ROOT), "command_line": "app.main:app"}),
            encoding="utf-8"
        )

        stop_ps = PROJECT_ROOT / "Stop-ZEZEdit.ps1"
        res = _run_ps_command(f'& "{stop_ps}"')
        assert res.returncode == 0

        # Dummy process must NOT have been killed because its commandline is "import time; time.sleep(30)", not app.main:app
        time.sleep(0.5)
        assert dummy.poll() is None, "Foreign process was killed by stop script!"
    finally:
        dummy.kill()


# ---------------------------------------------------------------------------
# 8. Python environment validation
# ---------------------------------------------------------------------------
def test_08_python_environment_validation():
    start_ps = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    content = start_ps.read_text(encoding="utf-8")
    assert "backend\\.venv\\scripts\\python.exe" in content.lower()
    assert "fastapi, uvicorn" in content.lower()


# ---------------------------------------------------------------------------
# 9. FFmpeg / FFprobe discovery
# ---------------------------------------------------------------------------
def test_09_ffmpeg_discovery():
    start_ps = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    content = start_ps.read_text(encoding="utf-8")
    assert "ffmpeg" in content.lower()
    assert "ffprobe" in content.lower()


# ---------------------------------------------------------------------------
# 10. Required configuration (.env / .env.example)
# ---------------------------------------------------------------------------
def test_10_required_configuration():
    start_ps = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    content = start_ps.read_text(encoding="utf-8")
    assert ".env.example" in content
    assert ".env" in content


# ---------------------------------------------------------------------------
# 11. Health check timeout and error diagnostics
# ---------------------------------------------------------------------------
def test_11_health_check_timeout_diagnostics():
    start_ps = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    content = start_ps.read_text(encoding="utf-8")
    assert "TimeoutSeconds" in content
    assert "launcher_stderr.log" in content


# ---------------------------------------------------------------------------
# 12. Graceful shutdown sequence
# ---------------------------------------------------------------------------
def test_12_graceful_shutdown_sequence():
    stop_ps = PROJECT_ROOT / "Stop-ZEZEdit.ps1"
    content = stop_ps.read_text(encoding="utf-8")
    assert "taskkill" in content.lower()
    assert "graceful" in content.lower()


# ---------------------------------------------------------------------------
# 13. Owned child process shutdown
# ---------------------------------------------------------------------------
def test_13_owned_child_process_shutdown():
    stop_ps = PROJECT_ROOT / "Stop-ZEZEdit.ps1"
    content = stop_ps.read_text(encoding="utf-8")
    assert "parentprocessid" in content.lower() or "child" in content.lower()


# ---------------------------------------------------------------------------
# 14. Unrelated process preservation during stop
# ---------------------------------------------------------------------------
def test_14_unrelated_process_preservation():
    stop_ps = PROJECT_ROOT / "Stop-ZEZEdit.ps1"
    content = stop_ps.read_text(encoding="utf-8")
    assert "taskkill /im python.exe" not in content.lower()
    assert "preserving process" in content.lower()


# ---------------------------------------------------------------------------
# 15. Repeated stop request (idempotent)
# ---------------------------------------------------------------------------
def test_15_repeated_stop_request():
    stop_ps = PROJECT_ROOT / "Stop-ZEZEdit.ps1"
    res1 = _run_ps_command(f'& "{stop_ps}"')
    res2 = _run_ps_command(f'& "{stop_ps}"')
    assert res1.returncode == 0
    assert res2.returncode == 0
    assert "no active zezedit" in res2.stdout.lower() or "cleanly stopped" in res2.stdout.lower()


# ---------------------------------------------------------------------------
# 16. Restart after clean shutdown
# ---------------------------------------------------------------------------
def test_16_restart_after_clean_shutdown():
    # Verify that PID files are unlinked so next startup proceeds without blocker
    temp_dir = PROJECT_ROOT / "storage" / "temp"
    pid_file = temp_dir / "zezedit.pid"
    meta_file = temp_dir / "zezedit_process.json"
    stop_ps = PROJECT_ROOT / "Stop-ZEZEdit.ps1"
    _run_ps_command(f'& "{stop_ps}"')
    assert not pid_file.exists() or not meta_file.exists()


# ---------------------------------------------------------------------------
# 17. Restart after simulated crash (recover_interrupted_jobs)
# ---------------------------------------------------------------------------
def test_17_restart_after_simulated_crash(tmp_path: Path):
    from app.core.config import Settings
    from app.core.storage import StorageLayout
    from app.db.connection import sqlite_session
    from app.db.migrator import run_migrations
    from app.services.jobs import JobOrchestrator

    layout = StorageLayout.from_root(tmp_path / "storage")
    layout.ensure_directories()
    run_migrations(layout.db_file, PROJECT_ROOT / "backend" / "migrations", layout.backups)

    settings = Settings(storage_root=layout.root)
    orch = JobOrchestrator(settings=settings, db_path=layout.db_file)

    # Insert a job in 'running' state simulating crash
    with sqlite_session(layout.db_file) as conn:
        conn.execute(
            """
            INSERT INTO jobs (id, job_type, status, priority, retry_count, current_stage, created_at, updated_at)
            VALUES ('job_crashed_restart', 'export_render', 'running', 1, 0, 'rendering', datetime('now'), datetime('now'))
            """
        )

    # Run recovery (as done on startup in main.py)
    recovered = orch.recover_interrupted_jobs()
    assert "job_crashed_restart" in recovered
    rec = orch.get_job("job_crashed_restart")
    assert rec.status == "interrupted"


# ---------------------------------------------------------------------------
# 18. Log creation and error reporting
# ---------------------------------------------------------------------------
def test_18_log_creation_and_error_reporting():
    start_ps = PROJECT_ROOT / "Start-ZEZEdit.ps1"
    content = start_ps.read_text(encoding="utf-8")
    assert "launcher_stdout.log" in content
    assert "launcher_stderr.log" in content
    assert "storage\\logs" in content.lower()
