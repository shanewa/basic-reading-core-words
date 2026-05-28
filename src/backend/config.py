from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppConfig:
    repo_root: Path
    books_dir: Path
    db_path: Path
    host: str
    port: int
    debug: bool
    daily_target_default: int
    image_mode_enabled: bool
    image_provider: str


def load_config() -> AppConfig:
    repo_root = Path(__file__).resolve().parents[2]
    books_dir = repo_root / "books"
    db_default = repo_root / "src" / "data" / "study.db"

    return AppConfig(
        repo_root=repo_root,
        books_dir=books_dir,
        db_path=Path(os.getenv("STUDY_DB_PATH", str(db_default))),
        host=os.getenv("APP_HOST", "127.0.0.1"),
        port=int(os.getenv("APP_PORT", "5000")),
        debug=os.getenv("APP_DEBUG", "0") in {"1", "true", "True"},
        daily_target_default=int(os.getenv("DAILY_TARGET_DEFAULT", "20")),
        image_mode_enabled=os.getenv("IMAGE_MODE_ENABLED", "1") not in {"0", "false", "False"},
        image_provider=os.getenv("IMAGE_PROVIDER", "loremflickr"),
    )
