from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from src.saenggibu.config import get_gemini_model
from src.saenggibu.generator import generate_for_student, run_batch
from src.saenggibu.inspector import inspect_text as run_inspect_text
from src.saenggibu.inspector.issues import report_to_dict
from src.saenggibu.inspector.runner import (
    inspect_all_students,
    inspect_student_by_id,
    inspect_students_by_ids,
)
from src.saenggibu.models import StudentInput
from src.saenggibu.pattern_analyzer import analyze_and_save, load_patterns, update_style_guide
from src.saenggibu.sample_store import (
    delete_all_samples,
    delete_sample,
    delete_samples,
    import_path,
    list_samples,
    reconcile_sample_index,
)
from src.saenggibu.student_parser import parse_and_save, parse_file_to_student, parse_text_to_student
from src.saenggibu.upload_formats import SAMPLE_EXTENSIONS, STUDENT_EXTENSIONS, check_upload_extension
from src.saenggibu.usage import usage_summary
from src.saenggibu.write_sections import normalize_write_sections, students_needing_section
from src.saenggibu.student_store import (
    add_student,
    delete_all_students,
    delete_student,
    delete_students,
    export_students_xlsx,
    get_student,
    import_students_file,
    list_students,
    reset_all_generated,
    reset_generated_for_students,
    reset_student_generated,
    save_student,
)
from src.web.auth import AdminSession, SESSION_COOKIE, admin_auth_configured, create_session_token, verify_password, verify_session_token

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
    write_targets: list[str] = Field(default_factory=list)


class RunRequest(BaseModel):
    student_id: str | None = None
    status: str = "pending"
    sections: list[str] | None = None
    limit: int | None = None


class ParseStudentRequest(BaseModel):
    text: str


class StyleGuideUpdate(BaseModel):
    style_guide: str


class BulkDeleteSamplesRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)


class BulkStudentIdsRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)


class StudentUpdateRequest(BaseModel):
    generated: dict[str, Any] | None = None
    notes: dict[str, Any] | None = None
    subjects: dict[str, dict[str, Any]] | None = None
    changche: dict[str, str] | None = None
    status: str | None = None


class InspectTextRequest(BaseModel):
    text: str
    section_key: str = "본문"
    student_name: str = ""


class InspectBatchRequest(BaseModel):
    ids: list[str] = Field(default_factory=list)


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
    if not admin_auth_configured():
        raise HTTPException(
            status_code=503,
            detail="서버 설정이 완료되지 않았습니다. .env 에 ADMIN_PASSWORD 와 ADMIN_SESSION_SECRET 을 설정하세요.",
        )
    try:
        if not verify_password(payload.password):
            raise HTTPException(status_code=401, detail="비밀번호가 올바르지 않습니다.")
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        token = create_session_token()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"token": token}


