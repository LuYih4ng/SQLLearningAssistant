# 作用: 配置数据库连接。现在管理两个数据库。

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- 应用主数据库 ---
# 用于存储用户、聊天记录等应用自身数据
# APP_DB_URL = "sqlite:///" + os.path.join(os.path.dirname(__file__), "sql_assistant.db") # 原始 SQLite URL

# PostgreSQL 连接字符串示例：
# "postgresql://user:password@host:port/database_name"
# 将 'user'、'password'、'host'、'port' 和 'database_name' 替换为您的 PostgreSQL 详细信息。
APP_DB_URL = "postgresql://postgres:123456@localhost:5432/sql_assistant_db" #

app_engine = create_engine(
    APP_DB_URL
)
AppSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)

Base = declarative_base() # ORM模型的基类保持不变


# --- 依赖注入 ---
def get_db():
    """获取应用主数据库的会话"""
    db = AppSessionLocal()
    try:
        yield db
    finally:
        db.close()

