from __future__ import annotations

import base64
import json
from collections.abc import Generator

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.infrastructure.database import SessionLocal

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    from app.repositories.user_repository import UserRepository
    from app.services.auth_service import decode_token

    try:
        payload = decode_token(token)
        user_id: str = payload.get("user_id")
    except JWTError:
        raise HTTPException(status_code=401, detail={"error": "invalidToken"})

    user = UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail={"error": "invalidToken"})
    return user


def decode_investlink_token(token: str) -> str:
    """Декодирует JWT от Investlink без верификации подписи.
    Возвращает user_id из payload (поле user_id или sub).
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("invalid jwt")
        padding = 4 - len(parts[1]) % 4
        payload_bytes = base64.b64decode(parts[1] + "=" * padding)
        payload = json.loads(payload_bytes)
        user_id = payload.get("user_id") or payload.get("sub")
        if not user_id:
            raise ValueError("no user_id in token")
        return str(user_id)
    except Exception:
        raise HTTPException(status_code=401, detail={"error": "unauthorized"})


def get_investlink_user_id(token: str = Depends(oauth2_scheme)) -> str:
    return decode_investlink_token(token)
