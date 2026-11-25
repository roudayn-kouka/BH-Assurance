"""Load pipeline configuration from mlops/configs/*.yaml."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml

CONFIG_DIR = Path(__file__).resolve().parents[1] / "configs"


def load_config(name: str, path: Optional[Path] = None) -> Dict[str, Any]:
    path = Path(path) if path else CONFIG_DIR / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}
