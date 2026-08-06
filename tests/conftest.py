from dataclasses import replace
from pathlib import Path
import pytest
from app.config import load_settings
from app.database import init_db

@pytest.fixture
def settings(tmp_path):
    base=load_settings(Path(__file__).resolve().parent.parent/"config.toml")
    s=replace(base,database_path=tmp_path/"test.db",incoming_dir=tmp_path/"incoming",
              processed_dir=tmp_path/"processed",quarantine_dir=tmp_path/"quarantine")
    for f in (s.incoming_dir,s.processed_dir,s.quarantine_dir): f.mkdir()
    init_db(s.database_path)
    return s
