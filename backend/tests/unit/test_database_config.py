import pytest
from app.config import Settings
from sqlalchemy import create_engine


@pytest.mark.parametrize(
    ("database_url", "expected"),
    [
        ("postgresql://user@db.example.test/postgres", "postgresql+psycopg"),
        ("postgres://user@db.example.test/postgres", "postgresql+psycopg"),
        ("postgresql+psycopg://user@db.example.test/postgres", "postgresql+psycopg"),
        ("sqlite:///./sql_app.db", "sqlite"),
    ],
)
def test_sqlalchemy_database_url_uses_psycopg_for_postgresql(database_url, expected):
    settings = Settings(_env_file=None, DATABASE_URL=database_url)

    assert settings.sqlalchemy_database_url.startswith(f"{expected}:")


def test_postgresql_url_loads_psycopg_without_connecting():
    settings = Settings(_env_file=None, DATABASE_URL="postgresql://localhost/postgres")

    engine = create_engine(settings.sqlalchemy_database_url)
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "psycopg"
    finally:
        engine.dispose()
