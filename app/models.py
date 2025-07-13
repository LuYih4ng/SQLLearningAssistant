# 作用: 定义数据库表结构 (ORM模型)。

from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)
    points = Column(Integer, default=0)

    chat_histories = relationship("ChatHistory", back_populates="user")
    generated_questions = relationship("GeneratedQuestion", back_populates="user")
    # 新增: 用户与每日题目提交记录的关系
    daily_submissions = relationship("DailySubmission", back_populates="user")

class ChatHistory(Base):
    __tablename__ = 'chat_history'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    request_message = Column(Text, nullable=False)
    response_message = Column(Text, nullable=False)
    llm_provider = Column(String, nullable=False)
    timestamp = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = relationship("User", back_populates="chat_histories")

class GeneratedQuestion(Base):
    __tablename__ = 'generated_questions'
    id = Column(Integer, primary_key=True, index=True)
    question_text = Column(Text, nullable=False)
    correct_sql = Column(Text, nullable=False)
    correct_result_hash = Column(String, nullable=False)
    topics = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    user_id = Column(Integer, ForeignKey('users.id'))

    user = relationship("User", back_populates="generated_questions")

# --- 新增模型 ---

class DailyQuestion(Base):
    __tablename__ = 'daily_questions'
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    question_text = Column(Text, nullable=False)
    correct_sql = Column(Text, nullable=False)
    # 每日一题的日期，确保每天只有一题
    question_date = Column(Date, nullable=False, unique=True, default=datetime.date.today)
    author_id = Column(Integer, ForeignKey('users.id')) # 记录出题的管理员

    submissions = relationship("DailySubmission", back_populates="question")

class DailySubmission(Base):
    __tablename__ = 'daily_submissions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    question_id = Column(Integer, ForeignKey('daily_questions.id'))
    submitted_sql = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    submitted_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = relationship("User", back_populates="daily_submissions")
    question = relationship("DailyQuestion", back_populates="submissions")
