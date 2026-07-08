#!/usr/bin/env python3
"""로컬 모델·비용 실험 — 라이브 서버와 무관하게 프로필 비교.

예시:
  python3 scripts/model_compare.py plan
  python3 scripts/model_compare.py plan --profiles split,flash,pro
  GEMINI_API_KEY=... python3 scripts/model_compare.py run --profile flash --section 행발
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

from src.saenggibu.config import (  # noqa: E402
    get_gemini_model_fast,
    get_gemini_model_pro,
    get_gemini_model_profile,
    skip_gemini_proofread,
)
from src.saenggibu.generator import _generate_haengbal, _generate_setuk, _system_prompt  # noqa: E402
from src.saenggibu.model_routing import plan_write_section, summarize_plan  # noqa: E402
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
        notes={
            "행발": "모둠장 경험, 발표 적극적. 과제 완성도 높음.",
            "keywords": ["책임감", "협력", "성실"],
        },
        subjects={
            "과학": {
                "content": "산화환원 반응 실험에서 변화량 측정과 오차 분석에 참여",
                "topic": "산화환원",
                "assessment_type": "탐구보고서",
            }
        },
        changche={"봉사": "도서관 정리 봉사 4회"},
    )


def cmd_plan(args: argparse.Namespace) -> None:
    profiles = [p.strip() for p in args.profiles.split(",") if p.strip()]
    skip = args.skip_proofread or skip_gemini_proofread()
    print(f"학생 1명 · 섹션={args.section} · 과목={args.subjects} · 맞춤법={'끔' if skip else '켬'}\n")
    print(f"현재 .env 프로필: {get_gemini_model_profile()}")
    print(f"  Pro:   {get_gemini_model_pro()}")
    print(f"  Flash: {get_gemini_model_fast()}\n")

    for profile in profiles:
        steps = plan_write_section(
            args.section,
            subject_count=args.subjects,
            profile=profile,
            skip_proofread=skip,
        )
        counts = summarize_plan(steps)
        print(f"=== profile: {profile} ({len(steps)}회 호출) ===")
        for step in steps:
            print(f"  · {step.step}: {step.model}")
        print(f"  모델별: {counts}\n")


def _generate_section(student: StudentInput, section: str, style: str) -> str:
    if section == "행발":
        return _generate_haengbal(student, style)
    if section == "세특":
        subject = next(iter(student.subjects))
        info = student.subjects[subject]
        return _generate_setuk(student, subject, info, style)
    raise SystemExit(f"지원 섹션: 행발, 세특 (현재: {section})")


def cmd_run(args: argparse.Namespace) -> None:
    os.environ["GEMINI_MODEL_PROFILE"] = args.profile
    if args.skip_proofread:
        os.environ["GEMINI_SKIP_PROOFREAD"] = "1"

    # Re-read profile after env override
    from importlib import reload

    import src.saenggibu.config as config_mod
    import src.saenggibu.gemini_client as gemini_mod

    reload(config_mod)
    reload(gemini_mod)

    clear_usage_log = gemini_mod.clear_usage_log
    summarize_usage_log = gemini_mod.summarize_usage_log

    student = _load_fixture()
    style = args.style or DEFAULT_STYLE

    print(f"profile={args.profile} section={args.section} skip_proofread={args.skip_proofread}")
    steps = plan_write_section(args.section, subject_count=args.subjects, profile=args.profile)
    for step in steps:
        print(f"  → {step.step}: {step.model}")

    print("\n생성 중...\n")
    clear_usage_log()
    text = _generate_section(student, args.section, style)
    print("--- 결과 ---")
    print(text)
    print("---")
    print(f"글자 수: {len(text)} · 바이트(cp949): {len(text.encode('cp949', errors='replace'))}")

    usage = summarize_usage_log()
    totals = usage["totals"]
    if totals["calls"]:
        print(
            f"\n토큰 사용량 (API usage_metadata, {totals['calls']}회 호출)"
        )
        print(
            f"  입력(prompt): {totals['prompt_tokens']:,} · "
            f"출력(candidates): {totals['output_tokens']:,} · "
            f"합계: {totals['total_tokens']:,}"
        )
        if totals["thoughts_tokens"]:
            print(f"  thinking: {totals['thoughts_tokens']:,}")
        for model, bucket in usage["by_model"].items():
            print(
                f"  · {model}: 입력 {bucket['prompt_tokens']:,} / "
                f"출력 {bucket['output_tokens']:,} / 합계 {bucket['total_tokens']:,}"
            )
        if args.json:
            print("\n" + json.dumps(usage, ensure_ascii=False, indent=2))
    else:
        print("\n토큰 사용량: API 응답에 usage_metadata가 없습니다.")


def cmd_info(_: argparse.Namespace) -> None:
    print(json.dumps(
        {
            "profile": get_gemini_model_profile(),
            "pro": get_gemini_model_pro(),
            "fast": get_gemini_model_fast(),
            "skip_proofread": skip_gemini_proofread(),
            "env_local": (ROOT / ".env.local").exists(),
        },
        ensure_ascii=False,
        indent=2,
    ))


def main() -> None:
    parser = argparse.ArgumentParser(description="생기부 Gemini 모델 프로필 로컬 실험")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_plan = sub.add_parser("plan", help="프로필별 API 호출 계획 (키 불필요)")
    p_plan.add_argument("--profiles", default="split,flash,pro")
    p_plan.add_argument("--section", default="행발")
    p_plan.add_argument("--subjects", type=int, default=1)
    p_plan.add_argument("--skip-proofread", action="store_true")
    p_plan.set_defaults(func=cmd_plan)

    p_run = sub.add_parser("run", help="실제 생성 1회 (GEMINI_API_KEY 필요)")
    p_run.add_argument("--profile", default="split", choices=["split", "flash", "pro"])
    p_run.add_argument("--section", default="행발", choices=["행발", "세특"])
    p_run.add_argument("--subjects", type=int, default=1)
    p_run.add_argument("--skip-proofread", action="store_true")
    p_run.add_argument("--style", default="")
    p_run.add_argument("--json", action="store_true", help="토큰 사용량 상세 JSON 출력")
    p_run.set_defaults(func=cmd_run)

    p_info = sub.add_parser("info", help="현재 .env / .env.local 설정 출력")
    p_info.set_defaults(func=cmd_info)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
