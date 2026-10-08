from functools import lru_cache
from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix='', extra='ignore', hide_input_in_errors=True)
    app_environment: Literal['local', 'test'] = 'local'
    platform_mode: Literal['synthetic'] = 'synthetic'
    db_host: str = 'db'
    db_name: str = 'cw_ops'
    db_user: str = 'cw_ops'
    db_password: SecretStr = Field(min_length=24)
    session_minutes: int = Field(default=30, ge=1, le=120)


@lru_cache
def settings():
    return Settings()
