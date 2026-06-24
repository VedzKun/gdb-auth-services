#!/usr/bin/env python3
"""
Authentication Service - Database Reset Script

Drops and recreates the gdb_auth_db database completely.
⚠️ WARNING: This will delete ALL data in auth_tokens and auth_audit_logs tables!

Use only for:
  - Development/testing
  - Cleaning up test data
  - Starting fresh after corruption

DO NOT use in production!

Usage:
    python reset_db.py

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


# SQL Schema for Auth Service
CREATE_AUTH_TOKENS_TABLE = """
CREATE TABLE IF NOT EXISTS auth_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id BIGINT NOT NULL,
    login_id VARCHAR(255) NOT NULL,
    token_jti VARCHAR(255) NOT NULL UNIQUE,
    issued_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT valid_expiry CHECK (expires_at > issued_at)
);

-- Indexes for auth_tokens
CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_id ON auth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_token_jti ON auth_tokens(token_jti);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires_at ON auth_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_is_revoked ON auth_tokens(is_revoked);
"""

CREATE_AUTH_AUDIT_LOGS_TABLE = """
CREATE TYPE auth_action_enum AS ENUM ('LOGIN_SUCCESS', 'LOGIN_FAILURE', 'TOKEN_REVOKED');

CREATE TABLE IF NOT EXISTS auth_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    login_id VARCHAR(255) NOT NULL,
    user_id BIGINT,
    action auth_action_enum NOT NULL,
    reason VARCHAR(500),
    ip_address INET,
    user_agent VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for auth_audit_logs
CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_user_id ON auth_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_login_id ON auth_audit_logs(login_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_action ON auth_audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_created_at ON auth_audit_logs(created_at);
"""

CREATE_VIEWS = """
-- Active Tokens View
CREATE OR REPLACE VIEW active_auth_tokens AS
SELECT
    id,
    user_id,
    login_id,
    token_jti,
    issued_at,
    expires_at
FROM auth_tokens
WHERE is_revoked = FALSE
    AND expires_at > CURRENT_TIMESTAMP;

-- Recent Logins View
CREATE OR REPLACE VIEW recent_auth_logins AS
SELECT
    id,
    login_id,
    user_id,
    action,
    reason,
    ip_address,
    created_at
FROM auth_audit_logs
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '30 days'
ORDER BY created_at DESC;

-- Failed Logins View
CREATE OR REPLACE VIEW failed_auth_logins AS
SELECT
    id,
    login_id,
    user_id,
    reason,
    ip_address,
    created_at
FROM auth_audit_logs
WHERE action = 'LOGIN_FAILURE'
ORDER BY created_at DESC;
"""

CREATE_CLEANUP_FUNCTION = """
-- Function to revoke expired tokens
CREATE OR REPLACE FUNCTION cleanup_expired_tokens()
RETURNS TABLE(revoked_count INTEGER) AS $$
DECLARE
    revoked_count INTEGER;
BEGIN
    UPDATE auth_tokens
    SET is_revoked = TRUE
    WHERE expires_at <= CURRENT_TIMESTAMP
        AND is_revoked = FALSE;
    
    GET DIAGNOSTICS revoked_count = ROW_COUNT;
    RETURN QUERY SELECT revoked_count;
END;
$$ LANGUAGE plpgsql;
"""


def confirm_action():
    """Ask user to confirm destructive operation."""
    print("\n" + "!"*70)
    print("  ⚠️  WARNING: THIS WILL DELETE ALL DATA IN THE AUTHENTICATION DATABASE!")
    print("!"*70)
    print("\nThis action will:")
    print("  • Drop the entire gdb_auth_db database")
    print("  • Delete all auth_tokens")
    print("  • Delete all auth_audit_logs")
    print("  • Recreate empty schema")
    print("\n⚠️  THIS CANNOT BE UNDONE!")
    print("\nDo NOT use this in production!")
    
    response = input("\nType 'YES' to confirm: ").strip().upper()
    return response == "YES"


async def drop_database():
    """Drop the database if it exists."""
    
    db_host = os.getenv("DATABASE_HOST", "localhost")
    db_port = int(os.getenv("DATABASE_PORT", 5432))
    db_user = os.getenv("DATABASE_USER", "postgres")
    db_password = os.getenv("DATABASE_PASSWORD", "")
    db_name = os.getenv("DATABASE_NAME", "gdb_auth_db")
    
    try:
        # Connect to postgres database
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database="postgres",
        )
        
        # Terminate active connections
        logger.info("🔌 Terminating active connections...")
        terminate_sql = f"""
        SELECT pg_terminate_backend(pid) 
        FROM pg_stat_activity 
        WHERE datname = $1 AND pid <> pg_backend_pid()
        """
        await conn.execute(terminate_sql, db_name)
        
        # Check if database exists and drop it
        db_exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_name
        )
        
        if db_exists:
            logger.info(f"🗑️  Dropping database: {db_name}")
            await conn.execute(f"DROP DATABASE {db_name}")
            logger.info(f"✅ Database dropped: {db_name}")
        else:
            logger.info(f"ℹ️  Database does not exist: {db_name}")
        
        await conn.close()
        
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Failed to drop database: {str(e)}")
        raise


async def create_tables():
    """Create all required tables in the database."""
    
    db_host = os.getenv("DATABASE_HOST", "localhost")
    db_port = int(os.getenv("DATABASE_PORT", 5432))
    db_user = os.getenv("DATABASE_USER", "postgres")
    db_password = os.getenv("DATABASE_PASSWORD", "")
    db_name = os.getenv("DATABASE_NAME", "gdb_auth_db")
    
    try:
        # First, connect to postgres to create database
        conn = await asyncpg.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database="postgres",
        )
        
        logger.info(f"📦 Creating database: {db_name}")
        await conn.execute(f"CREATE DATABASE {db_name}")
        logger.info(f"✅ Database created: {db_name}")
        
        await conn.close()
        
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Failed to create database: {str(e)}")
        raise
    
    # Connect to new database
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
        # Create auth_tokens table
        logger.info("📋 Creating auth_tokens table...")
        await connection.execute(CREATE_AUTH_TOKENS_TABLE)
        logger.info("✅ auth_tokens table created successfully")
        
        # Create auth_audit_logs table
        logger.info("📋 Creating auth_audit_logs table...")
        await connection.execute(CREATE_AUTH_AUDIT_LOGS_TABLE)
        logger.info("✅ auth_audit_logs table created successfully")
        
        # Create views
        logger.info("📋 Creating views...")
        await connection.execute(CREATE_VIEWS)
        logger.info("✅ Views created successfully")
        
        # Create cleanup function
        logger.info("📋 Creating cleanup function...")
        await connection.execute(CREATE_CLEANUP_FUNCTION)
        logger.info("✅ Cleanup function created successfully")
        
        logger.info("\n" + "="*60)
        logger.info("🎉 All tables created successfully!")
        logger.info("="*60)
        
    except asyncpg.PostgresError as e:
        logger.error(f"❌ Error creating tables: {str(e)}")
        raise
    finally:
        await connection.close()
        logger.info("🔌 Database connection closed")


async def main():
    """Main entry point."""
    try:
        db_host = os.getenv("DATABASE_HOST", "localhost")
        db_port = int(os.getenv("DATABASE_PORT", 5432))
        db_user = os.getenv("DATABASE_USER", "postgres")
        db_name = os.getenv("DATABASE_NAME", "gdb_auth_db")
        
        logger.info("🚀 Starting database reset...")
        logger.info(f"Database configuration:")
        logger.info(f"  Host: {db_host}")
        logger.info(f"  Port: {db_port}")
        logger.info(f"  Database: {db_name}")
        logger.info(f"  User: {db_user}\n")
        
        # Confirm action
        if not confirm_action():
            logger.info("\n❌ Reset cancelled by user")
            sys.exit(0)
        
        # Drop database
        await drop_database()
        
        # Create fresh database and schema
        await create_tables()
        
        logger.info("\n" + "="*60)
        logger.info("✅ DATABASE RESET COMPLETE!")
        logger.info("="*60)
        logger.info("\nNext steps:")
        logger.info("  1. Run: python -m uvicorn app.main:app --reload")
        logger.info("  2. Test: curl http://localhost:8004/health")
        logger.info("="*60)
        
    except Exception as e:
        logger.error(f"\n❌ Reset failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
