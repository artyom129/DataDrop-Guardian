from __future__ import annotations
import os, re, tomllib
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class FieldRule:
    name: str
    type: str
    required: bool = False
    minimum: float | None = None

@dataclass(frozen=True)
class Pipeline:
    id: str
    name: str
    filename_pattern: str
    duplicate_key: tuple[str, ...]
    fields: tuple[FieldRule, ...]

@dataclass(frozen=True)
class Settings:
    base_dir: Path
    app_name: str
    database_path: Path
    scan_interval_seconds: float
    incoming_dir: Path
    processed_dir: Path
    quarantine_dir: Path
    pipelines: tuple[Pipeline, ...]

def _resolve(base: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else base / p

def load_settings(config_path: str | Path | None = None) -> Settings:
    path = Path(config_path or os.getenv("DATADROP_CONFIG", "config.toml")).resolve()
    with path.open("rb") as fh:
        data = tomllib.load(fh)
    base = path.parent
    app = data.get("app", {})
    monitor = data.get("monitor", {})
    pipelines = []
    for raw in data.get("pipelines", []):
        re.compile(raw["filename_pattern"])
        fields = tuple(FieldRule(
            name=f["name"],
            type=f.get("type", "text"),
            required=bool(f.get("required", False)),
            minimum=float(f["minimum"]) if "minimum" in f else None,
        ) for f in raw.get("fields", []))
        pipelines.append(Pipeline(
            id=raw["id"],
            name=raw["name"],
            filename_pattern=raw["filename_pattern"],
            duplicate_key=tuple(raw.get("duplicate_key", [])),
            fields=fields,
        ))
    settings = Settings(
        base_dir=base,
        app_name=app.get("name", "DataDrop Guardian"),
        database_path=_resolve(base, app.get("database_path", "data/datadrop.db")),
        scan_interval_seconds=max(float(monitor.get("scan_interval_seconds", 1)), .2),
        incoming_dir=_resolve(base, monitor.get("incoming_dir", "data/incoming")),
        processed_dir=_resolve(base, monitor.get("processed_dir", "data/processed")),
        quarantine_dir=_resolve(base, monitor.get("quarantine_dir", "data/quarantine")),
        pipelines=tuple(pipelines),
    )
    for folder in (settings.incoming_dir, settings.processed_dir, settings.quarantine_dir):
        folder.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
