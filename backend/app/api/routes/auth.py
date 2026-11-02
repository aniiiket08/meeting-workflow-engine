import logging
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db, require_roles
from app.config import settings
from app.core.security import create_access_token, verify_password
from app.db.models.user import User, UserRole
from app.db.schemas.token import Token, TokenUser
from app.db.schemas.user import LoginRequest, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger("meeting_organizer")


@router.post("/login", response_model=Token)
def login_for_access_token(
    login_data: LoginRequest,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate user with username (or email) and password.

    The ``username`` field accepts either a username (e.g. ``admin``) or an
    email address (e.g. ``admin@meetingorganizer.internal``). The lookup is
    case-sensitive on both fields.
    """
    request_started = perf_counter()
    identifier = login_data.username.strip()
    lookup_started = perf_counter()
    user = (
        db.query(User)
        .filter((User.username == identifier) | (User.email == identifier))
        .first()
    )
    lookup_ms = (perf_counter() - lookup_started) * 1000
    if not user:
        logger.info(
            "AUTH_TIMING user_lookup_ms=%.2f bcrypt_verify_ms=0 jwt_generation_ms=0 total_ms=%.2f",
            lookup_ms,
            (perf_counter() - request_started) * 1000,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    verification_started = perf_counter()
    password_valid = verify_password(login_data.password, user.hashed_password)
    verification_ms = (perf_counter() - verification_started) * 1000
    if not password_valid:
        logger.info(
            "AUTH_TIMING user_lookup_ms=%.2f bcrypt_verify_ms=%.2f jwt_generation_ms=0 total_ms=%.2f",
            lookup_ms,
            verification_ms,
            (perf_counter() - request_started) * 1000,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    token_started = perf_counter()
    access_token = create_access_token(subject=user.id)
    token_ms = (perf_counter() - token_started) * 1000
    logger.info(
        "AUTH_TIMING user_lookup_ms=%.2f bcrypt_verify_ms=%.2f jwt_generation_ms=%.2f total_ms=%.2f",
        lookup_ms,
        verification_ms,
        token_ms,
        (perf_counter() - request_started) * 1000,
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=TokenUser.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user)) -> User:
    """Return currently authenticated user profile."""
    return current_user


@router.get("/chairman-only")
def chairman_only_route(current_user: User = Depends(require_roles(UserRole.CHAIRMAN))) -> dict[str, str]:
    """Test endpoint accessible only to users with CHAIRMAN role."""
    return {"message": f"Welcome Chairman {current_user.name}"}


@router.get("/principal-only")
def principal_only_route(
    current_user: User = Depends(require_roles(UserRole.CHAIRMAN, UserRole.PRINCIPAL))
) -> dict[str, str]:
    """Test endpoint accessible to CHAIRMAN and PRINCIPAL roles."""
    return {"message": f"Welcome Principal {current_user.name}"}


class DevLoginRequest(BaseModel):
    username: str


@router.post("/dev/login", response_model=Token)
def dev_login(payload: DevLoginRequest, db: Session = Depends(get_db)) -> Token:
    """Development-only one-click login.

    Issues a JWT for the requested username without requiring a password. Only
    available when ``APP_ENV=development``; returns 404 in any other
    environment so this endpoint can never be exercised in the wild.
    """
    if settings.APP_ENV != "development":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not found",
        )

    user = (
        db.query(User)
        .filter(
            (User.username == payload.username)
            | (User.email == payload.username)
        )
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unknown username",
        )

    access_token = create_access_token(subject=user.id)
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=TokenUser.model_validate(user),
    )