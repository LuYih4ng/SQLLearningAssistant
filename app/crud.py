# 作用: 封装数据库的CRUD(创建、读取、更新、删除)操作。

from sqlalchemy.orm import Session
from . import models, schemas, security
import datetime

# --- User CRUD ---
def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = security.get_password_hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def add_points_to_user(db: Session, user_id: int, points_to_add: int):
    """为指定用户增加积分"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db_user.points += points_to_add
        db.commit()
        db.refresh(db_user)
    return db_user

def get_leaderboard(db: Session, limit: int = 10):
    """获取积分排行榜"""
    return db.query(models.User).order_by(models.User.points.desc()).limit(limit).all()

def get_all_users(db: Session):
    return db.query(models.User).all()

def update_user_permissions(db: Session, user_id: int, is_admin: bool):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db_user.is_admin = is_admin
        db.commit()
        db.refresh(db_user)
    return db_user

# 【重要修复】添加缺失的 update_user_password 函数
def update_user_password(db: Session, user: models.User, new_password: str):
    """更新用户的密码"""
    user.hashed_password = security.get_password_hash(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# --- ChatHistory CRUD ---
def create_chat_history(db: Session, history: schemas.ChatHistoryCreate, user_id: int):
    db_history = models.ChatHistory(**history.model_dump(), user_id=user_id)
    db.add(db_history)
    db.commit()
    db.refresh(db_history)
    return db_history


# --- GeneratedQuestion CRUD ---
def create_generated_question(
    db: Session,
    question_text: str,
    correct_sql: str,
    correct_result_hash: str,
    topics: str,
    user_id: int
) -> models.GeneratedQuestion:
    """将新生成的题目存入数据库"""
    db_question = models.GeneratedQuestion(
        question_text=question_text,
        correct_sql=correct_sql,
        correct_result_hash=correct_result_hash,
        topics=topics,
        user_id=user_id
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

def get_question_by_id(db: Session, question_id: int):
    """根据ID获取AI生成的题目信息"""
    return db.query(models.GeneratedQuestion).filter(models.GeneratedQuestion.id == question_id).first()

# --- DailyQuestion & Submission CRUD ---
def create_daily_question(db: Session, question: schemas.DailyQuestionCreate, author_id: int):
    """由管理员创建每日一题"""
    db_question = models.DailyQuestion(
        **question.model_dump(),
        author_id=author_id,
        question_date=datetime.date.today()
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question

def get_daily_question_by_date(db: Session, date: datetime.date):
    """根据日期获取每日一题"""
    return db.query(models.DailyQuestion).filter(models.DailyQuestion.question_date == date).first()

def get_daily_question_by_id(db: Session, question_id: int):
    return db.query(models.DailyQuestion).filter(models.DailyQuestion.id == question_id).first()

def create_daily_submission(db: Session, user_id: int, question_id: int, submitted_sql: str, is_correct: bool):
    """创建用户的每日一题提交记录"""
    db_submission = models.DailySubmission(
        user_id=user_id,
        question_id=question_id,
        submitted_sql=submitted_sql,
        is_correct=is_correct
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission

def check_if_daily_question_is_solved(db: Session, user_id: int, question_id: int) -> bool:
    """检查用户是否已经正确回答过某一天的每日一题"""
    correct_submission = db.query(models.DailySubmission).filter(
        models.DailySubmission.user_id == user_id,
        models.DailySubmission.question_id == question_id,
        models.DailySubmission.is_correct == True
    ).first()
    return correct_submission is not None
