from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE = "sgb_admin_session"
SESSION_MAX_AGE = 60 * 60 * 24  # 24h


def _serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("ADMIN_SESSION_SECRET", "").strip()
    if not secret:
        raise RuntimeError("ADMIN_SESSION_SECRET가 .env에 설정되지 않았습니다.")
    return URLSafeTimedSerializer(secret, salt="sgb-admin-session")


def get_admin_password() -> str:
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not password:
        raise RuntimeError("ADMIN_PASSWORD가 .env에 설정되지 않았습니다.")
    return password


def verify_password(password: str) -> bool:
    expected = get_admin_password()
    return secrets.compare_digest(password, expected)


def create_session_token() -> str:
    payload = {"sub": "admin", "iat": int(time.time()), "nonce": secrets.token_hex(8)}
    return _serializer().dumps(payload)


def verify_session_token(token: str) -> bool:
    if not token:
        return False
    try:
        data = _serializer().loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired):
        return False
    return isinstance(data, dict) and data.get("sub") == "admin"


@dataclass
class AdminSession:
    token: str
