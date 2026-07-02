"""엑셀 생기부 파일을 샘플 JSON으로 변환."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from src.saenggibu.models import SampleRecord, new_id
from src.saenggibu.sample_store import add_sample


def _char_count(text: str) -> int:
    return len(re.sub(r"\s+", "", text))


def parse_xlsx(path: Path, label: str) -> list[dict]:
    records: list[dict] = []
    xl = pd.ExcelFile(path)
    for sheet in xl.sheet_names:
        df = pd.read_excel(path, sheet_name=sheet, header=None)
        for row in df.itertuples(index=False):
            vals = ["" if pd.isna(x) else str(x).strip() for x in row]
            if len(vals) < 3:
                continue
            content = ""
            name = ""

            if vals[0].isdigit() and vals[1] and not vals[1].isdigit() and len(vals[1]) <= 6:
                name = vals[1]
                content = max(vals[2:], key=_char_count, default="")
            elif len(vals) > 3 and vals[0].isdigit() and vals[1].isdigit() and vals[2]:
                name = vals[2]
                content = vals[3] if len(vals) > 3 else ""

            if not name or _char_count(content) < 50:
                continue

            records.append(
                {
                    "label": f"{label}_{sheet}_{name}",
                    "student_name": name,
                    "sheet": sheet,
                    "content": content,
                    "chars": _char_count(content),
                }
            )
    return records


def import_xlsx_dir(path: Path) -> list[SampleRecord]:
    mapping = {
        "__A-1_________ea56.xlsx": "윤사A-1",
        "__B_________c899.xlsx": "윤사B",
        "__B_____ba2a.xlsx": "생윤B",
        "__D-1_____ebf8.xlsx": "생윤D-1",
        "___-___302__e163.xlsx": "논술302",
        "___-___307__6c1f.xlsx": "고윤307",
        "___-___310__22af.xlsx": "윤사310",
        "________201__0c06.xlsx": "현사윤201",
    }
    imported: list[SampleRecord] = []
    for fname, subject in mapping.items():
        fpath = path / fname
        if not fpath.exists():
            continue
        for item in parse_xlsx(fpath, subject):
            record = SampleRecord(
                id=new_id("sample"),
                label=item["label"],
                grade=2 if "2학년" in subject or subject in ("윤사A-1", "윤사B") else 3,
                school_year="",
                sections={"세특": {subject.split("(")[0] if "(" in subject else subject: item["content"]}},
                source_file=str(fpath),
            )
            imported.append(add_sample(record))
    return imported


if __name__ == "__main__":
    upload = Path("/home/ubuntu/.cursor/projects/workspace/uploads")
    items = import_xlsx_dir(upload)
    print(f"imported {len(items)} samples")
