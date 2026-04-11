from datetime import datetime, timedelta
from typing import Optional
import bcrypt
from jose import JWTError, jwt
from app.config import settings


def _password_bytes_bcrypt(password: str) -> bytes:
    """Bcrypt accepts at most 72 bytes; truncate on UTF-8 boundaries."""
    if not isinstance(password, str):
        raise TypeError("password must be a string")
    raw = password.encode("utf-8")
    if len(raw) <= 72:
        return raw
    return raw[:72]


def hash_password(password: str) -> str:
    """Hash a plain text password (bcrypt, 72-byte limit)."""
    pw = _password_bytes_bcrypt(password)
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("ascii")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against a bcrypt hash string."""
    try:
        pw = _password_bytes_bcrypt(plain_password)
        h = hashed_password.encode("ascii")
    except (TypeError, UnicodeEncodeError, AttributeError):
        return False
    try:
        return bcrypt.checkpw(pw, h)
    except ValueError:
        return False


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({
        "exp":  expire,
        "iat":  datetime.utcnow(),
        "type": "access"
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None
