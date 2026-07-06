from __future__ import annotations

from src.saenggibu.inspector.rules import DEFAULT_BYTE_LIMITS, neis_byte_len


def test_neis_byte_len_korean() -> None:
    assert neis_byte_len("가") == 2
    assert neis_byte_len("abc") == 3


def test_setuk_hard_max_is_1500_bytes() -> None:
    assert DEFAULT_BYTE_LIMITS["세특"]["hard_max"] == 1500
