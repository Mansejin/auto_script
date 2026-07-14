from __future__ import annotations

import re
from pathlib import Path


def test_health_check_bypasses_maintenance_gate() -> None:
    config_path = Path(__file__).resolve().parents[1] / "docker" / "nginx.conf"
    config = config_path.read_text(encoding="utf-8")

    health_match = re.search(r"location = /health \{(?P<body>.*?)\n    \}", config, re.DOTALL)
    maintenance_match = re.search(r"location / \{", config)

    assert health_match is not None
    assert maintenance_match is not None
    assert health_match.start() < maintenance_match.start()
    assert "maintenance.on" not in health_match.group("body")
    assert "proxy_pass http://sgb_api;" in health_match.group("body")
