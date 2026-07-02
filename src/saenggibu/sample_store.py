from __future__ import annotations

import json
from pathlib import Path

from .config import SAMPLES_DIR, ensure_data_dirs
from .io_utils import load_json, read_table_file, save_json
from .models import SampleRecord, new_id
from .document_import import parse_docx_records, parse_xlsx_records


def _index_path() -> Path:
    return SAMPLES_DIR / "index.json"


def _load_index() -> list[dict]:
    path = _index_path()
    if not path.exists():
        return []
    return load_json(path)


def _save_index(items: list[dict]) -> None:
    save_json(_index_path(), items)


def list_samples() -> list[SampleRecord]:
    ensure_data_dirs()
    return [SampleRecord.from_dict(item) for item in _load_index()]


def get_sample(sample_id: str) -> SampleRecord | None:
    for sample in list_samples():
        if sample.id == sample_id:
            return sample
    return None


def add_sample(record: SampleRecord) -> SampleRecord:
    ensure_data_dirs()
    items = _load_index()
    items.append(record.to_dict())
    _save_index(items)
    save_json(SAMPLES_DIR / f"{record.id}.json", record.to_dict())
    return record


def import_json_file(path: Path) -> SampleRecord:
    data = load_json(path)
    if isinstance(data, list):
        raise ValueError("JSON 배열은 import-dir로 처리하세요. 단일 객체 파일만 지원합니다.")
    record = SampleRecord.from_dict(data)
    record.id = record.id or new_id("sample")
    record.source_file = str(path)
    return add_sample(record)


def import_tsv_file(path: Path) -> SampleRecord:
    rows = read_table_file(path)
    if not rows:
        raise ValueError(f"빈 표 파일: {path}")

    sections: dict[str, object] = {"행발": "", "세특": {}, "창체": {}}
    label = path.stem
    grade: int | None = None
    school_year = ""

    for row in rows:
        section = row.get("영역", row.get("section", "")).strip()
        subject = row.get("과목", row.get("subject", "")).strip()
        content = row.get("내용", row.get("content", row.get("text", ""))).strip()
        if row.get("label"):
            label = row["label"]
        if row.get("grade"):
            try:
                grade = int(row["grade"])
            except ValueError:
                pass
        if row.get("school_year"):
            school_year = row["school_year"]

        if not content:
            continue

        if section in ("행발", "행동특성", "행동특성 및 종합의견"):
            sections["행발"] = content
        elif section in ("세특", "세부능력", "세부능력 및 특기사항"):
            if subject:
                cast = sections["세특"]
                assert isinstance(cast, dict)
                cast[subject] = content
        elif section in ("창체", "창의적 체험활동"):
            subsection = row.get("소분류", row.get("subsection", "자율")).strip() or "자율"
            cast = sections["창체"]
            assert isinstance(cast, dict)
            cast[subsection] = content
        elif subject:
            cast = sections["세특"]
            assert isinstance(cast, dict)
            cast[subject] = content
        else:
            sections["행발"] = content

    record = SampleRecord(
        id=new_id("sample"),
        label=label,
        grade=grade,
        school_year=school_year,
        sections=sections,
        source_file=str(path),
    )
    return add_sample(record)


def import_path(path: Path) -> list[SampleRecord]:
    if path.is_dir():
        imported: list[SampleRecord] = []
        for child in sorted(path.iterdir()):
            if child.name.startswith("students"):
                continue
            if child.suffix.lower() in {".json", ".tsv", ".csv", ".xlsx", ".docx"}:
                imported.extend(import_path(child))
        return imported

    suffix = path.suffix.lower()
    if suffix == ".json":
        return [import_json_file(path)]
    if suffix in {".tsv", ".csv"}:
        return [import_tsv_file(path)]
    if suffix == ".xlsx":
        return [add_sample(record) for record in parse_xlsx_records(path)]
    if suffix == ".docx":
        return [add_sample(record) for record in parse_docx_records(path)]
    raise ValueError(
        f"지원하지 않는 형식: {path.suffix} ({path.name}). "
        "xlsx, docx, tsv, csv, json 을 사용하세요."
    )
