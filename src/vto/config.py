from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_key: str = "changeme-generate-a-real-key"

    database_url: str = "postgresql://vto:vto@localhost:5432/vto"
    redis_url: str = "redis://localhost:6379/0"

    weights_dir: Path = Path("weights")
    datasets_dir: Path = Path("datasets")
    device: str = "cuda"
    dtype: str = "float16"

    results_dir: Path = Path("/tmp/vto-results")
    result_ttl_hours: int = 24

    rate_limit: str = "30/minute"

    sentry_dsn: str = ""


settings = Settings()
