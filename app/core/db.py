import os
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://hub:hubpass@localhost:5432/balancehub",
)

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db() -> None:
    # Import models before metadata creation.
    from app.core import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _migrate_connector_state_columns()


def _migrate_connector_state_columns() -> None:
    # Runtime-safe schema upgrade for prototype environments without Alembic.
    wanted = {
        "axis_name": "ALTER TABLE connector_state ADD COLUMN axis_name VARCHAR(16) NOT NULL DEFAULT 'AXIS_5'",
        "connector_class": "ALTER TABLE connector_state ADD COLUMN connector_class VARCHAR(32) NOT NULL DEFAULT 'Core'",
        "economic_impact_weight": "ALTER TABLE connector_state ADD COLUMN economic_impact_weight DOUBLE PRECISION NOT NULL DEFAULT 1.0",
        "dependency_degree": "ALTER TABLE connector_state ADD COLUMN dependency_degree INTEGER NOT NULL DEFAULT 1",
        "node_degree": "ALTER TABLE connector_state ADD COLUMN node_degree INTEGER NOT NULL DEFAULT 1",
    }
    with engine.begin() as conn:
        columns = {c["name"] for c in inspect(conn).get_columns("connector_state")}
        for name, ddl in wanted.items():
            if name not in columns:
                conn.execute(text(ddl))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
