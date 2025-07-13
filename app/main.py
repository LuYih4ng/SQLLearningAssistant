# 作用: FastAPI应用的入口文件。

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # 新增导入
from . import models
from .database import app_engine
from .routers import auth, chat, test, admin, daily

# 在应用启动时创建数据库表
models.Base.metadata.create_all(bind=app_engine)

app = FastAPI(
    title="SQL学习助手",
    description="一个集成了大模型的智能SQL学习与测验平台",
    version="1.0.0", # 版本升级
)

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 【重要更新】添加CORS中间件 ---
# 定义允许访问的源列表
# "null" 对应直接用浏览器打开的本地 file://... 文件
# "http://127.0.0.1:5500" 对应VS Code的Live Server插件默认地址
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
    allow_methods=["*"], # 允许所有HTTP方法
    allow_headers=["*"], # 允许所有请求头
)


# 包含路由
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(test.router)
app.include_router(admin.router)
app.include_router(daily.router)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "欢迎来到SQL学习助手 API"}
