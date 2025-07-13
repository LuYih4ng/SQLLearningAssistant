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
    # 关系更新: 指向新的Question模型
    authored_questions = relationship("Question", foreign_keys='Question.author_id', back_populates="author")
    approved_questions = relationship("Question", foreign_keys='Question.approver_id', back_populates="approver")
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


# 【核心重构】新增 Question 模型作为主题库
class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    question_text = Column(Text, nullable=False)
    correct_sql = Column(Text, nullable=False)

    # 每个题目自带的数据库环境 (建表+插入数据)
    setup_sql = Column(Text, nullable=False)

    topics = Column(String, nullable=False)  # 知识点, e.g., "GROUP BY,JOIN"
    status = Column(String, default='draft', index=True)  # 状态: 'draft', 'published'

    author_id = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    approver_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    published_at = Column(DateTime, nullable=True)

    author = relationship("User", foreign_keys=[author_id], back_populates="authored_questions")
    approver = relationship("User", foreign_keys=[approver_id], back_populates="approved_questions")


# 【模型简化】DailyQuestion 现在只引用 Question 表中的题目ID
class DailyQuestion(Base):
    __tablename__ = 'daily_questions'
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey('questions.id'), unique=True)  # 引用题库中的题目
    question_date = Column(Date, nullable=False, unique=True, default=datetime.date.today)

    # 建立与Question的关系，方便查询
    question = relationship("Question")
    submissions = relationship("DailySubmission", back_populates="daily_question_entry")


class DailySubmission(Base):
    __tablename__ = 'daily_submissions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    # 修改外键，指向daily_questions表
    daily_question_id = Column(Integer, ForeignKey('daily_questions.id'))
    submitted_sql = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=False)
    submitted_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    user = relationship("User", back_populates="daily_submissions")
    daily_question_entry = relationship("DailyQuestion", back_populates="submissions")

# 原有的 GeneratedQuestion 模型已被移除
