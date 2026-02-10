from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from platformdirs import user_config_dir


@dataclass
class AppConfig:
    include_tree: bool = True
    include_file_contents: bool = True
    max_file_bytes: int = 200_000
    use_default_ignores: bool = True
    respect_gitignore: bool = True

    filter_by_extension: bool = False
    selected_extensions: list[str] | None = None

    def __post_init__(self) -> None:
        if self.selected_extensions is None:
            self.selected_extensions = []


def config_path() -> Path:
    cfg_dir = Path(user_config_dir(appname="prompt-utils"))
    cfg_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir / "config.json"


def load_config() -> AppConfig:
    p = config_path()
    if not p.exists():
        return AppConfig()
    
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return AppConfig()
    
    cfg = AppConfig()
    for k, v in data.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)
    return cfg


def save_config(cfg: AppConfig) -> None:
    p = config_path()
    p.write_text(json.dumps(asdict(cfg), indent=4, sort_keys=True), encoding="utf-8")