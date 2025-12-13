"""Neo4j database connection management."""

import logging
from contextlib import contextmanager
from typing import Generator

from neo4j import GraphDatabase, Driver, Session

from src.config import settings

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Neo4j database connection wrapper."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        """Initialize Neo4j connection.

        Args:
            uri: Neo4j bolt URI. Defaults to settings.NEO4J_URI.
            user: Neo4j username. Defaults to settings.NEO4J_USER.
            password: Neo4j password. Defaults to settings.NEO4J_PASSWORD.
        """
        self._uri = uri or settings.NEO4J_URI
        self._user = user or settings.NEO4J_USER
        self._password = password or settings.NEO4J_PASSWORD
        self._driver: Driver | None = None

    def connect(self) -> "Neo4jConnection":
        """Establish connection to Neo4j."""
        if self._driver is None:
            logger.info(f"Connecting to Neo4j at {self._uri}")
            self._driver = GraphDatabase.driver(
                self._uri,
                auth=(self._user, self._password),
            )
        return self

    def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed")

    def verify(self) -> bool:
        """Verify the connection is working.

        Returns:
            True if connection is valid.

        Raises:
            Exception if connection fails.
        """
        if self._driver is None:
            self.connect()

        self._driver.verify_connectivity()
        logger.info("Neo4j connection verified")
        return True

    @contextmanager
    def session(self, **kwargs) -> Generator[Session, None, None]:
        """Get a Neo4j session as a context manager.

        Args:
            **kwargs: Additional arguments passed to driver.session()

        Yields:
            Neo4j Session object.
        """
        if self._driver is None:
            self.connect()

        session = self._driver.session(**kwargs)
        try:
            yield session
        finally:
            session.close()

    def __enter__(self) -> "Neo4jConnection":
        """Context manager entry."""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()


# Singleton connection instance
_connection: Neo4jConnection | None = None


def get_connection() -> Neo4jConnection:
    """Get or create the singleton Neo4j connection."""
    global _connection
    if _connection is None:
        _connection = Neo4jConnection()
    return _connection