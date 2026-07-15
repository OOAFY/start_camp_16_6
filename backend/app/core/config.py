from functools import lru_cache
from pathlib import Path
import os


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


@lru_cache(maxsize=1)
def load_settings() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[3]
    for candidate in (repo_root / ".env", repo_root / "backend" / ".env"):
        _load_env_file(candidate)

    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:5173")
    origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]

    return {
        "database_url": os.getenv("DATABASE_URL", "sqlite:///./localhub.db"),
        "cors_origins": origins,
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "openai_model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
    }
