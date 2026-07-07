from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def test_admin_js_has_valid_syntax() -> None:
    js_path = Path(__file__).resolve().parents[1] / "web" / "admin" / "js" / "admin.js"
    node = shutil.which("node")
    if not node:
        return
    result = subprocess.run([node, "--check", str(js_path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or result.stdout
