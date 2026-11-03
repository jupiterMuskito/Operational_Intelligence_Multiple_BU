from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(os.getenv("PORTAL_CONFIG_PATH", ROOT / "config" / "business_units.json"))
UPLOAD_DIR = Path(os.getenv("PORTAL_UPLOAD_DIR", ROOT / "data" / "uploads"))


class ConfigError(ValueError):
    pass


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ConfigError("Enter a valid business-unit name.")
    return slug


def load_business_units() -> dict[str, dict[str, Any]]:
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ConfigError(f"Could not load business-unit configuration: {exc}") from exc
    units = payload.get("business_units", payload)
    if not isinstance(units, dict) or not units:
        raise ConfigError("Configuration must contain at least one business unit.")
    for slug, config in units.items():
        validate_business_unit(slug, config)
    return units


def validate_business_unit(slug: str, config: dict[str, Any]) -> None:
    required = ("name", "hierarchy", "navigation", "kpis", "data")
    missing = [key for key in required if key not in config]
    if missing:
        raise ConfigError(f"{slug}: missing {', '.join(missing)}")
    if not isinstance(config.get("hierarchy"), list) or not config["hierarchy"]:
        raise ConfigError(f"{slug}: hierarchy must be a non-empty list")
    if not isinstance(config.get("kpis"), list):
        raise ConfigError(f"{slug}: kpis must be a list")


def save_business_units(units: dict[str, dict[str, Any]]) -> None:
    for slug, config in units.items():
        validate_business_unit(slug, config)
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(
        json.dumps({"schema_version": 1, "business_units": units}, indent=2),
        encoding="utf-8",
    )


def clone_business_unit(source_slug: str, name: str, units: dict[str, dict[str, Any]]) -> str:
    slug = slugify(name)
    if slug in units:
        raise ConfigError(f"A business unit named '{slug}' already exists.")
    if source_slug not in units:
        raise ConfigError("The template business unit does not exist.")
    config = deepcopy(units[source_slug])
    config["name"] = name.strip()
    config["short_name"] = name.strip()
    config["hierarchy"] = [name.strip(), "Configure division", "Configure unit"]
    config["data"] = {"process_file": "", "date_column": "date", "source_label": "No data uploaded", "is_demo": True}
    units[slug] = config
    save_business_units(units)
    return slug


def config_as_json(slug: str, config: dict[str, Any]) -> bytes:
    return json.dumps({"slug": slug, "config": config}, indent=2).encode("utf-8")


def import_business_unit(payload: bytes, units: dict[str, dict[str, Any]]) -> str:
    try:
        data = json.loads(payload.decode("utf-8"))
        slug = slugify(data["slug"])
        config = data["config"]
        validate_business_unit(slug, config)
    except Exception as exc:
        raise ConfigError(f"Invalid business-unit JSON: {exc}") from exc
    units[slug] = config
    save_business_units(units)
    return slug


def resolve_data_path(relative_path: str) -> Path | None:
    if not relative_path:
        return None
    candidate = (ROOT / relative_path).resolve()
    if ROOT.resolve() not in candidate.parents:
        raise ConfigError("Configured data path is outside the application directory.")
    return candidate


def load_process_data(config: dict[str, Any]) -> pd.DataFrame:
    path = resolve_data_path(str(config.get("data", {}).get("process_file", "")))
    if path is None or not path.exists():
        return pd.DataFrame()
    try:
        if path.suffix.lower() == ".csv":
            frame = pd.read_csv(path)
        else:
            frame = pd.read_excel(path, engine="openpyxl")
    except Exception as exc:
        raise ConfigError(f"Could not read operational data: {exc}") from exc
    frame.columns = [str(column).strip() for column in frame.columns]
    return frame.dropna(how="all").reset_index(drop=True)


def save_uploaded_data(slug: str, frame: pd.DataFrame, units: dict[str, dict[str, Any]]) -> Path:
    if slug not in units:
        raise ConfigError("Unknown business unit.")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    destination = (
        ROOT / "data" / "processed" / "analysis" / "butamer_kpi_dataset.csv"
        if slug == "refinery"
        else UPLOAD_DIR / f"{slug}_process.csv"
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(destination, index=False)
    relative = destination.relative_to(ROOT).as_posix()
    units[slug]["data"]["process_file"] = relative
    units[slug]["data"]["source_label"] = f"Admin upload: {len(frame):,} rows"
    units[slug]["data"]["is_demo"] = False
    save_business_units(units)
    return destination
