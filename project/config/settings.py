from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    admin_tg_id: int = Field(alias="ADMIN_TG_ID")

    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(alias="REDIS_URL")

    supergroup_id: int = Field(alias="SUPERGROUP_ID")

    company_name: str = Field(default="Apex Clean", alias="COMPANY_NAME")
    company_inn: str = Field(default="", alias="COMPANY_INN")
    company_phone: str = Field(default="", alias="COMPANY_PHONE")
    company_pay_url: str = Field(default="", alias="COMPANY_PAY_URL")

    storage_backend: str = Field(default="local", alias="STORAGE_BACKEND")
    local_storage_dir: str = Field(default="storage", alias="LOCAL_STORAGE_DIR")
