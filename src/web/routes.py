from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from src.saenggibu.generator import generate_for_student, run_batch
from src.saenggibu.models import StudentInput
from src.saenggibu.pattern_analyzer import analyze_and_save, load_patterns
from src.saenggibu.sample_store import import_path, list_samples
from src.saenggibu.upload_formats import SAMPLE_EXTENSIONS, STUDENT_EXTENSIONS, check_upload_extension
from src.saenggibu.student_store import (
    add_student,
    get_student,
    import_students_file,
    list_students,
    save_student,
)
from src.web.auth import AdminSession, SESSION_COOKIE, create_session_token, verify_password, verify_session_token

router = APIRouter(prefix="/api")
logger = logging.getLogger("sgb.web")


class LoginRequest(BaseModel):
    password: str


class StudentCreateRequest(BaseModel):
    name: str
    grade: int
    class_num: int
    number: int
    gender: str = ""
    haengbal_notes: str = ""
    keywords: list[str] = Field(default_factory=list)
    subjects: dict[str, dict[str, Any]] = Field(default_factory=dict)
    changche: dict[str, str] = Field(default_factory=dict)


class RunRequest(BaseModel):
    student_id: str | None = None
    status: str = "pending"
    sections: list[str] | None = None
    limit: int | None = None


def _extract_token(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(SESSION_COOKIE, "")


def require_admin(request: Request) -> AdminSession:
    token = _extract_token(request)
    if not verify_session_token(token):
        raise HTTPException(status_code=401, detail="관리자 로그인이 필요합니다.")
    return AdminSession(token=token)


@router.post("/auth/login")
def login(payload: LoginRequest) -> dict[str, str]:
    if not verify_password(payload.password):
        raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다.")
    token = create_session_token()
    return {"token": token}


@router.get("/auth/me")
def auth_me(session: AdminSession = Depends(require_admin)) -> dict[str, bool]:
    return {"ok": True, "admin": True}


@router.get("/samples")
def api_samples_list(_: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    samples = list_samples()
    return {"samples": [s.to_dict() for s in samples], "count": len(samples)}


@router.post("/samples/import")
async def api_samples_import(
    file: UploadFile = File(...),
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    try:
        check_upload_extension(file.filename, SAMPLE_EXTENSIONS)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    suffix = Path(file.filename or "upload").suffix.lower() or ".json"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        imported = import_path(tmp_path)
        return {"imported": len(imported), "samples": [s.to_dict() for s in imported]}
    except ValueError as exc:
        logger.warning("samples import failed: %s (%s)", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("samples import error: %s", file.filename)
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/analyze")
def api_analyze(use_gemini: bool = False, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    return analyze_and_save(use_gemini=use_gemini)


@router.get("/patterns")
def api_patterns(_: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    patterns = load_patterns()
    if not patterns:
        raise HTTPException(status_code=404, detail="패턴이 없습니다. analyze를 먼저 실행하세요.")
    return patterns


@router.get("/students")
def api_students_list(status: str | None = None, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    students = list_students(status=status)
    return {"students": [s.to_dict() for s in students], "count": len(students)}


@router.get("/students/{student_id}")
def api_student_show(student_id: str, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    student = get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    return student.to_dict()


@router.post("/students")
def api_student_create(payload: StudentCreateRequest, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    student = StudentInput(
        id="",
        name=payload.name,
        grade=payload.grade,
        class_num=payload.class_num,
        number=payload.number,
        gender=payload.gender,
        notes={"행발": payload.haengbal_notes, "keywords": payload.keywords},
        subjects=payload.subjects,
        changche=payload.changche,
    )
    return add_student(student).to_dict()


@router.post("/students/import")
async def api_students_import(
    file: UploadFile = File(...),
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    try:
        check_upload_extension(file.filename, STUDENT_EXTENSIONS)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    suffix = Path(file.filename or "upload").suffix.lower() or ".tsv"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        imported = import_students_file(tmp_path)
        return {"imported": len(imported), "students": [s.to_dict() for s in imported]}
    except ValueError as exc:
        logger.warning("students import failed: %s (%s)", file.filename, exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("students import error: %s", file.filename)
        raise HTTPException(status_code=500, detail=f"서버 오류: {exc}") from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@router.post("/students/{student_id}/reset")
def api_student_reset(student_id: str, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    student = get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    student.status = "pending"
    student.generated = {}
    student.error_message = ""
    save_student(student)
    return {"id": student.id, "status": student.status}


@router.post("/run")
def api_run(payload: RunRequest, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    sections = payload.sections

    if payload.student_id:
        student = get_student(payload.student_id)
        if not student:
            raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
        updated = generate_for_student(student, sections=sections)
        return {"mode": "single", "student": updated.to_dict()}

    students = list_students(status=payload.status or "pending")
    if payload.limit:
        students = students[: payload.limit]
    if not students:
        return {"mode": "batch", "processed": 0, "errors": [], "results": []}

    return {"mode": "batch", **run_batch(students, sections=sections, continue_on_error=True)}
