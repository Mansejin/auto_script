from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import JOBS_DIR, ensure_data_dirs
from .generator import generate_for_student, run_batch
from .io_utils import save_json
from .models import new_id
from .student_store import get_student, list_students
from .write_sections import normalize_write_sections, students_needing_section


@dataclass
class RunJob:
    id: str
    kind: str = "run"
    status: str = "pending"  # pending | running | done | error
    section: str = ""
    student_id: str | None = None
    limit: int | None = None
    total: int = 0
    processed: int = 0
    current_label: str = ""
    message: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, str]] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _job_path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def create_run_job(
    *,
    sections: list[str],
    student_id: str | None = None,
    limit: int | None = None,
) -> RunJob:
    ensure_data_dirs()
    section = normalize_write_sections(sections)[0]
    job = RunJob(
        id=new_id("job"),
        section=section,
        student_id=student_id,
        limit=limit,
        created_at=_now_iso(),
        updated_at=_now_iso(),
    )
    save_job(job)
    return job


def save_job(job: RunJob) -> RunJob:
    ensure_data_dirs()
    job.updated_at = _now_iso()
    save_json(_job_path(job.id), job.to_dict())
    return job


def get_job(job_id: str) -> RunJob | None:
    path = _job_path(job_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return RunJob(**data)


def execute_run_job(job_id: str) -> RunJob:
    job = get_job(job_id)
    if not job:
        raise ValueError(f"job not found: {job_id}")

    job.status = "running"
    job.message = "작성을 시작합니다."
    save_job(job)

    try:
        sections = [job.section]
        if job.student_id:
            student = get_student(job.student_id)
            if not student:
                raise ValueError("학생을 찾을 수 없습니다.")
            job.total = 1
            job.current_label = student.display_name
            save_job(job)
            updated = generate_for_student(
                student,
                sections=sections,
                progress=lambda _section, message: _update_job_progress(job_id, message, student.display_name),
            )
            job.status = "done"
            job.processed = 1
            job.result = {"mode": "single", "section": job.section, "student": updated.to_dict()}
            job.message = "완료"
            return save_job(job)

        students = students_needing_section(list_students(), job.section)
        if job.limit:
            students = students[: job.limit]
        job.total = len(students)
        save_job(job)

        if not students:
            job.status = "done"
            job.message = f"작성이 필요한 학생이 없습니다 ({job.section})."
            job.result = {
                "mode": "batch",
                "section": job.section,
                "processed": 0,
                "errors": [],
                "results": [],
            }
            return save_job(job)

        def progress(_section: str, message: str) -> None:
            _update_job_progress(job_id, message)

        result = run_batch(students, sections=sections, continue_on_error=True, progress=progress)
        job.status = "done"
        job.processed = int(result.get("processed", 0))
        job.errors = list(result.get("errors") or [])
        job.result = {"mode": "batch", "section": job.section, **result}
        job.message = "완료"
        return save_job(job)
    except Exception as exc:
        job.status = "error"
        job.message = str(exc)
        job.errors.append({"id": job.id, "error": str(exc)})
        return save_job(job)


def _update_job_progress(job_id: str, message: str, current_label: str | None = None) -> None:
    job = get_job(job_id)
    if not job:
        return
    job.message = message
    if current_label:
        job.current_label = current_label
    save_job(job)


def list_jobs(*, limit: int = 20) -> list[RunJob]:
    ensure_data_dirs()
    paths = sorted(JOBS_DIR.glob("job*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    jobs: list[RunJob] = []
    for path in paths[:limit]:
        job = get_job(path.stem)
        if job:
            jobs.append(job)
    return jobs
