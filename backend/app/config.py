from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    muse_api: str = ""
    muse_base: str = "https://api.meta.ai/v1"
    muse_model: str = "muse-spark-1.3"
    typesafe_api_key: str = ""
    typesafe_base: str = "https://api.typesafe.ai/v1"
    openrouter_key: str = ""  # Jev via OpenRouter when there is no TypeSafe key
    openrouter_decisions: str = "https://openrouter.ai/api/alpha/decisions"
    jev_openrouter_model: str = "typesafe/jev-1.14"
    hunch_url: str = "http://127.0.0.1:8765"
    case_matcher: str = "gemma"  # "jev": no local embedding model (small servers), see cases.JevCaseStore
    infominer_key: str = ""
    daily_budget_usd: float = 15.0
    max_chars: int = 4000
    verify_per_ip_hour: int = 10
    verify_timeout_s: float = 150.0  # whole agent run; Cloudflare and nginx allow longer
    screen_per_ip_hour: int = 600  # posts, not requests
    teacher_enabled: bool = False  # /teacher/v1/answer for the local hunch student; never on a public host
    data_dir: Path = ROOT / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
