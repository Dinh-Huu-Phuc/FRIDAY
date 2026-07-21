from __future__ import annotations

from sqlalchemy import inspect, text

from friday.src.db.database import get_engine
from friday.src.models.admin_account import AdminAccount


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _add_user_quota_columns() -> None:
    engine = get_engine()
    inspector = inspect(engine)

    with engine.begin() as connection:
        if not _has_column(inspector, "users", "free_question_limit_daily"):
            connection.execute(text("ALTER TABLE users ADD COLUMN free_question_limit_daily INTEGER NOT NULL DEFAULT 10"))
        if not _has_column(inspector, "users", "api_key_question_limit_daily"):
            connection.execute(text("ALTER TABLE users ADD COLUMN api_key_question_limit_daily INTEGER NOT NULL DEFAULT 10"))


def _create_admin_table() -> None:
    engine = get_engine()
    AdminAccount.__table__.create(bind=engine, checkfirst=True)


def run() -> None:
    _add_user_quota_columns()
    _create_admin_table()


if __name__ == "__main__":
    run()
