import re

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.dependencies import get_current_user, get_db
from app.domain.models import User
from app.domain.schemas import UserCreate
from app.repositories.user_repository import UserRepository
from app.services import auth_service

router = APIRouter()

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: Session = Depends(get_db)):
    email = body.email.lower().strip()

    if not _EMAIL_RE.match(email):
        return JSONResponse(status_code=400, content={"error": "invalidEmail"})
    if len(body.password) < 3:
        return JSONResponse(status_code=400, content={"error": "weakPassword"})

    repo = UserRepository(db)
    if repo.get_by_email(email):
        return JSONResponse(status_code=400, content={"error": "emailTaken"})

    user = repo.create(email=email, hashed_password=auth_service.hash_password(body.password))
    token = auth_service.create_token(user)
    return JSONResponse(
        status_code=201,
        content={"token": token, "user": auth_service.user_response(user)},
    )


@router.post("/login")
async def login(body: UserCreate, db: Session = Depends(get_db)):
    email = body.email.lower().strip()
    user = UserRepository(db).get_by_email(email)

    if not user:
        return JSONResponse(status_code=400, content={"error": "accountNotFound"})
    if not auth_service.verify_password(body.password, user.password):
        return JSONResponse(status_code=400, content={"error": "wrongPassword"})

    token = auth_service.create_token(user)
    return {"token": token, "user": auth_service.user_response(user)}


@router.get("/refresh")
async def refresh(current_user: User = Depends(get_current_user)):
    return {"token": auth_service.create_token(current_user)}
