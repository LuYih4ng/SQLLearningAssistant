# 作用: 使用Pydantic加载和管理环境变量。

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # DeepSeek 配置
    DEEPSEEK_API_KEY: str = "default_key"
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1" # 新增

    # 通义千问 配置
    QWEN_API_KEY: str = "default_key"

    class Config:
        # 指定从哪个文件加载环境变量
        env_file = ".env"

# 创建一个全局配置实例，在其他地方可以直接导入使用
settings = Settings()
