# SQLLearningAssistant
一个基于 FastAPI 实现的简单的 SQL 学习助手
## 快速开始 (Getting Started)

请按照以下步骤在您的本地环境中设置并运行本项目

### 1. 安装 (Installation)


```
git clone https://github.com/LuYih4ng/SQLLearningAssistant.git
```
安装项目所需的依赖包
```
cd SQLLearningAssistant
pip install -r requirements.txt
```

### 2. 配置 (Configuration)
复制环境变量模板文件
```
cp .env.example .env
```
打开并编辑新建的 .env 文件，填入您自己的API-KEY

### 3. 运行 (Usage)
```
uvicorn app.main:app --reload
```
