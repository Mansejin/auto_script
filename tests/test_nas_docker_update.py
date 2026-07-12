from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "nas-docker-update.sh"


def run_command(args: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or result.stdout
    return result


def git(cwd: Path, *args: str) -> None:
    run_command(
        [
            "git",
            "-c",
            "user.name=Test User",
            "-c",
            "user.email=test@example.com",
            *args,
        ],
        cwd=cwd,
    )


def test_bootstrap_reexec_preserves_old_rev_for_deploy_scope(tmp_path: Path) -> None:
    if not shutil.which("git"):
        return

    remote = tmp_path / "remote.git"
    source = tmp_path / "source"
    deploy = tmp_path / "deploy"
    script_text = SCRIPT.read_text()

    run_command(["git", "init", "--bare", "--initial-branch=main", str(remote)], cwd=tmp_path)
    run_command(["git", "init", "--initial-branch=main", str(source)], cwd=tmp_path)
    (source / "scripts").mkdir()
    (source / "src").mkdir()
    (source / "scripts" / "nas-docker-update.sh").write_text(script_text)
    (source / "src" / "app.py").write_text("VERSION = 'a'\n")
    git(source, "add", ".")
    git(source, "commit", "-m", "initial")
    git(source, "remote", "add", "origin", str(remote))
    git(source, "push", "-u", "origin", "main")

    run_command(["git", "clone", str(remote), str(deploy)], cwd=tmp_path)

    (source / "src" / "app.py").write_text("VERSION = 'b'\n")
    git(source, "add", "src/app.py")
    git(source, "commit", "-m", "backend change")
    git(source, "push", "origin", "main")

    fake_docker = tmp_path / "docker"
    fake_docker.write_text("#!/bin/sh\nexit 0\n")
    fake_docker.chmod(0o755)
    bootstrap_script = tmp_path / "sgb-deploy.sh"
    bootstrap_script.write_text(script_text)

    env = os.environ.copy()
    env.update(
        {
            "DOCKER_BIN": str(fake_docker),
            "SGB_BRANCH": "main",
            "SGB_DOCKER_SUDO": "0",
            "SGB_REPO_DIR": str(deploy),
        }
    )
    result = run_command(["sh", str(bootstrap_script), "--pull-only"], cwd=tmp_path, env=env)
    output = result.stdout + result.stderr

    assert "re-exec deploy script from repo (post git sync)" in output
    assert "deploy scope: rebuild" in output
    assert "deploy scope: none" not in output
