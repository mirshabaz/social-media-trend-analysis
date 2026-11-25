from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.schemas.dataset import (
    PasswordChangeRequest,
    UserLoginRequest,
    UserProfileUpdateRequest,
    UserRegisterRequest,
)
from app.services.activity_service import record_event
from app.services.auth_service import (
    create_access_token,
    get_current_user,
    get_optional_user,
    hash_password,
    serialize_user,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> dict:
    email = payload.email.strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="Please enter a valid email address.")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = User(
        email=email,
        full_name=payload.full_name.strip(),
        role=payload.role.strip() or "Social Media Analyst",
        organization=payload.organization.strip(),
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    record_event(
        db,
        action="user_registered",
        title="Workspace Account Created",
        message=f"Welcome {user.full_name}! Your SOCIALPULSE AI analyst account is active.",
        category="security",
        severity="success",
        target_type="user",
        target_name=user.email,
        user_id=user.id,
    )
    return {"status": "success", "token": token, "user": serialize_user(user)}


@router.post("/login")
async def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> dict:
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled.")

    token = create_access_token(user)
    record_event(
        db,
        action="user_login",
        title="Signed In",
        message=f"Signed in as {user.full_name} ({user.email}).",
        category="security",
        severity="info",
        target_type="user",
        target_name=user.email,
        user_id=user.id,
    )
    return {"status": "success", "token": token, "user": serialize_user(user)}


@router.post("/logout")
async def logout(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> dict:
    if current_user:
        record_event(
            db,
            action="user_logout",
            title="Signed Out",
            message=f"Session ended for {current_user.email}.",
            category="security",
            severity="info",
            target_type="user",
            target_name=current_user.email,
            user_id=current_user.id,
        )
    return {"status": "success", "message": "Signed out."}


@router.get("/me")
async def me(current_user: User = Depends(get_current_user)) -> dict:
    return {"status": "success", "user": serialize_user(current_user)}


@router.put("/profile")
async def update_profile(
    payload: UserProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    current_user.full_name = payload.full_name.strip()
    current_user.role = payload.role.strip() or current_user.role
    current_user.organization = payload.organization.strip()
    current_user.bio = payload.bio.strip()
    db.commit()
    db.refresh(current_user)

    record_event(
        db,
        action="profile_updated",
        title="Profile Updated",
        message=f"Updated workspace profile for {current_user.full_name}.",
        category="security",
        severity="success",
        target_type="user",
        target_name=current_user.email,
        user_id=current_user.id,
    )
    return {"status": "success", "user": serialize_user(current_user)}


@router.put("/password")
async def change_password(
    payload: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    current_user.password_hash = hash_password(payload.new_password)
    db.commit()

    record_event(
        db,
        action="password_changed",
        title="Password Changed",
        message="Account password updated securely.",
        category="security",
        severity="warning",
        target_type="user",
        target_name=current_user.email,
        user_id=current_user.id,
    )
    return {"status": "success", "message": "Password updated successfully."}

