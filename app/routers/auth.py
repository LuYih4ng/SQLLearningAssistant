# 作用: 定义认证相关的API路由，包括注册、登录、获取用户信息和修改密码。

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from .. import crud, models, schemas, security
from ..database import get_db
from ..dependencies import get_current_user

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post("/register", response_model=schemas.User, status_code=status.HTTP_201_CREATED)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """用户注册接口"""
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该用户名已被注册",
        )
    return crud.create_user(db=db, user=user)


@router.post("/token", response_model=schemas.Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """用户登录获取Token接口。"""
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(
        data={"sub": user.username}
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me", response_model=schemas.User)
def read_users_me(current_user: models.User = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    return current_user


# --- 新增接口 ---
@router.post("/users/me/password")
def change_user_password(
        password_data: schemas.UserPasswordChange,
        current_user: models.User = Depends(get_current_user),
        db: Session = Depends(get_db)
):
    """
    登录用户修改自己的密码。
    """
    # 1. 验证旧密码是否正确
    if not security.verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")

    # 2. 更新密码
    crud.update_user_password(db, user=current_user, new_password=password_data.new_password)

    return {"message": "密码修改成功"}
