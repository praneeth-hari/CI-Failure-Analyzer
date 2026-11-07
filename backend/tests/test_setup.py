from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine


def test_settings_load_token():
    assert settings.github_token.startswith("github_pat_")


def test_database_connection():
    with engine.connect() as conn:
        assert conn.execute(text("select 1")).scalar() == 1
