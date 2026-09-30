from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from aptum.core.config import get_settings
from aptum.db.base import Base

# Import every module's models so Base.metadata knows all tables.
from aptum.modules.companies import models as _companies  # noqa: F401
from aptum.modules.profile import models as _profile  # noqa: F401
from aptum.modules.skills import models as _skills  # noqa: F401
from aptum.modules.users import models as _users  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
database_url = get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata, compare_type=True
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
