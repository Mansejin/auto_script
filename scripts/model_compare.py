#!/usr/bin/env python3
"""로컬 모델 확인 — 생기부 작성은 Pro 고정.

  python3 scripts/model_compare.py plan
  GEMINI_API_KEY=... python3 scripts/model_compare.py run --section 행발
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.saenggibu.config import get_gemini_model_pro  # noqa: E402
from src.saenggibu.generator import _generate_haengbal, _generate_setuk  # noqa: E402
from src.saenggibu.model_routing import plan_sample_analysis, plan_write_section  # noqa: E402
from src.saenggibu.models import StudentInput  # noqa: E402

FIXTURE_PATH = ROOT / "data" / "saenggibu" / "fixtures" / "benchmark_student.json"
DEFAULT_STYLE = "객관적·관찰 중심 문체."


def _load_fixture() -> StudentInput:
    if FIXTURE_PATH.exists():
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        return StudentInput.from_dict(data)
    return StudentInput(id="bench-1", name="김민수", grade=2, class_num=1, number=1, notes={"행발": "메모"})


def cmd_plan(_: argparse.Namespace) -> None:
    print(f"Gemini 모델: {get_gemini_model_pro()}\n")
    for step in plan_write_section("행발"):
        print(f"  · {step.step}: {step.model}")
    print("\n샘플 분석:")
    for step in plan_sample_analysis():
        print(f"  · {step.step}: {step.model}")


def cmd_run(args: argparse.Namespace) -> None:
    from src.saenggibu.gemini_client import clear_usage_log, summarize_usage_log

    student = _load_fixture()
    style = args.style or DEFAULT_STYLE
    print(f"section={args.section} model={get_gemini_model_pro()}\n")
    clear_usage_log()
    if args.section == "행발":
        text = _generate_haengbal(student, style)
    elif args.section == "세특":
        subject = next(iter(student.subjects))
        text = _generate_setuk(student, subject, student.subjects[subject], style)
    else:
        raise SystemExit("지원: 행발, 세특")
    print(text)
    usage = summarize_usage_log()["totals"]
    if usage["calls"]:
        print(f"\n토큰 합계: {usage['total_tokens']:,}")


def cmd_info(_: argparse.Namespace) -> None:
    print(json.dumps({"model": get_gemini_model_pro()}, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan").set_defaults(func=cmd_plan)
    p_run = sub.add_parser("run")
    p_run.add_argument("--section", default="행발", choices=["행발", "세특"])
    p_run.add_argument("--style", default="")
    p_run.set_defaults(func=cmd_run)
    sub.add_parser("info").set_defaults(func=cmd_info)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
