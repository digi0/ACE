"""Alembic environment.

Two decisions worth knowing about:

* The engine comes from backend.database, not from alembic.ini. That module
  already resolves Railway's DATABASE_URL and applies the postgres:// rewrite
  SQLAlchemy needs; a second copy of that logic in an ini file is how a
  migration ends up run against the wrong database.
* Models are imported for their side effect of populating Base.metadata, which
  is what `alembic revision --autogenerate` diffs against.
"""

from logging.config import fileConfig

from alembic import context

from backend.database import Base, engine
import backend.models  # noqa: F401 — registers every table on Base.metadata

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite cannot ALTER most things in place; batch mode rewrites the
            # table instead. Local dev runs on SQLite, prod on Postgres, and a
            # migration that only works on one of them is a migration that gets
            # discovered at deploy time.
            render_as_batch=connection.dialect.name == "sqlite",
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
