"""
Database Connection Management

Handles connection pooling and initialization for gdb_auth_db.
Uses asyncpg for high-performance async PostgreSQL access.

Author: GDB Architecture Team
"""

import asyncpg
import logging
from typing import Optional
from app.config.settings import settings


logger = logging.getLogger(__name__)


class Database:
    """AsyncPG database connection pool manager."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self) -> None:
        """
        Initialize database connection pool.
        Also handles automatic schema creation and table initialization.
        
        Called during application startup.
        """
        # Connect pool directly to the shared production database
        # Note: On Render, we use a shared database with schemas per service.
        # We do NOT attempt to create a new database (requires superuser).
        try:
            self.pool = await asyncpg.create_pool(setup=set_schema_search_path, 
                host=settings.DATABASE_HOST,
                port=settings.DATABASE_PORT,
                database=settings.DATABASE_NAME,
                user=settings.DATABASE_USER,
                password=settings.DATABASE_PASSWORD,
                min_size=settings.MIN_DB_POOL_SIZE,
                max_size=settings.MAX_DB_POOL_SIZE,
            )
            logger.info(
                f"Connected to database: {settings.DATABASE_NAME} "
                f"at {settings.DATABASE_HOST}:{settings.DATABASE_PORT}"
            )
        except Exception as e:
            logger.error(f"Failed to connect to database pool: {str(e)}")
            raise

        # Check if core table 'auth_tokens' exists, run schema
        try:
            from pathlib import Path
            async with self.pool.acquire() as conn:
                # Ensure the auth_service schema exists first
                await conn.execute("CREATE SCHEMA IF NOT EXISTS auth_service")
                await conn.execute("SET search_path TO auth_service, public")
                
                auth_tokens_exists = await conn.fetchval(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'auth_service' AND table_name = 'auth_tokens')"
                )
                if not auth_tokens_exists:
                    logger.info("📋 Core table 'auth_tokens' does not exist. Running auth_schema.sql...")
                    schema_path = Path(__file__).parent / "auth_schema.sql"
                    if schema_path.exists():
                        with open(schema_path, "r", encoding="utf-8") as f:
                            schema_sql = f.read()
                        
                        # Execute schema statement by statement to handle partial states
                        for stmt in schema_sql.split(";"):
                            stmt_strip = stmt.strip()
                            if stmt_strip and not stmt_strip.startswith("--"):
                                try:
                                    await conn.execute(stmt_strip)
                                except Exception as stmt_err:
                                    err_msg = str(stmt_err).lower()
                                    if "already exists" in err_msg or "duplicate" in err_msg:
                                        logger.warning(f"⚠️ Skipping existing object: {stmt_err}")
                                    else:
                                        logger.error(f"Error executing statement: {stmt_err}")
                        logger.info("✅ Schema executed successfully")
                    else:
                        logger.error(f"❌ Schema file not found at {schema_path}")
                else:
                    logger.info("✅ auth_tokens table already exists, skipping schema execution")
        except Exception as e:
            logger.error(f"❌ Error during auth schema verification: {e}")
            raise
    
    async def disconnect(self) -> None:
        """
        Close database connection pool.
        
        Called during application shutdown.
        """
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def execute(
        self,
        query: str,
        *args,
        timeout: float = 10.0,
    ) -> None:
        """
        Execute a query that doesn't return rows (INSERT, UPDATE, DELETE, etc).
        
        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds
        
        Raises:
            Exception: If query fails
        """
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            await conn.execute(query, *args, timeout=timeout)
    
    async def fetch(
        self,
        query: str,
        *args,
        timeout: float = 10.0,
    ) -> list:
        """
        Fetch multiple rows from query result.
        
        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds
        
        Returns:
            List of asyncpg.Record objects
        """
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args, timeout=timeout)
    
    async def fetchrow(
        self,
        query: str,
        *args,
        timeout: float = 10.0,
    ) -> Optional[dict]:
        """
        Fetch single row from query result.
        
        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds
        
        Returns:
            Single row as dict-like object or None if no rows
        """
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(query, *args, timeout=timeout)
            return row
    
    async def fetchval(
        self,
        query: str,
        *args,
        timeout: float = 10.0,
    ) -> Optional[any]:
        """
        Fetch single value from query result.
        
        Args:
            query: SQL query
            *args: Query parameters
            timeout: Query timeout in seconds
        
        Returns:
            Single scalar value or None
        """
        if not self.pool:
            raise RuntimeError("Database not connected")
        
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args, timeout=timeout)


# Global database instance
db = Database()

# Schema configuration for multi-tenant database
SCHEMA_NAME = "auth_service"

# Update search_path for PostgreSQL
async def set_schema_search_path(connection):
    """Set the search path to use the correct schema."""
    await connection.execute(f"SET search_path TO auth_service, public")
