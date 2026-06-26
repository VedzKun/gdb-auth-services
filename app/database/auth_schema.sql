-- ================================================================
-- AUTH SERVICE DATABASE SCHEMA
-- Database: gdb_production_db (shared Render database)
-- Purpose: JWT token management and authentication audit logging
-- ================================================================

-- ================================================================
-- SCHEMA
-- ================================================================

-- Create the auth_service schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS auth_service;

-- Set search path for this script
SET search_path TO auth_service, public;

-- ================================================================
-- ENUMS
-- ================================================================

-- Use DO block to safely create enum type (IF NOT EXISTS not supported for types)
DO $$ BEGIN
    CREATE TYPE auth_action_enum AS ENUM (
        'LOGIN_SUCCESS',
        'LOGIN_FAILURE',
        'TOKEN_REVOKED'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;


-- ================================================================
-- AUTH TOKENS TABLE
-- Stores JWT token metadata for revocation and tracking
-- ================================================================
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

CREATE INDEX IF NOT EXISTS idx_auth_tokens_user_id ON auth_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_token_jti ON auth_tokens(token_jti);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_expires_at ON auth_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_auth_tokens_is_revoked ON auth_tokens(is_revoked);


-- ================================================================
-- AUTH AUDIT LOGS TABLE
-- Complete audit trail of all authentication attempts
-- ================================================================
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

CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_user_id ON auth_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_login_id ON auth_audit_logs(login_id);
CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_action ON auth_audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_auth_audit_logs_created_at ON auth_audit_logs(created_at);


-- ================================================================
-- VIEWS
-- ================================================================

-- Active Tokens View (not revoked and not expired)
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


-- Recent Logins View (last 30 days)
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


-- Failed Logins View (for security monitoring)
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


-- ================================================================
-- CLEANUP PROCEDURE
-- ================================================================

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


-- ================================================================
-- END OF AUTH SCHEMA
-- ================================================================
