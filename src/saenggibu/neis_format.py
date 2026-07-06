from __future__ import annotations

import csv
import io
import re
from typing import Any

from .config import CHANGCHE_SUBSECTIONS

_CHANGCHE_HEADER_MAP = {
    "자율": frozenset({"자율", "자율활동", "창체_자율", "창체 자율"}),
    "동아리": frozenset({"동아리", "동아리활동", "창체_동아리", "창체 동아리"}),
    "봉사": frozenset({"봉사", "봉사활동", "창체_봉사", "창체 봉사"}),
    "진로": frozenset({"진로", "진로활동", "창체_진로", "창체 진로"}),
}
_BLOCK_SECTION_RE = re.compile(
    r"【\s*(.+?)\s*】\s*\n([\s\S]*?)(?=\n【|\Z)",
    re.MULTILINE,
)


def _normalize_header(value: str) -> str:
    return re.sub(r"\s+", "", value.strip().lower())


def _header_lookup(headers: list[str]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for header in headers:
        key = _normalize_header(header)
        lookup[key] = header
    return lookup


def _find_column(lookup: dict[str, str], aliases: frozenset[str]) -> str | None:
    for alias in aliases:
        hit = lookup.get(_normalize_header(alias))
        if hit:
            return hit
    return None


def _parse_tsv_rows(text: str) -> tuple[list[str], list[dict[str, str]]]:
    sample = text.strip()
    if not sample:
        raise ValueError("붙여넣은 내용이 비어 있습니다.")
    delimiter = "\t" if "\t" in sample.splitlines()[0] else ","
    reader = csv.DictReader(io.StringIO(sample), delimiter=delimiter)
    if not reader.fieldnames:
        raise ValueError("표 헤더를 찾을 수 없습니다.")
    headers = [h.strip() for h in reader.fieldnames if h and h.strip()]
    rows = [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in reader]
    rows = [row for row in rows if any(row.values())]
    if not rows:
        raise ValueError("데이터 행을 찾을 수 없습니다.")
    return headers, rows


def _is_memo_import(headers: list[str]) -> bool:
    for header in headers:
        if header.startswith("창체_"):
            return True
        norm = _normalize_header(header)
        if norm in {"행발_notes", "행발_keywords"}:
            return True
    return False


def _row_to_fields(row: dict[str, str], headers: list[str]) -> dict[str, Any]:
    lookup = _header_lookup(headers)
    memo_import = _is_memo_import(headers)
    notes: dict[str, Any] = {}
    subjects: dict[str, dict[str, Any]] = {}
    changche: dict[str, str] = {}
    generated: dict[str, Any] = {}
    meta: dict[str, Any] = {}

    for key, value in row.items():
        if not value:
            continue
        norm = _normalize_header(key)
        if norm in {"학년", "grade"}:
            meta["grade"] = int(re.sub(r"\D", "", value) or 0) or None
        elif norm in {"반", "class", "classnum", "class_num"}:
            meta["class_num"] = int(re.sub(r"\D", "", value) or 0) or None
        elif norm in {"번호", "number", "no"}:
            meta["number"] = int(re.sub(r"\D", "", value) or 0) or None
        elif norm in {"이름", "성명", "name"}:
            meta["name"] = value

    haengbal_memo_col = _find_column(lookup, frozenset({"행발_notes"}))
    if haengbal_memo_col and row.get(haengbal_memo_col):
        notes["행발"] = row[haengbal_memo_col]

    haengbal_col = _find_column(
        lookup,
        frozenset({"행발", "행동특성", "행동특성 및 종합의견", "행동특성및종합의견"}),
    )
    if haengbal_col and row.get(haengbal_col):
        value = row[haengbal_col]
        if haengbal_memo_col and haengbal_col == haengbal_memo_col:
            pass
        elif memo_import and haengbal_col == _find_column(lookup, frozenset({"행발"})):
            notes["행발"] = value
        else:
            generated["행발"] = value

    keywords_col = _find_column(lookup, frozenset({"행발_keywords", "keywords", "키워드"}))
    if keywords_col and row.get(keywords_col):
        notes["keywords"] = [part.strip() for part in re.split(r"[|;]", row[keywords_col]) if part.strip()]

    for header in headers:
        if header.startswith("세특_") or header.startswith("subject_"):
            subject = header.split("_", 1)[1].strip()
            value = row.get(header, "").strip()
            if subject and value:
                if memo_import:
                    subjects[subject] = {
                        "content": value,
                        "activities": [value],
                        "notes": value,
                    }
                else:
                    generated.setdefault("세특", {})[subject] = value

    for subsection in CHANGCHE_SUBSECTIONS:
        memo_col = _find_column(lookup, frozenset({f"창체_{subsection}"}))
        if memo_col and row.get(memo_col):
            changche[subsection] = row[memo_col]
            continue
        gen_col = _find_column(lookup, _CHANGCHE_HEADER_MAP[subsection])
        if gen_col and row.get(gen_col) and not memo_import:
            generated.setdefault("창체", {})[subsection] = row[gen_col]

    write_targets: list[str] = []
    if notes.get("행발"):
        write_targets.append("행발")
    if subjects:
        write_targets.append("세특")
    for subsection in CHANGCHE_SUBSECTIONS:
        if changche.get(subsection):
            write_targets.append(subsection)
    if write_targets:
        notes["write_targets"] = write_targets

    return {
        "meta": meta,
        "notes": notes,
        "subjects": subjects,
        "changche": changche,
        "generated": generated,
    }


def _parse_block_text(text: str) -> dict[str, Any]:
    notes: dict[str, Any] = {}
    subjects: dict[str, dict[str, Any]] = {}
    changche: dict[str, str] = {}
    generated: dict[str, Any] = {}

    matches = list(_BLOCK_SECTION_RE.finditer(text.strip()))
    if not matches:
        raise ValueError("【항목명】 형식의 구간을 찾지 못했습니다.")

    for match in matches:
        label = match.group(1).strip()
        body = match.group(2).strip()
        if not body:
            continue
        if "행동특성" in label or label == "행발":
            generated["행발"] = body
            notes["행발"] = body
        elif label.startswith("세특"):
            subject = label.split("·", 1)[-1].strip() if "·" in label else "과목"
            subjects[subject] = {"content": body, "activities": [body], "notes": body}
            generated.setdefault("세특", {})[subject] = body
        elif label.startswith("창체"):
            subsection = label.split("·", 1)[-1].strip() if "·" in label else ""
            if subsection in CHANGCHE_SUBSECTIONS:
                changche[subsection] = body
                generated.setdefault("창체", {})[subsection] = body
        elif label in CHANGCHE_SUBSECTIONS or label.endswith("활동"):
            key = label.replace("활동", "")
            if key in CHANGCHE_SUBSECTIONS:
                changche[key] = body
                generated.setdefault("창체", {})[key] = body

    write_targets: list[str] = []
    if notes.get("행발"):
        write_targets.append("행발")
    if subjects:
        write_targets.append("세특")
    for subsection in CHANGCHE_SUBSECTIONS:
        if changche.get(subsection):
            write_targets.append(subsection)
    if write_targets:
        notes["write_targets"] = write_targets

    return {
        "meta": {},
        "notes": notes,
        "subjects": subjects,
        "changche": changche,
        "generated": generated,
    }


def parse_neis_paste(text: str) -> dict[str, Any]:
    """NEIS·엑셀 붙여넣기를 학생 필드로 파싱합니다."""
    text = text.strip()
    if not text:
        raise ValueError("붙여넣은 내용이 비어 있습니다.")

    if text.startswith("【") or "【행동특성" in text or "【세특" in text or "【창체" in text:
        fields = _parse_block_text(text)
        return {"format": "block", **fields}

    headers, rows = _parse_tsv_rows(text)
    fields = _row_to_fields(rows[0], headers)
    return {"format": "tsv", "headers": headers, "row_count": len(rows), **fields}
