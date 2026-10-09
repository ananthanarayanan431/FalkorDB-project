"""Alembic migrations build exactly the schema the ORM models describe."""
from pathlib import Path

from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[2]


def _config(tmp_path) -> Config:
    cfg = Config(str(ROOT / "alembic.ini"), attributes={"configure_logger": False})
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{tmp_path / 'migrations.db'}")
    return cfg


def test_upgrade_matches_models_and_downgrades(tmp_path):
    cfg = _config(tmp_path)
    command.upgrade(cfg, "head")
    command.check(cfg)  # raises if the models and the migrated schema differ
    command.downgrade(cfg, "base")
