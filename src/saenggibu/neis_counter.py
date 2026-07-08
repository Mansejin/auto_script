"""NEIS 글자수 계산 — https://github.com/hjh010501/neis-counter 와 동일 규칙.

영어·숫자·일반 특수문자·띄어쓰기 1byte, 엔터 2byte, 한글 3byte.
"""

from __future__ import annotations

import re

MATH_SYMBOLS_RE = re.compile(r"[\+\-\*\/=<>∞∑∏∫√∂∆πθΩαβγδεζηλμνξοπρστυφχψω·]")
OTHER_SYMBOLS_RE = re.compile(r"[‘’“”]")
GENERAL_SPECIAL_RE = re.compile(r"[\{\}\[\]\/?.,;:|\)*~`!^\-_+<>@\#$%&\\\=\(\'\"]")
HANGUL_RE = re.compile(r"[ㄱ-ㅎㅏ-ㅣ가-힣]")
ASCII_LETTER_RE = re.compile(r"[a-zA-Z]")
DIGIT_RE = re.compile(r"[0-9]")
WHITESPACE_RE = re.compile(r"\s")
NON_WHITESPACE_RE = re.compile(r"[^\s]")
NON_NEWLINE_RE = re.compile(r"[^\n]")
NEWLINE_TAB_SPACE_RE = re.compile(r"[\n\t\r\s]")
NEWLINE_CR_RE = re.compile(r"[\n\r]")


def _normalize_neis_content(content: str) -> str:
    if content == "\n" and content.startswith("\n"):
        content = content[1:]
    if content != "\n" and content.endswith("\n"):
        content = content[:-1]
    return content


def _strip_categories(text: str, *, keep: str) -> str:
    """Filter text down to characters belonging to `keep` category."""
    if keep == "english":
        s = HANGUL_RE.sub("", text)
        s = DIGIT_RE.sub("", s)
        s = MATH_SYMBOLS_RE.sub("", s)
        s = GENERAL_SPECIAL_RE.sub("", s)
        s = WHITESPACE_RE.sub("", s)
        return OTHER_SYMBOLS_RE.sub("", s)
    if keep == "korean":
        s = ASCII_LETTER_RE.sub("", text)
        s = DIGIT_RE.sub("", s)
        s = MATH_SYMBOLS_RE.sub("", s)
        s = GENERAL_SPECIAL_RE.sub("", s)
        s = WHITESPACE_RE.sub("", s)
        return OTHER_SYMBOLS_RE.sub("", s)
    if keep == "number":
        s = ASCII_LETTER_RE.sub("", text)
        s = HANGUL_RE.sub("", s)
        s = MATH_SYMBOLS_RE.sub("", s)
        s = GENERAL_SPECIAL_RE.sub("", s)
        s = WHITESPACE_RE.sub("", s)
        return OTHER_SYMBOLS_RE.sub("", s)
    if keep == "onebyte_special":
        s = ASCII_LETTER_RE.sub("", text)
        s = HANGUL_RE.sub("", s)
        s = DIGIT_RE.sub("", s)
        return NEWLINE_TAB_SPACE_RE.sub("", s)
    if keep == "threebyte_special":
        s = ASCII_LETTER_RE.sub("", text)
        s = HANGUL_RE.sub("", s)
        s = DIGIT_RE.sub("", s)
        s = MATH_SYMBOLS_RE.sub("", s)
        s = GENERAL_SPECIAL_RE.sub("", s)
        s = NEWLINE_TAB_SPACE_RE.sub("", s)
        return OTHER_SYMBOLS_RE.sub("", s)
    if keep == "space":
        s = ASCII_LETTER_RE.sub("", text)
        s = HANGUL_RE.sub("", s)
        s = DIGIT_RE.sub("", s)
        s = MATH_SYMBOLS_RE.sub("", s)
        s = GENERAL_SPECIAL_RE.sub("", s)
        s = OTHER_SYMBOLS_RE.sub("", s)
        s = NON_WHITESPACE_RE.sub("", s)
        return NEWLINE_CR_RE.sub("", s)
    if keep == "line":
        s = ASCII_LETTER_RE.sub("", text)
        s = HANGUL_RE.sub("", s)
        s = GENERAL_SPECIAL_RE.sub("", s)
        s = DIGIT_RE.sub("", s)
        s = MATH_SYMBOLS_RE.sub("", s)
        s = NON_NEWLINE_RE.sub("", s)
        return OTHER_SYMBOLS_RE.sub("", s)
    raise ValueError(f"unknown category: {keep}")


def neis_counter_byte_len(text: str) -> int:
    """Return NEIS 입력란 바이트 수 (neis-counter 규칙)."""
    content = _normalize_neis_content(text)
    english = _strip_categories(content, keep="english")
    korean = _strip_categories(content, keep="korean")
    number = _strip_categories(content, keep="number")
    onebyte_special = _strip_categories(content, keep="onebyte_special")
    threebyte_special = _strip_categories(content, keep="threebyte_special")
    space = _strip_categories(content, keep="space")
    line = _strip_categories(content, keep="line")
    return (
        len(english)
        + len(korean) * 3
        + len(number)
        + len(onebyte_special)
        + len(threebyte_special) * 3
        + len(space)
        + len(line) * 2
    )


def neis_counter_char_len_without_spaces(text: str) -> int:
    """neis-counter UI의 '공백 제외 N자'."""
    content = _normalize_neis_content(text)
    no_breaks = re.sub(r"(\r\n\t|\n|\r\t)", "", content)
    return len(no_breaks.replace(" ", ""))