@router.get("/auth/me")
def auth_me(session: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    return {
        "ok": True,
        "admin": True,
        "usage": usage_summary(),
        "gemini_model": get_gemini_model(),
    }


@router.get("/usage")
def api_usage(_: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    return usage_summary()


@router.get("/samples")
def api_samples_list(_: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    samples = list_samples()
    return {"samples": [s.to_dict() for s in samples], "count": len(samples)}


@router.post("/samples/reconcile")
def api_samples_reconcile(_: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    removed = reconcile_sample_index()
    samples = list_samples()
    return {"removed": removed, "count": len(samples), "samples": [s.to_dict() for s in samples]}


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


@router.delete("/samples/{sample_id}")
def api_samples_delete(sample_id: str, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    if not delete_sample(sample_id):
        raise HTTPException(status_code=404, detail="샘플을 찾을 수 없습니다.")
    return {"deleted": True, "id": sample_id}


@router.delete("/samples")
def api_samples_delete_all(_: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    count = delete_all_samples()
    return {"deleted": True, "count": count}


@router.post("/samples/bulk-delete")
def api_samples_bulk_delete(
    payload: BulkDeleteSamplesRequest,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    if not payload.ids:
        raise HTTPException(status_code=400, detail="삭제할 샘플을 선택하세요.")
    return delete_samples(payload.ids)


@router.post("/analyze")
def api_analyze(use_gemini: bool = False, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    return analyze_and_save(use_gemini=use_gemini)


@router.get("/patterns")
def api_patterns(_: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    patterns = load_patterns()
    if not patterns:
        raise HTTPException(status_code=404, detail="패턴이 없습니다. analyze를 먼저 실행하세요.")
    return patterns


@router.put("/patterns/style-guide")
def api_patterns_update(payload: StyleGuideUpdate, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    try:
        return update_style_guide(payload.style_guide)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/students")
def api_students_list(status: str | None = None, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    students = list_students(status=status)
    return {"students": [s.to_dict() for s in students], "count": len(students)}


@router.get("/students/export/xlsx")
def api_students_export_xlsx(_: AdminSession = Depends(require_admin)) -> Response:
    students = list_students()
    if not students:
        raise HTTPException(status_code=404, detail="보낼 학생이 없습니다.")
    if not any(s.generated for s in students):
        raise HTTPException(status_code=404, detail="작성된 생기부가 없습니다.")
    from datetime import datetime, timezone

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    content = export_students_xlsx(students)
    filename = f"saenggibu_{stamp}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/students/{student_id}/inspect")
def api_student_inspect(student_id: str, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    report = inspect_student_by_id(student_id)
    if report is None:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    return report_to_dict(report)


@router.post("/inspect/text")
def api_inspect_text(payload: InspectTextRequest, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="검사할 본문을 입력하세요.")
    report = run_inspect_text(
        text,
        section_key=payload.section_key.strip() or "본문",
        student_name=payload.student_name.strip(),
    )
    return report_to_dict(report)


@router.post("/inspect/batch")
def api_inspect_batch(
    payload: InspectBatchRequest,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    if payload.ids:
        reports, not_found = inspect_students_by_ids(payload.ids)
    else:
        reports = inspect_all_students()
        not_found = []
    summary = {
        "total": len(reports),
        "fail": sum(1 for report in reports if report.status == "fail"),
        "warn": sum(1 for report in reports if report.status == "warn"),
        "ok": sum(1 for report in reports if report.status == "ok"),
    }
    return {
        "summary": summary,
        "not_found": not_found,
        "reports": [report_to_dict(report) for report in reports],
    }


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
        notes={
            "행발": payload.haengbal_notes,
            "keywords": payload.keywords,
            "write_targets": payload.write_targets,
        },
        subjects=payload.subjects,
        changche=payload.changche,
    )
    return add_student(student).to_dict()


@router.post("/students/parse")
def api_students_parse(payload: ParseStudentRequest, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    try:
        preview = parse_text_to_student(payload.text)
        return {"preview": preview.to_dict(), "saved": False}
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/students/parse-save")
def api_students_parse_save(payload: ParseStudentRequest, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    try:
        student = parse_and_save(payload.text)
        return student.to_dict()
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/students/parse-file")
async def api_students_parse_file(
    file: UploadFile = File(...),
    save: bool = False,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    suffix = Path(file.filename or "upload").suffix.lower() or ".txt"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        student = parse_file_to_student(tmp_path)
        if save:
            return add_student(student).to_dict()
        return {"preview": student.to_dict(), "saved": False}
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        tmp_path.unlink(missing_ok=True)


@router.patch("/students/{student_id}")
def api_student_update(
    student_id: str,
    payload: StudentUpdateRequest,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    student = get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    if payload.generated is not None:
        student.generated = payload.generated
    if payload.notes is not None:
        student.notes = payload.notes
    if payload.subjects is not None:
        student.subjects = payload.subjects
    if payload.changche is not None:
        student.changche = payload.changche
    if payload.status is not None:
        student.status = payload.status
    return save_student(student).to_dict()


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
    reset_student_generated(student)
    return {"id": student.id, "status": student.status}


@router.delete("/students/{student_id}")
def api_student_delete(student_id: str, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    if not delete_student(student_id):
        raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
    return {"deleted": True, "id": student_id}


@router.delete("/students")
def api_students_delete_all(_: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    count = delete_all_students()
    return {"deleted": True, "count": count}


@router.post("/students/bulk-delete")
def api_students_bulk_delete(
    payload: BulkStudentIdsRequest,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    if not payload.ids:
        raise HTTPException(status_code=400, detail="삭제할 학생을 선택하세요.")
    return delete_students(payload.ids)


@router.post("/students/bulk-reset-generated")
def api_students_bulk_reset_generated(
    payload: BulkStudentIdsRequest,
    _: AdminSession = Depends(require_admin),
) -> dict[str, Any]:
    if not payload.ids:
        raise HTTPException(status_code=400, detail="초기화할 학생을 선택하세요.")
    return reset_generated_for_students(payload.ids)


@router.delete("/students/generated/all")
def api_students_reset_all_generated(_: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    count = reset_all_generated()
    return {"reset": True, "count": count}


@router.post("/run")
def api_run(payload: RunRequest, _: AdminSession = Depends(require_admin)) -> dict[str, Any]:
    try:
        sections = normalize_write_sections(payload.sections)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    section = sections[0]

    if payload.student_id:
        student = get_student(payload.student_id)
        if not student:
            raise HTTPException(status_code=404, detail="학생을 찾을 수 없습니다.")
        updated = generate_for_student(student, sections=sections)
        return {"mode": "single", "section": section, "student": updated.to_dict()}

    students = students_needing_section(list_students(), section)
    if payload.limit:
        students = students[: payload.limit]
    if not students:
        return {
            "mode": "batch",
            "section": section,
            "processed": 0,
            "errors": [],
            "results": [],
            "message": f"작성이 필요한 학생이 없습니다 ({section}).",
        }

    result = run_batch(students, sections=sections, continue_on_error=True)
    return {"mode": "batch", "section": section, **result}
