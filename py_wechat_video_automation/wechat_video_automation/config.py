import os
from dataclasses import dataclass
from dotenv import load_dotenv


load_dotenv()


@dataclass
class AppConfig:
    google_api_key: str
    model_name: str
    output_dir: str
    state_db_path: str
    log_level: str


def get_config() -> AppConfig:
    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set. Put it in .env or environment.")

    model_name = os.getenv("MODEL_NAME", "gemini-1.5-pro").strip()
    output_dir = os.getenv("OUTPUT_DIR", os.path.join(os.getcwd(), "output")).strip()
    state_db_path = os.getenv("STATE_DB", os.path.join(os.getcwd(), "wechat_automation.db")).strip()
    log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper()

    os.makedirs(output_dir, exist_ok=True)

    return AppConfig(
        google_api_key=api_key,
        model_name=model_name,
        output_dir=output_dir,
        state_db_path=state_db_path,
        log_level=log_level,
    )