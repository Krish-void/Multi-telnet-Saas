import hashlib
import secrets
import os

SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret-key")
_sessions: dict[str, dict] = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain: str, hashed: str) -> bool:
    return hash_password(plain) == hashed


def create_token(user_data: dict) -> str:
    token = secrets.token_hex(32)
    _sessions[token] = user_data
    return token


def get_session(token: str) -> dict | None:
    return _sessions.get(token)


def revoke_token(token: str):
    _sessions.pop(token, None)
