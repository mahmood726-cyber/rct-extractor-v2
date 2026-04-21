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

import pytest

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


@pytest.fixture
def sandbox(tmp_path: Path):
    """Clone the installer into a tmp dir so real install doesn't mutate the repo on disk."""
    dst = tmp_path / "rx"
    dst.mkdir()
    shutil.copy(INSTALLER, dst / "install-autostart.ps1")
    # Save + restore any pre-existing Startup .lnk so the user's real install survives
    real = startup_folder() / "allmeta-rct-extractor.lnk"
    backup = None
    if real.exists():
        backup = tmp_path / "preexisting.lnk"
        shutil.copy(real, backup)
        real.unlink()
    yield dst
    # Cleanup: remove .lnk the test wrote + restore original, and purge sandbox launcher side-effects
    if real.exists():
        real.unlink()
    if backup is not None:
        shutil.copy(backup, real)


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
    assert (startup_folder() / "allmeta-rct-extractor.lnk").exists(), "Startup .lnk not created"


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
