# SQLLearningAssistant
一个基于 FastAPI 实现的简单的 SQL 学习助手
## 快速开始 (Getting Started)

请按照以下步骤在您的本地环境中设置并运行本项目

### 1. 安装 (Installation)


```bash
git clone https://github.com/LuYih4ng/SQLLearningAssistant.git
```
安装项目所需的依赖包
```bash
cd SQLLearningAssistant
pip install -r requirements.txt
```

### 2. 配置 (Configuration)
复制环境变量模板文件
```bash
cp .env.example .env
```
打开并编辑新建的 .env 文件，填入您自己的API-KEY

### 3. 运行 (Usage)
```bash
uvicorn app.main:app --reload
```

### 4. 打开网页 (Running the Frontend)
切换工作目录
```bash
cd frontend
start index.html
```

