"""Database connection and session management."""

from pathlib import Path
from typing import Union

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine

from valerie.data.schema import Base


# Enable foreign keys for SQLite
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign key constraints for SQLite connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Database:
    """Database manager for SQLite."""

    def __init__(self, db_path: Union[str, Path] = "data/valerie.db"):
        """Initialize database connection.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            echo=False,
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        self._session: Session | None = None

    def create_tables(self) -> None:
        """Create all tables defined in the schema."""
        Base.metadata.create_all(bind=self.engine)

    def drop_tables(self) -> None:
        """Drop all tables from the database."""
        Base.metadata.drop_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get a new database session.

        Returns:
            A new SQLAlchemy Session instance.
        """
        return self.SessionLocal()

    def __enter__(self) -> Session:
        """Context manager entry - creates and returns a session."""
        self._session = self.get_session()
        return self._session

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - handles rollback on error and closes session."""
        if self._session is not None:
            if exc_type is not None:
                self._session.rollback()
            self._session.close()
            self._session = None


# Default database instance
_default_db: Database | None = None


def get_database(db_path: Union[str, Path] = "data/valerie.db") -> Database:
    """Get or create default database instance.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        The default Database instance.
    """
    global _default_db
    if _default_db is None:
        _default_db = Database(db_path)
    return _default_db


def init_database(db_path: Union[str, Path] = "data/valerie.db") -> Database:
    """Initialize database and create tables.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        The initialized Database instance with all tables created.
    """
    db = get_database(db_path)
    db.create_tables()
    return db
