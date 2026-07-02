#!/usr/bin/env python3
"""대한민국 생기부 자동 작성 CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.saenggibu.config import ensure_data_dirs
from src.saenggibu.generator import generate_for_student, run_batch
from src.saenggibu.models import StudentInput
from src.saenggibu.pattern_analyzer import analyze_and_save, load_patterns
from src.saenggibu.sample_store import import_path, list_samples
from src.saenggibu.student_store import (
    add_student,
    get_student,
    import_students_file,
    list_students,
    save_student,
)


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_samples_import(args: argparse.Namespace) -> None:
    path = Path(args.path)
    imported = import_path(path)
    _print_json({"imported": len(imported), "samples": [s.to_dict() for s in imported]})


def cmd_samples_list(_: argparse.Namespace) -> None:
    samples = list_samples()
    if not samples:
        print("등록된 샘플이 없습니다. `python sgb.py samples import data/saenggibu/examples/`")
        return
    for sample in samples:
        grade = f"{sample.grade}학년" if sample.grade else "학년미상"
        print(f"- {sample.id}: {sample.label} ({grade}) ← {sample.source_file or '직접입력'}")


def cmd_analyze(args: argparse.Namespace) -> None:
    result = analyze_and_save(use_gemini=args.gemini)
    _print_json(
        {
            "sample_count": result.get("sample_count"),
            "sections": list(result.get("sections", {}).keys()),
            "style_guide_preview": (result.get("style_guide") or "")[:500] + "...",
            "saved_to": "data/saenggibu/patterns.json",
        }
    )


def cmd_patterns_show(_: argparse.Namespace) -> None:
    patterns = load_patterns()
    if not patterns:
        raise SystemExit("패턴 파일이 없습니다. `python sgb.py analyze`를 먼저 실행하세요.")
    _print_json(patterns)


def cmd_students_import(args: argparse.Namespace) -> None:
    imported = import_students_file(Path(args.file))
    _print_json({"imported": len(imported), "students": [s.to_dict() for s in imported]})


def cmd_students_add(args: argparse.Namespace) -> None:
    student = StudentInput(
        id=args.id or "",
        name=args.name,
        grade=args.grade,
        class_num=args.class_num,
        number=args.number,
        gender=args.gender or "",
        notes={"행발": args.haengbal_notes or "", "keywords": args.keywords or []},
        subjects={},
        changche={
            "자율": args.changche_jayul or "",
            "동아리": args.changche_club or "",
            "봉사": args.changche_volunteer or "",
            "진로": args.changche_career or "",
        },
    )
    if args.subject and args.subject_notes:
        student.subjects[args.subject] = {"activities": [args.subject_notes], "traits": "", "notes": ""}

    saved = add_student(student)
    _print_json(saved.to_dict())


def cmd_students_list(args: argparse.Namespace) -> None:
    students = list_students(status=args.status)
    if args.json:
        _print_json([s.to_dict() for s in students])
        return

    if not students:
        print("등록된 학생이 없습니다.")
        return

    for student in students:
        subjects = ", ".join(student.subjects.keys()) if student.subjects else "-"
        print(
            f"- {student.id} | {student.display_name} | 상태:{student.status} | "
            f"세특:{subjects}"
        )


def cmd_students_show(args: argparse.Namespace) -> None:
    student = get_student(args.id)
    if not student:
        raise SystemExit(f"학생을 찾을 수 없습니다: {args.id}")
    _print_json(student.to_dict())


def cmd_students_reset(args: argparse.Namespace) -> None:
    student = get_student(args.id)
    if not student:
        raise SystemExit(f"학생을 찾을 수 없습니다: {args.id}")
    student.status = "pending"
    student.generated = {}
    student.error_message = ""
    save_student(student)
    _print_json({"id": student.id, "status": student.status, "message": "재작성 대기로 초기화됨"})


def cmd_run(args: argparse.Namespace) -> None:
    sections = args.sections.split(",") if args.sections else None

    if args.student:
        student = get_student(args.student)
        if not student:
            raise SystemExit(f"학생을 찾을 수 없습니다: {args.student}")
        updated = generate_for_student(student, sections=sections)
        _print_json({"id": updated.id, "status": updated.status, "generated": updated.generated})
        return

    students = list_students(status=args.status or "pending")
    if not students:
        print("작성할 학생이 없습니다. (status=pending)")
        return

    if args.limit:
        students = students[: args.limit]

    if not args.yes:
        print(f"총 {len(students)}명 작성 예정. API 호출이 발생합니다.")
        answer = input("계속하시겠습니까? [y/N]: ").strip().lower()
        if answer not in ("y", "yes"):
            print("취소됨")
            return

    result = run_batch(students, sections=sections, continue_on_error=True)
    _print_json(result)


def cmd_init(_: argparse.Namespace) -> None:
    ensure_data_dirs()
    print("data/saenggibu/ 폴더 구조를 준비했습니다.")
    print("다음 단계:")
    print("  1. python sgb.py samples import data/saenggibu/examples/")
    print("  2. python sgb.py analyze [--gemini]")
    print("  3. python sgb.py students import data/saenggibu/examples/students.example.tsv")
    print("  4. python sgb.py run --yes")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="대한민국 생기부 자동 작성 머신")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="데이터 폴더 초기화")
    p_init.set_defaults(func=cmd_init)

    p_samples = sub.add_parser("samples", help="과거 생기부 샘플 관리")
    samples_sub = p_samples.add_subparsers(dest="samples_cmd", required=True)

    p_si = samples_sub.add_parser("import", help="샘플 파일/폴더 가져오기")
    p_si.add_argument("path", help="JSON/TSV 파일 또는 폴더")
    p_si.set_defaults(func=cmd_samples_import)

    p_sl = samples_sub.add_parser("list", help="샘플 목록")
    p_sl.set_defaults(func=cmd_samples_list)

    p_analyze = sub.add_parser("analyze", help="샘플 패턴 분석 및 스타일 가이드 생성")
    p_analyze.add_argument("--gemini", action="store_true", help="Gemini로 스타일 가이드 정제")
    p_analyze.set_defaults(func=cmd_analyze)

    p_patterns = sub.add_parser("patterns", help="저장된 패턴/스타일 가이드 보기")
    p_patterns.set_defaults(func=cmd_patterns_show)

    p_students = sub.add_parser("students", help="학생 데이터 관리")
    students_sub = p_students.add_subparsers(dest="students_cmd", required=True)

    p_sti = students_sub.add_parser("import", help="학생 TSV/CSV 일괄 등록")
    p_sti.add_argument("file", help="학생 정보 표 파일")
    p_sti.set_defaults(func=cmd_students_import)

    p_sta = students_sub.add_parser("add", help="학생 1명 수동 등록")
    p_sta.add_argument("--name", required=True)
    p_sta.add_argument("--grade", type=int, required=True)
    p_sta.add_argument("--class-num", type=int, required=True)
    p_sta.add_argument("--number", type=int, required=True)
    p_sta.add_argument("--id", help="학생 ID (미지정 시 자동)")
    p_sta.add_argument("--gender", help="성별")
    p_sta.add_argument("--haengbal-notes", help="행발 작성용 메모")
    p_sta.add_argument("--keywords", nargs="*", help="행발 키워드")
    p_sta.add_argument("--subject", help="세특 과목명")
    p_sta.add_argument("--subject-notes", help="세특 활동 메모")
    p_sta.add_argument("--changche-jayul", help="창체 자율 메모")
    p_sta.add_argument("--changche-club", help="창체 동아리 메모")
    p_sta.add_argument("--changche-volunteer", help="창체 봉사 메모")
    p_sta.add_argument("--changche-career", help="창체 진로 메모")
    p_sta.set_defaults(func=cmd_students_add)

    p_stl = students_sub.add_parser("list", help="학생 목록")
    p_stl.add_argument("--status", help="pending|done|error 등 필터")
    p_stl.add_argument("--json", action="store_true", help="JSON 출력")
    p_stl.set_defaults(func=cmd_students_list)

    p_sts = students_sub.add_parser("show", help="학생 상세")
    p_sts.add_argument("id", help="학생 ID")
    p_sts.set_defaults(func=cmd_students_show)

    p_str = students_sub.add_parser("reset", help="작성 결과 초기화 (재작성)")
    p_str.add_argument("id", help="학생 ID")
    p_str.set_defaults(func=cmd_students_reset)

    p_run = sub.add_parser("run", help="생기부 자동 작성 실행")
    p_run.add_argument("--student", help="특정 학생 ID만 작성")
    p_run.add_argument("--status", help="일괄 작성 시 대상 상태 (기본: pending)")
    p_run.add_argument("--sections", help="행발,세특,창체 중 선택 (쉼표 구분)")
    p_run.add_argument("--limit", type=int, help="일괄 작성 인원 제한")
    p_run.add_argument("--yes", "-y", action="store_true", help="확인 없이 실행")
    p_run.set_defaults(func=cmd_run)

    return parser


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except KeyboardInterrupt:
        raise SystemExit("\n중단됨") from None
    except Exception as exc:
        raise SystemExit(f"오류: {exc}") from exc


if __name__ == "__main__":
    main()
