#!/usr/bin/env python3
"""디디딧 대본 시트 자동 수정 CLI."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.operations import (
    diff_rows,
    find_part,
    group_by_part,
    parse_table_text,
    read_script,
    replace_part,
    replace_range,
    script_to_dict,
    update_rows,
)
from src.sheets_client import authorize_google, exchange_oauth_code, get_oauth_authorization_url


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _print_json(data: object) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_read(args: argparse.Namespace) -> None:
    header_row, rows = read_script()
    if args.part:
        part = find_part(rows, args.part)
        if not part:
            raise SystemExit(f"파트를 찾을 수 없습니다: {args.part}")
        _print_json(part.to_dict())
        return
    if args.rows:
        _print_json([row.to_dict() for row in rows])
        return
    _print_json(script_to_dict(header_row, rows))


def cmd_list_parts(_: argparse.Namespace) -> None:
    _, rows = read_script()
    parts = group_by_part(rows)
    for part in parts:
        print(f"- {part.name}: {part.start_row}~{part.end_row}행 ({len(part.rows)}줄)")


def cmd_update(args: argparse.Namespace) -> None:
    payload = _load_json(Path(args.file))
    if not isinstance(payload, list):
        raise SystemExit("업데이트 JSON은 배열이어야 합니다. 예: [{\"row\": 5, \"대본\": \"...\"}]")
    changed = update_rows(payload)
    _print_json({"updated_rows": changed, "count": len(changed)})


def cmd_replace_part(args: argparse.Namespace) -> None:
    text = Path(args.file).read_text(encoding="utf-8")
    new_rows = parse_table_text(text)
    if not new_rows:
        raise SystemExit("교체할 행이 없습니다. TSV/CSV/마크다운 표 형식을 확인하세요.")
    result = replace_part(args.part, new_rows)
    _print_json({"part": args.part, **result})


def cmd_replace_range(args: argparse.Namespace) -> None:
    text = Path(args.file).read_text(encoding="utf-8")
    new_rows = parse_table_text(text)
    result = replace_range(args.start, args.end, new_rows)
    _print_json(result)


def cmd_diff(args: argparse.Namespace) -> None:
    _, current_rows = read_script()
    if args.part:
        part = find_part(current_rows, args.part)
        if not part:
            raise SystemExit(f"파트를 찾을 수 없습니다: {args.part}")
        current_rows = part.rows

    new_rows = parse_table_text(Path(args.file).read_text(encoding="utf-8"))
    changes = diff_rows(current_rows, new_rows)
    _print_json({"change_count": len(changes), "changes": changes})


def cmd_apply_diff(args: argparse.Namespace) -> None:
    """수정본 파일과 현재 시트를 비교해, 변경된 셀만 자동 반영."""
    _, current_rows = read_script()
    target_rows = current_rows
    start_row = None

    if args.part:
        part = find_part(current_rows, args.part)
        if not part:
            raise SystemExit(f"파트를 찾을 수 없습니다: {args.part}")
        target_rows = part.rows
        start_row = part.start_row

    new_rows = parse_table_text(Path(args.file).read_text(encoding="utf-8"))

    if len(new_rows) != len(target_rows):
        if start_row is None:
            raise SystemExit(
                "행 수가 달라 자동 반영할 수 없습니다. "
                "`replace-part` 또는 `replace-range`를 사용하세요."
            )
        end_row = target_rows[-1].sheet_row
        result = replace_range(start_row, end_row, new_rows)
        _print_json({"mode": "replace", **result})
        return

    updates: list[dict] = []
    for old, new in zip(target_rows, new_rows):
        item: dict = {"row": old.sheet_row}
        changed = False
        for col in ("대본", "장면", "사이즈", "자막", "코멘트"):
            old_val = getattr(old, col)
            new_val = getattr(new, col)
            if old_val != new_val:
                item[col] = new_val
                changed = True
        if changed:
            updates.append(item)

    if not updates:
        _print_json({"mode": "noop", "message": "변경 사항 없음"})
        return

    changed_rows = update_rows(updates)
    _print_json({"mode": "patch", "updated_rows": changed_rows, "count": len(changed_rows)})


def cmd_auth(_: argparse.Namespace) -> None:
    authorize_google(interactive=True)
    print("구글 로그인 완료. 이제 cli.py 명령을 사용할 수 있습니다.")


def cmd_auth_url(_: argparse.Namespace) -> None:
    print(get_oauth_authorization_url())
    print("\n위 URL을 브라우저(Chrome/Safari)에서 열고 로그인·동의까지 완료하세요.")
    print("완료 후 주소창 URL의 code= 뒤 값을 복사해 채팅에 붙여넣으세요.")
    print("또는: python cli.py auth-code <코드>")


def cmd_auth_code(args: argparse.Namespace) -> None:
    exchange_oauth_code(args.code)
    print("구글 로그인 완료. credentials/token.json 이 저장되었습니다.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="디디딧 구글 시트 대본 수정 도구")
    sub = parser.add_subparsers(dest="command", required=True)

    p_read = sub.add_parser("read", help="시트 내용 읽기 (JSON)")
    p_read.add_argument("--part", help="특정 파트만 읽기 (예: 실사용)")
    p_read.add_argument("--rows", action="store_true", help="파트 구분 없이 전체 행만")
    p_read.set_defaults(func=cmd_read)

    p_parts = sub.add_parser("list-parts", help="파트 목록과 행 범위")
    p_parts.set_defaults(func=cmd_list_parts)

    p_update = sub.add_parser("update", help="지정 행의 셀만 수정")
    p_update.add_argument("file", help="업데이트 JSON 파일 경로")
    p_update.set_defaults(func=cmd_update)

    p_rp = sub.add_parser("replace-part", help="파트 전체를 새 표로 교체")
    p_rp.add_argument("part", help="교체할 파트 이름 (부분 일치)")
    p_rp.add_argument("file", help="TSV/CSV/마크다운 표 파일")
    p_rp.set_defaults(func=cmd_replace_part)

    p_rr = sub.add_parser("replace-range", help="행 범위를 새 표로 교체")
    p_rr.add_argument("start", type=int, help="시작 행 번호")
    p_rr.add_argument("end", type=int, help="끝 행 번호")
    p_rr.add_argument("file", help="TSV/CSV/마크다운 표 파일")
    p_rr.set_defaults(func=cmd_replace_range)

    p_diff = sub.add_parser("diff", help="수정본과 현재 시트 비교")
    p_diff.add_argument("file", help="수정본 표 파일")
    p_diff.add_argument("--part", help="특정 파트만 비교")
    p_diff.set_defaults(func=cmd_diff)

    p_apply = sub.add_parser("apply", help="수정본을 시트에 자동 반영")
    p_apply.add_argument("file", help="수정본 표 파일")
    p_apply.add_argument("--part", help="특정 파트만 반영")
    p_apply.set_defaults(func=cmd_apply_diff)

    p_auth = sub.add_parser("auth", help="구글 계정 로그인 (로컬 브라우저, 최초 1회)")
    p_auth.set_defaults(func=cmd_auth)

    p_auth_url = sub.add_parser("auth-url", help="OAuth 로그인 URL 출력 (클라우드용)")
    p_auth_url.set_defaults(func=cmd_auth_url)

    p_auth_code = sub.add_parser("auth-code", help="OAuth 인증 코드로 토큰 저장")
    p_auth_code.add_argument("code", help="브라우저에 표시된 인증 코드")
    p_auth_code.set_defaults(func=cmd_auth_code)

    return parser


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except FileNotFoundError as exc:
        raise SystemExit(str(exc)) from exc
    except Exception as exc:
        raise SystemExit(f"오류: {exc}") from exc


if __name__ == "__main__":
    main()
