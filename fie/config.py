import yaml
from pathlib import Path
from typing import Dict, Any

_config_cache: Dict[str, Any] = {}


def load_config() -> Dict[str, Any]:
    """
    Load configuration from config.yaml.
    Cache the result to avoid repeated reads.
    """
    global _config_cache
    
    if _config_cache:
        return _config_cache
    
    config_path = Path(__file__).parent / "config.yaml"
    
    with open(config_path, "r") as f:
        _config_cache = yaml.safe_load(f)
    
    return _config_cache


def get(key: str, default=None) -> Any:
    """
    Get config value using dot notation.
    Example: get("storage.data_path") -> ~/.fie/transactions.json
    """
    config = load_config()
    keys = key.split(".")
    value = config
    
    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default
    
    # Expand home directory for paths
    if isinstance(value, str) and value.startswith("~"):
        value = str(Path(value).expanduser())
    
    return value if value is not None else default
