#!/usr/bin/env python3
"""로컬 모델 비교 — 라이브 서버와 무관.

예시:
  python3 scripts/model_compare.py plan
  python3 scripts/model_compare.py plan --tiers fast,pro
  GEMINI_API_KEY=... python3 scripts/model_compare.py run --tier fast --section 행발
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.saenggibu.config import get_gemini_model_fast, get_gemini_model_pro  # noqa: E402
from src.saenggibu.generator import _generate_haengbal, _generate_setuk  # noqa: E402
from src.saenggibu.model_routing import plan_sample_analysis, plan_write_section, summarize_plan  # noqa: E402
from src.saenggibu.models import StudentInput  # noqa: E402

FIXTURE_PATH = ROOT / "data" / "saenggibu" / "fixtures" / "benchmark_student.json"
DEFAULT_STYLE = (
    "객관적·관찰 중심 문체. 학생 실명 대신 '학생' 사용. "
    "과장·순위·비교 표현 금지. 교육적이고 간결한 문장."
)


def _load_fixture() -> StudentInput:
    if FIXTURE_PATH.exists():
        data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        return StudentInput.from_dict(data)
    return StudentInput(
        id="bench-1",
        name="김민수",
        grade=2,
        class_num=3,
        number=5,
        gender="남",
        notes={"행발": "모둠장 경험, 발표 적극적.", "keywords": ["책임감", "협력"]},
        subjects={"과학": {"content": "실험 참여", "topic": "산화환원", "assessment_type": "탐구보고서"}},
    )


def cmd_plan(args: argparse.Namespace) -> None:
    tiers = [t.strip() for t in args.tiers.split(",") if t.strip()]
    print(f"학생 1명 · 섹션={args.section} · 과목={args.subjects}\n")
    print(f"  샘플 분석(고정): {get_gemini_model_pro()}")
    print(f"  일괄 작성(기본): {get_gemini_model_fast()}\n")

    for tier in tiers:
        model = get_gemini_model_pro() if tier == "pro" else get_gemini_model_fast()
        steps = plan_write_section(args.section, subject_count=args.subjects)
        if tier == "pro":
            steps = [type(steps[0])(s.step, model, "pro") for s in steps]
        print(f"=== 다시 쓰기/일괄 tier={tier} ({len(steps)}회) ===")
        for step in steps:
            print(f"  · {step.step}: {step.model}")
        print(f"  모델별: {summarize_plan(steps)}\n")

    sample = plan_sample_analysis()
    print("=== 샘플 분석 (항상 Pro) ===")
    for step in sample:
        print(f"  · {step.step}: {step.model}")


def _generate_section(student: StudentInput, section: str, style: str, tier: str) -> str:
    if section == "행발":
        return _generate_haengbal(student, style, tier=tier)  # type: ignore[arg-type]
    if section == "세특":
        subject = next(iter(student.subjects))
        info = student.subjects[subject]
        return _generate_setuk(student, subject, info, style, tier=tier)  # type: ignore[arg-type]
    raise SystemExit(f"지원 섹션: 행발, 세특 (현재: {section})")


def cmd_run(args: argparse.Namespace) -> None:
    from importlib import reload

    import src.saenggibu.gemini_client as gemini_mod

    reload(gemini_mod)

    student = _load_fixture()
    style = args.style or DEFAULT_STYLE
    tier = args.tier

    print(f"tier={tier} section={args.section}")
    steps = plan_write_section(args.section)
    model = get_gemini_model_pro() if tier == "pro" else get_gemini_model_fast()
    for step in steps:
        print(f"  → {step.step}: {model}")

    from src.saenggibu.gemini_client import clear_usage_log, summarize_usage_log

    print("\n생성 중...\n")
    clear_usage_log()
    text = _generate_section(student, args.section, style, tier)
    print("--- 결과 ---")
    print(text)
    print("---")
    print(f"글자 수: {len(text)}")

    usage = summarize_usage_log()
    totals = usage["totals"]
    if totals["calls"]:
        print(
            f"\n토큰: 입력 {totals['prompt_tokens']:,} · "
            f"출력 {totals['output_tokens']:,} · 합계 {totals['total_tokens']:,}"
        )


def cmd_info(_: argparse.Namespace) -> None:
    print(
        json.dumps(
            {
                "sample_analysis_model": get_gemini_model_pro(),
                "default_write_model": get_gemini_model_fast(),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="생기부 Gemini 모델 로컬 실험")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="호출 계획 (키 불필요)")
    p_plan.add_argument("--tiers", default="fast,pro")
    p_plan.add_argument("--section", default="행발")
    p_plan.add_argument("--subjects", type=int, default=1)
    p_plan.set_defaults(func=cmd_plan)

    p_run = sub.add_parser("run", help="실제 생성 1회 (GEMINI_API_KEY 필요)")
    p_run.add_argument("--tier", default="fast", choices=["fast", "pro"])
    p_run.add_argument("--section", default="행발", choices=["행발", "세특"])
    p_run.add_argument("--style", default="")
    p_run.set_defaults(func=cmd_run)

    p_info = sub.add_parser("info", help="현재 모델 설정")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
