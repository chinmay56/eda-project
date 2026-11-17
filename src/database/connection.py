"""
PostgreSQL Connection & Session Management module.
Provides connection pooling, context-managed transactions, and schema initialization.
"""

import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
import psycopg2
from psycopg2.extensions import connection as PgConnection
from psycopg2.pool import SimpleConnectionPool
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session

from src.config import db_settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Singleton database manager handling connection pooling,
    SQLAlchemy engine, and transaction contexts.
    """

    _instance: Optional["DatabaseManager"] = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._pool: Optional[SimpleConnectionPool] = None
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._init_pool()
        self._initialized = True

    def _init_pool(self) -> None:
        """Initialize PostgreSQL connection pool."""
        try:
            self._pool = SimpleConnectionPool(
                minconn=db_settings.pool_min,
                maxconn=db_settings.pool_max,
                host=db_settings.host,
                port=db_settings.port,
                dbname=db_settings.name,
                user=db_settings.user,
                password=db_settings.password,
                sslmode=db_settings.sslmode,
                connect_timeout=5,
            )
            # Also initialize SQLAlchemy engine for ORM / Pandas compatibility
            self._engine = create_engine(
                db_settings.connection_uri,
                pool_size=db_settings.pool_max,
                max_overflow=5,
                pool_timeout=10,
                pool_pre_ping=True,
            )
            self._session_factory = sessionmaker(bind=self._engine)
            logger.info("PostgreSQL connection pool and SQLAlchemy engine initialized successfully.")
        except Exception as exc:
            logger.error("Failed to initialize PostgreSQL pool: %s", exc)
            self._pool = None
            self._engine = None

    @property
    def is_available(self) -> bool:
        """Check if database connection pool is healthy."""
        if not self._pool:
            return False
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                    return cur.fetchone()[0] == 1
        except Exception:
            return False

    @contextmanager
    def get_connection(self) -> Generator[PgConnection, None, None]:
        """
        Yield a raw psycopg2 connection from the pool.
        Automatically checks out and returns connection to pool.
        """
        if not self._pool:
            raise ConnectionError(
                f"PostgreSQL connection pool not initialized. "
                f"Ensure PostgreSQL is running and DB '{db_settings.name}' exists."
            )
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    @contextmanager
    def transaction(self) -> Generator[PgConnection, None, None]:
        """
        Execute operations within an atomic transaction.
        Commits on success; rolls back on any exception.
        """
        with self.get_connection() as conn:
            try:
                yield conn
                conn.commit()
            except Exception as exc:
                conn.rollback()
                logger.error("Transaction rolled back due to error: %s", exc)
                raise

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Provide a transactional SQLAlchemy ORM session."""
        if not self._session_factory:
            raise ConnectionError("SQLAlchemy session factory is not available.")
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception as exc:
            session.rollback()
            logger.error("SQLAlchemy session rolled back: %s", exc)
            raise
        finally:
            session.close()

    @property
    def engine(self) -> Engine:
        if not self._engine:
            raise ConnectionError("SQLAlchemy engine is not initialized.")
        return self._engine

    def initialize_schema(self, schema_file: Optional[Path] = None) -> bool:
        """
        Execute DDL migration script to ensure all tables,
        constraints, and indexes exist.
        """
        if schema_file is None:
            schema_file = Path(__file__).resolve().parent / "schema.sql"

        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found at {schema_file}")

        sql = schema_file.read_text(encoding="utf-8")
        with self.transaction() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
        logger.info("Database schema initialized successfully from %s", schema_file)
        return True

    def close(self) -> None:
        """Close connection pool and engine cleanly."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
        if self._engine:
            self._engine.dispose()
            self._engine = None


db_manager = DatabaseManager()
