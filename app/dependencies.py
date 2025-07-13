# 作用: 定义通用的依赖项，如获取当前用户、验证管理员权限等。

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from . import crud, models
from .database import get_db
from .security import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    """获取当前登录的用户模型"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = crud.get_user_by_username(db, username=username)

    if user is None:
        raise credentials_exception
    return user


# --- 新增依赖 ---
def get_current_admin_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    获取当前登录的用户，并验证其是否为管理员。
    如果不是管理员，则抛出403 Forbidden错误。
    """
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足，此操作需要管理员权限"
        )
    return current_user
