from __future__ import annotations

import csv
import io
import re
from typing import Any

from .config import COLUMNS
from .models import ScriptPart, ScriptRow
from .sheets_client import find_header_row, open_worksheet


def _normalize_row(values: list[str]) -> ScriptRow:
    padded = (values + [""] * len(COLUMNS))[: len(COLUMNS)]
    return ScriptRow(
        sheet_row=0,
        대본=padded[0].strip(),
        장면=padded[1].strip(),
        사이즈=padded[2].strip(),
        자막=padded[3].strip(),
        코멘트=padded[4].strip(),
    )


def read_script() -> tuple[int, list[ScriptRow]]:
    ws = open_worksheet()
    all_values = ws.get_all_values()
    header_row = find_header_row(all_values)
    data_start = header_row + 1

    rows: list[ScriptRow] = []
    for idx, raw in enumerate(all_values[data_start - 1 :], start=data_start):
        if not any(cell.strip() for cell in raw):
            continue
        row = _normalize_row(raw)
        row.sheet_row = idx
        rows.append(row)
    return header_row, rows


def group_by_part(rows: list[ScriptRow]) -> list[ScriptPart]:
    parts: list[ScriptPart] = []
    current_name = ""
    current_rows: list[ScriptRow] = []
    start_row = 0

    for row in rows:
        scene = row.장면.strip()
        if scene and scene != current_name:
            if current_rows:
                parts.append(
                    ScriptPart(
                        name=current_name or "(미분류)",
                        start_row=start_row,
                        end_row=current_rows[-1].sheet_row,
                        rows=current_rows,
                    )
                )
            current_name = scene
            current_rows = [row]
            start_row = row.sheet_row
        else:
            if not current_rows:
                current_name = scene or "(미분류)"
                start_row = row.sheet_row
            current_rows.append(row)

    if current_rows:
        parts.append(
            ScriptPart(
                name=current_name or "(미분류)",
                start_row=start_row,
                end_row=current_rows[-1].sheet_row,
                rows=current_rows,
            )
        )
    return parts


def find_part(rows: list[ScriptRow], query: str) -> ScriptPart | None:
    query_lower = query.strip().lower()
    for part in group_by_part(rows):
        if query_lower in part.name.lower():
            return part
    return None


def script_to_dict(header_row: int, rows: list[ScriptRow]) -> dict[str, Any]:
    return {
        "header_row": header_row,
        "total_rows": len(rows),
        "parts": [part.to_dict() for part in group_by_part(rows)],
        "rows": [row.to_dict() for row in rows],
    }


def update_rows(updates: list[dict[str, Any]]) -> list[int]:
    ws = open_worksheet()
    changed: list[int] = []

    for item in updates:
        row_num = int(item["row"])
        current = ws.row_values(row_num)
        padded = (current + [""] * len(COLUMNS))[: len(COLUMNS)]
        row = _normalize_row(padded)
        row.sheet_row = row_num

        for col_name in COLUMNS:
            if col_name in item and item[col_name] is not None:
                setattr(row, col_name, str(item[col_name]))

        ws.update(f"A{row_num}:E{row_num}", [row.to_values()], value_input_option="USER_ENTERED")
        changed.append(row_num)
    return changed


def replace_range(start_row: int, end_row: int, new_rows: list[ScriptRow]) -> dict[str, Any]:
    ws = open_worksheet()
    delete_count = max(0, end_row - start_row + 1)

    if delete_count > 0:
        ws.delete_rows(start_row, end_row)

    if new_rows:
        values = [row.to_values() for row in new_rows]
        ws.insert_rows(values, row=start_row, value_input_option="USER_ENTERED")

    return {
        "replaced_start": start_row,
        "replaced_end": end_row,
        "deleted_count": delete_count,
        "inserted_count": len(new_rows),
    }


def replace_part(part_query: str, new_rows: list[ScriptRow]) -> dict[str, Any]:
    _, rows = read_script()
    part = find_part(rows, part_query)
    if not part:
        raise ValueError(f"'{part_query}' 파트를 찾을 수 없습니다. `list-parts`로 확인하세요.")
    return replace_range(part.start_row, part.end_row, new_rows)


def parse_table_text(text: str) -> list[ScriptRow]:
    text = text.strip()
    if not text:
        return []

    if "|" in text and "\n" in text:
        return _parse_markdown_table(text)
    return _parse_delimited(text)


def _parse_delimited(text: str) -> list[ScriptRow]:
    sample = text.splitlines()[0] if text.splitlines() else ""
    delimiter = "\t" if "\t" in sample else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    parsed_rows = list(reader)
    if not parsed_rows:
        return []

    start_idx = 0
    first = [cell.strip() for cell in parsed_rows[0]]
    if first[: len(COLUMNS)] == list(COLUMNS) or ("대본" in first and "장면" in first):
        start_idx = 1

    rows: list[ScriptRow] = []
    for raw in parsed_rows[start_idx:]:
        if not any(cell.strip() for cell in raw):
            continue
        row = _normalize_row(raw)
        row.sheet_row = 0
        rows.append(row)
    return rows


def _parse_markdown_table(text: str) -> list[ScriptRow]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    data_lines = [line for line in lines if not re.match(r"^\|?[\s\-:|]+\|?$", line)]
    rows: list[ScriptRow] = []
    for line in data_lines:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not any(cells):
            continue
        if cells[0] == "대본" or (len(cells) > 1 and cells[1] == "장면"):
            continue
        row = _normalize_row(cells)
        row.sheet_row = 0
        rows.append(row)
    return rows


def diff_rows(old_rows: list[ScriptRow], new_rows: list[ScriptRow]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    max_len = max(len(old_rows), len(new_rows))

    for i in range(max_len):
        old = old_rows[i] if i < len(old_rows) else None
        new = new_rows[i] if i < len(new_rows) else None

        if old is None and new is not None:
            changes.append({"type": "add", "index": i + 1, "new": new.to_dict()})
            continue
        if new is None and old is not None:
            changes.append({"type": "delete", "index": i + 1, "old": old.to_dict()})
            continue
        if old is None or new is None:
            continue

        field_changes: dict[str, dict[str, str]] = {}
        for col in COLUMNS:
            old_val = getattr(old, col)
            new_val = getattr(new, col)
            if old_val != new_val:
                field_changes[col] = {"old": old_val, "new": new_val}

        if field_changes:
            changes.append(
                {
                    "type": "modify",
                    "row": old.sheet_row,
                    "index": i + 1,
                    "changes": field_changes,
                }
            )
    return changes
