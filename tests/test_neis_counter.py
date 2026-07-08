from __future__ import annotations

from src.saenggibu.neis_counter import neis_counter_byte_len, neis_counter_char_len_without_spaces


def test_neis_counter_byte_len_korean() -> None:
    assert neis_counter_byte_len("가") == 3
    assert neis_counter_byte_len("가" * 500) == 1500
    assert neis_counter_byte_len("가" * 545) == 1635
    assert neis_counter_byte_len("가" * 300) == 900


def test_neis_counter_byte_len_ascii_and_newline() -> None:
    assert neis_counter_byte_len("abc") == 3
    assert neis_counter_byte_len("hello world") == 11
    assert neis_counter_byte_len("a\n") == 1
    assert neis_counter_byte_len("a\nb") == 4


def test_neis_counter_char_len_without_spaces() -> None:
    assert neis_counter_char_len_without_spaces("가 나") == 2
    assert neis_counter_char_len_without_spaces("a\nb") == 2
