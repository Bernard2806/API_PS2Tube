import secrets
import uuid

_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def new_id() -> str:
    return uuid.uuid4().hex


def new_code(length: int = 6) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
