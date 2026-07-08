"""로컬 개발용 더미 학생 시드 (SGB_DEV=1 일 때만)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from .config import ROOT, is_dev_mode
from .models import StudentInput
from .student_store import get_student, save_student

logger = logging.getLogger(__name__)

DEV_DEMO_ID = "dev-demo"
FIXTURE_PATH = ROOT / "data" / "saenggibu" / "fixtures" / "dev_demo_student.json"


def seed_dev_demo_student(*, force: bool = False) -> bool:
    """로컬 테스트용 작성 완료 학생을 1명 넣는다. 이미 있으면 건너뜀."""
    if not is_dev_mode():
        return False
    if not FIXTURE_PATH.is_file():
        logger.warning("dev demo fixture missing: %s", FIXTURE_PATH)
        return False

    existing = get_student(DEV_DEMO_ID)
    if existing and existing.generated and not force:
        return False

    raw = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    student = StudentInput.from_dict(raw)
    student.id = DEV_DEMO_ID
    save_student(student)
    logger.info("dev demo student seeded: %s (%s)", DEV_DEMO_ID, student.display_name)
    return True
