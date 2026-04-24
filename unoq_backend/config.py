from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CookBot"
    api_title: str = "CookBot API"
    mode: Literal["simulator", "hardware"] = Field(default="simulator", alias="COOKBOT_MODE")
    mega_transport: Literal["fake", "fake_tcp", "serial"] = Field(
        default="fake", alias="COOKBOT_MEGA_TRANSPORT"
    )
    camera: Literal["mock", "libcamera", "disabled"] = Field(default="mock", alias="COOKBOT_CAMERA")
    ai: Literal["mock", "openai_compatible", "disabled"] = Field(
        default="mock", alias="COOKBOT_AI"
    )
    bind: str = Field(default="127.0.0.1", alias="COOKBOT_BIND")
    port: int = Field(default=8000, alias="COOKBOT_PORT")
    fake_mega_host: str = Field(default="127.0.0.1", alias="COOKBOT_FAKE_MEGA_HOST")
    fake_mega_port: int = Field(default=8765, alias="COOKBOT_FAKE_MEGA_PORT")
    serial_port: str = Field(default="/dev/ttyACM0", alias="COOKBOT_SERIAL_PORT")
    serial_baud: int = Field(default=115200, alias="COOKBOT_SERIAL_BAUD")
    ai_base_url: str = Field(default="https://api.openai.com/v1", alias="COOKBOT_AI_BASE_URL")
    ai_api_key: str | None = Field(default=None, alias="COOKBOT_AI_API_KEY")
    ai_model: str = Field(default="gpt-4o-mini", alias="COOKBOT_AI_MODEL")
    log_path: Path = Field(default=Path("logs/cookbot.jsonl"), alias="COOKBOT_LOG_PATH")
    recipes_dir: Path = Field(default=Path("recipes"), alias="COOKBOT_RECIPES_DIR")
    config_dir: Path = Field(default=Path("config"), alias="COOKBOT_CONFIG_DIR")
    calibration_path: Path = Field(
        default=Path("config/calibration.json"), alias="COOKBOT_CALIBRATION_PATH"
    )
    workspace_path: Path = Field(
        default=Path("config/workspace.yaml"), alias="COOKBOT_WORKSPACE_PATH"
    )
    hardware_readiness_path: Path = Field(
        default=Path("config/hardware_readiness.yaml"), alias="COOKBOT_HARDWARE_READINESS_PATH"
    )

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", populate_by_name=True
    )


def get_settings() -> Settings:
    return Settings()
