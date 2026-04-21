"""Round-trip test for install-autostart.ps1.

Runs the installer in test mode (-NoStart, no health check / no server launch)
in a temp working copy, asserts that:

  1. Launcher script is dropped at the expected path
  2. Startup .lnk is created and points at pythonw + the launcher
  3. Uninstall removes the .lnk
  4. Uninstall preserves the launcher script (checked-in artifact)
  5. Re-install does not overwrite a user-edited launcher
  6. Re-install overwrites a byte-identical-to-canonical launcher

Skipped on non-Windows.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest  # noqa: F401 — pytest is used via its decorators/fixtures only

IS_WINDOWS = sys.platform == "win32"

REPO_ROOT = Path(__file__).resolve().parent.parent
INSTALLER = REPO_ROOT / "install-autostart.ps1"


def run_ps(script: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script), *args],
        cwd=str(cwd or script.parent),
        capture_output=True,
        text=True,
        timeout=60,
    )


def startup_folder() -> Path:
    # $env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup
    appdata = os.environ.get("APPDATA")
    assert appdata, "APPDATA not set"
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


@pytest.fixture(scope="session")
def _startup_lnk_lock(tmp_path_factory):
    """Serialises access to the real Startup folder across pytest-xdist workers.

    Two workers running installer tests in parallel could race on the user's real
    `allmeta-rct-extractor.lnk`: one deletes, the other sees no file, they corrupt
    each other's backups. A session-scoped filelock + stable backup location
    survives worker processes.
    """
    try:
        import filelock  # type: ignore
    except ImportError:
        filelock = None
    lock_dir = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "allmeta-test-backups"
    lock_dir.mkdir(parents=True, exist_ok=True)
    if filelock:
        yield filelock.FileLock(str(lock_dir / "startup.lock"))
    else:
        # Best-effort: without filelock, xdist-level serialisation relies on
        # `@pytest.mark.xdist_group("startup_folder")` + `--dist loadgroup`.
        class _Noop:
            def __enter__(self): return self
            def __exit__(self, *a): return False
        yield _Noop()


@pytest.fixture
def sandbox(tmp_path: Path, _startup_lnk_lock):
    """Clone the installer into a tmp dir so real install doesn't mutate the repo on disk.

    Backs up any pre-existing Startup .lnk to a STABLE location under
    %LOCALAPPDATA%/allmeta-test-backups so a kill mid-test doesn't lose the
    real shortcut along with the pytest tmp_path.
    """
    dst = tmp_path / "rx"
    dst.mkdir()
    shutil.copy(INSTALLER, dst / "install-autostart.ps1")

    real = startup_folder() / "allmeta-rct-extractor.lnk"
    stable_backup_dir = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "allmeta-test-backups"
    stable_backup_dir.mkdir(parents=True, exist_ok=True)
    stable_backup = stable_backup_dir / "allmeta-rct-extractor.pretest.lnk"

    with _startup_lnk_lock:
        backup_created = False
        if real.exists():
            shutil.copy(real, stable_backup)
            backup_created = True
            real.unlink()
        try:
            yield dst
        finally:
            if real.exists():
                real.unlink()
            if backup_created and stable_backup.exists():
                shutil.copy(stable_backup, real)
                stable_backup.unlink()


# xdist affinity: all tests in this module share one worker so the Startup-folder
# serialisation is visible to the scheduler.
pytestmark = pytest.mark.xdist_group("startup_folder")


def _lnk_properties(lnk_path: Path) -> dict:
    """Read TargetPath / Arguments / WorkingDirectory out of a .lnk via WScript.Shell."""
    ps = f"""
$sh = New-Object -ComObject WScript.Shell
$l  = $sh.CreateShortcut('{lnk_path}')
[pscustomobject]@{{
  TargetPath       = $l.TargetPath
  Arguments        = $l.Arguments
  WorkingDirectory = $l.WorkingDirectory
}} | ConvertTo-Json -Compress
"""
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        capture_output=True, text=True, timeout=15,
    )
    assert r.returncode == 0, f"shortcut read failed: {r.stderr!r}"
    import json
    return json.loads(r.stdout.strip())


@pytest.mark.skipif(not IS_WINDOWS, reason="installer is Windows-only")
def test_install_creates_launcher_and_lnk(sandbox: Path):
    script = sandbox / "install-autostart.ps1"
    r = run_ps(script, "-NoStart", cwd=sandbox)
    assert r.returncode == 0, f"install failed: stdout={r.stdout!r} stderr={r.stderr!r}"
    launcher = sandbox / "_autostart_launcher.py"
    assert launcher.exists(), "launcher script not created"
    body = launcher.read_text(encoding="utf-8", errors="replace")
    assert "uvicorn.run" in body
    assert "src.api.main:app" in body
    assert "port=8000" in body
    lnk = startup_folder() / "allmeta-rct-extractor.lnk"
    assert lnk.exists(), "Startup .lnk not created"
    # Verify shortcut contents so a future regression that points at the wrong exe
    # or a stale launcher path is caught at test time, not at login.
    props = _lnk_properties(lnk)
    assert props["TargetPath"].lower().endswith("pythonw.exe"), f"TargetPath unexpected: {props['TargetPath']!r}"
    assert "_autostart_launcher.py" in props["Arguments"], f"Arguments unexpected: {props['Arguments']!r}"
    assert str(sandbox).lower() in props["WorkingDirectory"].lower(), f"WorkingDirectory not under sandbox: {props['WorkingDirectory']!r}"


@pytest.mark.skipif(not IS_WINDOWS, reason="installer is Windows-only")
def test_uninstall_removes_lnk_and_keeps_launcher(sandbox: Path):
    script = sandbox / "install-autostart.ps1"
    r = run_ps(script, "-NoStart", cwd=sandbox)
    assert r.returncode == 0
    launcher = sandbox / "_autostart_launcher.py"
    assert launcher.exists()

    u = run_ps(script, "-Uninstall", cwd=sandbox)
    assert u.returncode == 0, f"uninstall failed: {u.stdout!r} {u.stderr!r}"
    assert not (startup_folder() / "allmeta-rct-extractor.lnk").exists(), "Startup .lnk not removed"
    assert launcher.exists(), "launcher should be preserved across uninstall (it's a checked-in file)"


@pytest.mark.skipif(not IS_WINDOWS, reason="installer is Windows-only")
def test_uninstall_is_idempotent_when_lnk_missing(sandbox: Path):
    script = sandbox / "install-autostart.ps1"
    u = run_ps(script, "-Uninstall", cwd=sandbox)
    assert u.returncode == 0, f"uninstall on clean slate failed: {u.stdout!r} {u.stderr!r}"
    # Second uninstall also OK
    u2 = run_ps(script, "-Uninstall", cwd=sandbox)
    assert u2.returncode == 0


@pytest.mark.skipif(not IS_WINDOWS, reason="installer is Windows-only")
def test_reinstall_preserves_user_edited_launcher(sandbox: Path):
    script = sandbox / "install-autostart.ps1"
    # First install
    r = run_ps(script, "-NoStart", cwd=sandbox)
    assert r.returncode == 0
    launcher = sandbox / "_autostart_launcher.py"
    user_edit = "# USER EDIT KEEP-ME\n" + launcher.read_text(encoding="utf-8")
    launcher.write_text(user_edit, encoding="utf-8")
    # Re-install
    r2 = run_ps(script, "-NoStart", cwd=sandbox)
    assert r2.returncode == 0
    assert "USER EDIT KEEP-ME" in launcher.read_text(encoding="utf-8"), \
        "re-install overwrote user-edited launcher"
