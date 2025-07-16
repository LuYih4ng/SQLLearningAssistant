# 作用: FastAPI应用的入口文件。

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import app_engine
# 【重要】确保导入了所有重构后的路由
from .routers import auth, chat, test, admin, daily

# 在应用启动时创建数据库表
# 提示：由于模型已重构，您需要删除旧的 .db 文件再重启，以生成新表结构
models.Base.metadata.create_all(bind=app_engine)

app = FastAPI(
    title="SQL学习助手",
    description="一个集成了大模型的智能SQL学习与测验平台",
    version="2.0.0", # 版本升级，代表重构完成
)

# --- CORS中间件 ---
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:5500",
    "null"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- 包含所有路由 ---
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(test.router)
app.include_router(admin.router)
app.include_router(daily.router)
@app.get("/", tags=["Root"])
def read_root():
    return {"message": "欢迎来到 SQL 学习助手 v2.0 API"}
