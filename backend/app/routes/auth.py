from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserSkillState
from app.bkt.manager import BKTManager
from app.repositories.skill_repository import SkillRepository
from app.schemas import UserCreate, UserLogin
from app.security import (
    hash_password,
    verify_password,
    create_access_token
)
from seed import seed_skills

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)


@router.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="E-mail já cadastrado"
        )

    seed_skills(db)
    new_user = User(
        name=user.name,
        email=user.email,
        phone=user.phone,
        password=hash_password(user.password),
    )

    try:
        db.add(new_user)
        db.flush()
        for skill in SkillRepository.get_all_skills(db):
            db.add(
                UserSkillState(
                    user_id=new_user.id,
                    skill_id=skill.id,
                    mastery_probability=BKTManager.get_initial_mastery(skill.code),
                )
            )
        db.commit()
        db.refresh(new_user)
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Usuário cadastrado com sucesso",
        "user_id": new_user.id
    }


@router.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()

    if not existing_user:
        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha inválidos"
        )

    if not verify_password(user.password, existing_user.password):
        raise HTTPException(
            status_code=401,
            detail="E-mail ou senha inválidos"
        )

    access_token = create_access_token(
        data={"sub": existing_user.id}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }