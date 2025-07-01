from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # DeepSeek 配置
    DEEPSEEK_API_KEY: str = "default_key"
    DEEPSEEK_API_BASE: str = "https://api.deepseek.com/v1"

    # 通义千问 配置
    QWEN_API_KEY: str = "default_key"

    class Config:
        env_file = ".env"

settings = Settings()