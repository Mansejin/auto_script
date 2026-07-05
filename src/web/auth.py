from __future__ import annotations

import os
import secrets
import time
from dataclasses import dataclass

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SESSION_COOKIE = "sgb_admin_session"
SESSION_MAX_AGE = 60 * 60 * 24  # 24h


def session_cookie_secure() -> bool:
    raw = os.getenv("SGB_COOKIE_SECURE", "").strip().lower()
    if raw in ("1", "true", "yes"):
        return True
    if raw in ("0", "false", "no"):
        return False
    host = os.getenv("SGB_HOST", "127.0.0.1").strip()
    return host not in ("127.0.0.1", "localhost", "0.0.0.0")


def _serializer() -> URLSafeTimedSerializer:
    secret = os.getenv("ADMIN_SESSION_SECRET", "").strip()
    if not secret:
        raise RuntimeError("ADMIN_SESSION_SECRET가 .env에 설정되지 않았습니다.")
    return URLSafeTimedSerializer(secret, salt="sgb-admin-session")


def get_admin_password() -> str:
    password = os.getenv("ADMIN_PASSWORD", "").strip()
    if not password:
        raise RuntimeError(
            "ADMIN_PASSWORD가 .env에 설정되지 않았습니다. "
            "프로젝트 루트 .env 파일에 ADMIN_PASSWORD=비밀번호 를 추가하세요."
        )
    return password


def admin_auth_configured() -> bool:
    return bool(os.getenv("ADMIN_PASSWORD", "").strip() and os.getenv("ADMIN_SESSION_SECRET", "").strip())


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
    except (BadSignature, SignatureExpired, RuntimeError):
        return False
    return isinstance(data, dict) and data.get("sub") == "admin"


@dataclass
class AdminSession:
    token: str
