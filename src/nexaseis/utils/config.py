import json
import os
import sys
from pathlib import Path

_ENV_CONFIG = "NEXASEIS_CONFIG"
_source_config = Path(__file__).resolve().parents[2] / "config.json"
_installed_config = Path(sys.prefix) / "share" / "nexaseis" / "config.json"


def get_config_path() -> Path:
    if configured_path := os.environ.get(_ENV_CONFIG):
        path = Path(configured_path).expanduser()
        if not path.is_file():
            raise FileNotFoundError(
                f"{_ENV_CONFIG} points to a missing file: {path}"
            )
        return path

    for path in (_source_config, _installed_config):
        if path.is_file():
            return path

    raise FileNotFoundError(
        "NexaSeis configuration was not found. Set NEXASEIS_CONFIG to the "
        "path of a config.json file."
    )

def load_config() -> dict:
    with get_config_path().open(encoding="utf-8") as file:
        return json.load(file)

