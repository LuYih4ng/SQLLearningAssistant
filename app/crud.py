# 作用: 封装数据库的CRUD(创建、读取、更新、删除)操作。

from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from typing import List, Optional, Dict
from collections import Counter
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


def update_user_password(db: Session, user: models.User, new_password: str):
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


# --- Question CRUD ---
def create_question_draft(db: Session, question_data: schemas.LLMGeneratedQuestionData, topics: str,
                          author_id: int) -> models.Question:
    temp_title = f"草稿-{topics}-{datetime.datetime.now().strftime('%H%M%S')}"
    db_question = models.Question(
        title=temp_title,
        question_text=question_data.question,
        correct_sql=question_data.correct_sql,
        setup_sql=question_data.setup_sql,
        topics=topics,
        status='draft',
        author_id=author_id
    )
    db.add(db_question)
    db.commit()
    db.refresh(db_question)
    return db_question


def get_draft_questions(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Question).filter(models.Question.status == 'draft').offset(skip).limit(limit).all()


def get_question_by_id(db: Session, question_id: int) -> Optional[models.Question]:
    return db.query(models.Question).filter(models.Question.id == question_id).first()


def update_question(db: Session, question_id: int, question_update: schemas.QuestionUpdate) -> Optional[
    models.Question]:
    db_question = get_question_by_id(db, question_id)
    if db_question:
        update_data = question_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_question, key, value)
        db.commit()
        db.refresh(db_question)
    return db_question


def publish_question(db: Session, question_id: int, approver_id: int) -> Optional[models.Question]:
    db_question = get_question_by_id(db, question_id)
    if db_question and db_question.status == 'draft':
        db_question.status = 'published'
        db_question.approver_id = approver_id
        db_question.published_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        db.refresh(db_question)
    return db_question


def get_random_published_question(db: Session, topics: List[str]):
    query = db.query(models.Question).filter(models.Question.status == 'published')
    if topics:
        topic_filters = [models.Question.topics.like(f"%{topic.strip()}%") for topic in topics]
        query = query.filter(or_(*topic_filters))
    return query.order_by(func.random()).first()


# --- DailyQuestion & Submission CRUD ---
def create_daily_question(db: Session, question_id: int):
    db_daily = models.DailyQuestion(
        question_id=question_id,
        question_date=datetime.date.today()
    )
    db.add(db_daily)
    db.commit()
    db.refresh(db_daily)
    return db_daily


def get_daily_question_by_date(db: Session, date: datetime.date):
    return db.query(models.DailyQuestion).filter(models.DailyQuestion.question_date == date).first()


def create_daily_submission(db: Session, user_id: int, daily_question_id: int, submitted_sql: str, is_correct: bool):
    db_submission = models.DailySubmission(
        user_id=user_id,
        daily_question_id=daily_question_id,
        submitted_sql=submitted_sql,
        is_correct=is_correct
    )
    db.add(db_submission)
    db.commit()
    db.refresh(db_submission)
    return db_submission


def check_if_daily_question_is_solved(db: Session, user_id: int, daily_question_id: int) -> bool:
    correct_submission = db.query(models.DailySubmission).filter(
        models.DailySubmission.user_id == user_id,
        models.DailySubmission.daily_question_id == daily_question_id,
        models.DailySubmission.is_correct == True
    ).first()
    return correct_submission is not None


# 【新增】检查用户今天是否已获得每日积分
def has_user_received_daily_points_today(db: Session, user_id: int) -> bool:
    """
    检查用户今天是否已经有过任何一次正确的每日一题提交。
    """
    today = datetime.date.today()
    start_of_day = datetime.datetime.combine(today, datetime.time.min)
    end_of_day = datetime.datetime.combine(today, datetime.time.max)

    correct_submission_today = db.query(models.DailySubmission).filter(
        models.DailySubmission.user_id == user_id,
        models.DailySubmission.is_correct == True,
        models.DailySubmission.submitted_at >= start_of_day,
        models.DailySubmission.submitted_at <= end_of_day
    ).first()

    return correct_submission_today is not None


# --- TestSubmission CRUD ---
def create_test_submission(db: Session, user_id: int, question_id: int, is_correct: bool):
    """创建一条能力测试的提交记录"""
    db_submission = models.TestSubmission(
        user_id=user_id,
        question_id=question_id,
        is_correct=is_correct
    )
    db.add(db_submission)
    db.commit()
    return db_submission


def get_user_weakest_topics(db: Session, user_id: int, time_delta_days: int = 30) -> List[str]:
    """
    根据用户在指定时间段内的错误记录，分析出最薄弱的知识点。
    """
    start_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=time_delta_days)

    wrong_submissions = db.query(models.TestSubmission).join(models.Question).filter(
        models.TestSubmission.user_id == user_id,
        models.TestSubmission.is_correct == False,
        models.TestSubmission.submitted_at >= start_date
    ).all()

    if not wrong_submissions:
        return []

    topic_errors = Counter()
    for sub in wrong_submissions:
        topics = [topic.strip() for topic in sub.question.topics.split(',')]
        topic_errors.update(topics)

    return [topic for topic, count in topic_errors.most_common(3)]
