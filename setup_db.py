#!/usr/bin/env python3
"""
Authentication Service - Database Setup Script

Creates the gdb_auth_db database and runs the schema.
Run this once before starting the service.

Usage:
    python setup_db.py

Author: GDB Architecture Team
"""

import asyncio
import asyncpg
import logging
from datetime import datetime
import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load .env file
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)





async def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    
    db_host = os.getenv("DATABASE_HOST", "localhost")
    db_port = int(os.getenv("DATABASE_PORT", 5432))
    db_user = os.getenv("DATABASE_USER", "postgres")
    db_password = os.getenv("DATABASE_PASSWORD", "")
    db_name = os.getenv("DATABASE_NAME", "gdb_auth_db")
    
    try:
        # First, connect to the postgres database to check/create target database
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database="postgres",
        )
        
        # Check if database exists
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_name
        )
        
        if not db_exists:
            logger.info(f"📦 Creating database: {db_name}")
            await conn.execute(f"CREATE DATABASE {db_name}")
            logger.info(f"✅ Database created: {db_name}")
        else:
            logger.info(f"✅ Database already exists: {db_name}")
        
        await conn.close()
        
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Failed to create database: {str(e)}")
        raise


async def create_tables():
    """Create all required tables in the database."""
    
    db_host = os.getenv("DATABASE_HOST", "localhost")
    db_port = int(os.getenv("DATABASE_PORT", 5432))
    db_user = os.getenv("DATABASE_USER", "postgres")
    db_password = os.getenv("DATABASE_PASSWORD", "")
    db_name = os.getenv("DATABASE_NAME", "gdb_auth_db")
    
    # First ensure database exists
    await create_database_if_not_exists()
    
    # Connect to database
    try:
        connection = await asyncpg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name,
        )
        logger.info(f"✅ Connected to database: {db_name}")
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Failed to connect to database: {str(e)}")
        raise
    
    try:
        # Read and execute schema
        schema_file = Path(__file__).parent / "app" / "database" / "auth_schema.sql"
        
        if not schema_file.exists():
            logger.error(f"Schema file not found: {schema_file}")
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
            
        logger.info(f"📋 Reading schema from {schema_file.name}...")
        with open(schema_file, "r") as f:
            schema_sql = f.read()

        logger.info("Executing schema...")
        await connection.execute(schema_sql)
        logger.info("✅ Schema executed successfully")
        
        logger.info("\n" + "="*60)
        logger.info("🎉 All tables created successfully!")
        logger.info("="*60)
        logger.info(f"Database: {db_name}")
        logger.info(f"Host: {db_host}:{db_port}")
        logger.info(f"User: {db_user}")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info("="*60)
        
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Error creating tables: {str(e)}")
        raise
    finally:
        await connection.close()
        logger.info("🔌 Database connection closed")


async def verify_tables():
    """Verify that all tables were created successfully."""
    
    db_host = os.getenv("DATABASE_HOST", "localhost")
    db_port = int(os.getenv("DATABASE_PORT", 5432))
    db_user = os.getenv("DATABASE_USER", "postgres")
    db_password = os.getenv("DATABASE_PASSWORD", "")
    db_name = os.getenv("DATABASE_NAME", "gdb_auth_db")
    
    connection = await asyncpg.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database=db_name,
    )
    
    try:
        # Get list of tables
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name
        """
        tables = await connection.fetch(query)
        
        if tables:
            logger.info("\n📊 Tables in database:")
            for table in tables:
                table_name = table['table_name']
                # Get row count
                count_query = f"SELECT COUNT(*) as cnt FROM {table_name}"
                count_result = await connection.fetchrow(count_query)
                row_count = count_result['cnt']
                logger.info(f"  ✓ {table_name}: {row_count} rows")
        else:
            logger.warning("No tables found in database")
            
        # Check views
        logger.info("\n📊 Views in database:")
        views_query = """
        SELECT viewname FROM pg_views 
        WHERE schemaname = 'public' 
        ORDER BY viewname
        """
        views = await connection.fetch(views_query)
        if views:
            for view in views:
                logger.info(f"  ✓ {view['viewname']}")
        
    finally:
        await connection.close()


async def main():
    """Main entry point."""
    try:
        db_host = os.getenv("DATABASE_HOST", "localhost")
        db_port = int(os.getenv("DATABASE_PORT", 5432))
        db_user = os.getenv("DATABASE_USER", "postgres")
        db_name = os.getenv("DATABASE_NAME", "gdb_auth_db")
        
        logger.info("🚀 Starting authentication database setup...")
        logger.info(f"Database configuration:")
        logger.info(f"  Host: {db_host}")
        logger.info(f"  Port: {db_port}")
        logger.info(f"  Database: {db_name}")
        logger.info(f"  User: {db_user}\n")
        
        # Create tables
        await create_tables()
        
        # Verify tables
        await verify_tables()
        
        logger.info("\n" + "="*60)
        logger.info("✅ DATABASE SETUP COMPLETE!")
        logger.info("="*60)
        logger.info("\nNext steps:")
        logger.info("  1. Verify .env configuration")
        logger.info("  2. Run: python -m uvicorn app.main:app --reload")
        logger.info("  3. Test: curl http://localhost:8004/health")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"\n❌ Setup failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
