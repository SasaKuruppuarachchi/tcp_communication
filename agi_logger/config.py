from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "cfg" / "configs.yaml"


class ConfigError(RuntimeError):
    pass


@dataclass
class ConfigPaths:
    config_path: Path
    base_dir: Path


def load_raw_config(config_path: Path | None = None) -> Dict[str, Any]:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if "agi_logger" not in data:
        raise ConfigError("Missing 'agi_logger' root key in configuration")
    return data


def save_raw_config(data: Dict[str, Any], config_path: Path | None = None) -> Path:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False)
    return path


def get_config_section(config: Dict[str, Any], *keys: str) -> Dict[str, Any]:
    node = config
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            raise ConfigError(f"Missing config section: {'/'.join(keys)}")
        node = node[key]
    if not isinstance(node, dict):
        raise ConfigError(f"Config section is not a dict: {'/'.join(keys)}")
    return node


def expand_path(value: str, base_dir: Path) -> str:
    expanded = Path(value).expanduser()
    if not expanded.is_absolute():
        expanded = (base_dir / expanded).resolve()
    return str(expanded)


def resolve_logger_paths(config: Dict[str, Any], config_path: Path) -> Dict[str, Any]:
    base_dir = config_path.parent
    logger_cfg = get_config_section(config, "agi_logger", "logger")
    resolved = dict(logger_cfg)

    if "bag_path" in resolved:
        resolved["bag_path"] = expand_path(str(resolved["bag_path"]), base_dir)
    if "qos_settings" in resolved:
        resolved["qos_settings"] = expand_path(str(resolved["qos_settings"]), base_dir)

    return resolved


def resolve_tcp_paths(config: Dict[str, Any], config_path: Path) -> Dict[str, Any]:
    base_dir = config_path.parent
    tcp_cfg = get_config_section(config, "agi_logger", "tcp_file_communication")
    resolved = dict(tcp_cfg)

    for side in ("server", "client"):
        if side in resolved and isinstance(resolved[side], dict):
            resolved_side = dict(resolved[side])
            if "file_path" in resolved_side:
                resolved_side["file_path"] = expand_path(str(resolved_side["file_path"]), base_dir)
            if "destination_path" in resolved_side:
                resolved_side["destination_path"] = expand_path(
                    str(resolved_side["destination_path"]), base_dir
                )
            resolved[side] = resolved_side
    return resolved


def get_config_paths(config_path: Path | None = None) -> ConfigPaths:
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    return ConfigPaths(config_path=path, base_dir=path.parent)


def update_nested_value(config: Dict[str, Any], dotted_key: str, value: Any) -> None:
    keys = dotted_key.split(".")
    if not keys:
        raise ConfigError("Empty key provided")
    node = config
    for key in keys[:-1]:
        if key not in node or not isinstance(node[key], dict):
            node[key] = {}
        node = node[key]
    node[keys[-1]] = value


def iter_nested_keys(config: Dict[str, Any], prefix: str = "") -> Iterable[Tuple[str, Any]]:
    for key, value in config.items():
        full_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            yield from iter_nested_keys(value, full_key)
        else:
            yield full_key, value
