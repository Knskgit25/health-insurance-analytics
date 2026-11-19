"""
Configuration loader and path manager.
"""

from pathlib import Path
from typing import Any

import yaml

# Project root directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = ROOT_DIR / "config" / "config.yaml"


def load_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load and parse YAML configuration file."""
    path = Path(config_path) if config_path else CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_path(key: str, config: dict[str, Any] | None = None) -> Path:
    """Resolve a configured relative path to an absolute Path."""
    if config is None:
        config = load_config()
    rel_path = config.get("paths", {}).get(key)
    if not rel_path:
        raise KeyError(f"Path key '{key}' not found in configuration")
    return ROOT_DIR / rel_path
