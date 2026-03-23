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
