from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.api.v1 import analysis, auth, strategies
from app.dependencies import get_current_user, get_db
from app.domain import models
from app.domain.models import Plan, User
from app.infrastructure.database import SessionLocal, engine
from app.infrastructure.vector_store import rag_store
from app.repositories.user_repository import UserRepository
from app.services.analysis_service import ANALYSIS_MODES
from app.services.auth_service import hash_password, user_response


def _seed_test_accounts(db: Session) -> None:
    seeds = [
        ("free@test.com",    "123", Plan.free),
        ("pro@test.com",     "123", Plan.pro),
        ("premium@test.com", "123", Plan.premium),
    ]
    repo = UserRepository(db)
    for email, password, plan in seeds:
        if not repo.get_by_email(email):
            repo.create(email=email, hashed_password=hash_password(password), plan=plan)
            print(f"[SEED] Created {email} ({plan.value})")


@asynccontextmanager
async def lifespan(app: FastAPI):
    models.Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        _seed_test_accounts(db)
    finally:
        db.close()
    rag_store.load_knowledge()
    print(f"[RAG] База знаний загружена: {rag_store.collection.count()} чанков")
    yield


app = FastAPI(title="Stock Analysis RAG API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "ngrok-skip-browser-warning"],
)

app.include_router(auth.router,       prefix="/auth",       tags=["auth"])
app.include_router(analysis.router,   prefix="/analyze",    tags=["analysis"])
app.include_router(strategies.router, prefix="/strategies", tags=["strategies"])


@app.get("/user/profile", tags=["auth"])
async def get_profile(current_user: User = Depends(get_current_user)):
    return user_response(current_user)


@app.get("/modes", tags=["analysis"])
async def get_modes():
    return {k: v["description"] for k, v in ANALYSIS_MODES.items()}


@app.get("/health")
async def health():
    return {"status": "ok", "knowledge_chunks": rag_store.collection.count()}
