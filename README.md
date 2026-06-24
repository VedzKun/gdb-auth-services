# Authentication Service - README

**Centralized JWT-based Authentication for GDB Microservices**

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Quick Start](#quick-start)
5. [API Endpoints](#api-endpoints)
6. [JWT Token Structure](#jwt-token-structure)
7. [Authentication Flow](#authentication-flow)
8. [Database Schema](#database-schema)
9. [Configuration](#configuration)
10. [Inter-Service Communication](#inter-service-communication)
11. [Security Considerations](#security-considerations)
12. [Troubleshooting](#troubleshooting)

---

## Overview

The **Authentication Service** is a centralized microservice that handles user login and JWT token generation for the GDB platform.

**Key Principles:**
- **Centralized Authentication**: Single source of truth for login
- **Decentralized Authorization**: Each service enforces its own rules
- **Stateless JWT**: No session state required
- **One-way Communication**: Auth Service → User Service only

**Technology Stack:**
- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL 12+ (gdb_auth_db)
- **Async**: asyncpg (no ORM)
- **Security**: bcrypt, PyJWT (HS256)
- **Server**: Uvicorn

---

## Architecture

### Service Integration Model

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT / API GATEWAY                      │
└────────┬────────────┬────────────┬───────────────────────────┘
         │            │            │
    ┌────▼────┐  ┌───▼────┐  ┌───▼─────┐
    │ Accounts │  │ Txns   │  │  Users  │
    │ Service  │  │Service │  │ Service │
    │(Port 8001)  │(8002)  │  │(8003)   │
    └────┬────┘  └───┬────┘  └───┬─────┘
         │            │            │
         │       ┌────▼────────────▼──────┐
         └──────►│  Auth Service          │
                 │  JWT Generation        │
                 │  (Port 8004)           │
                 └────┬──────────────────┘
                      │
                      ▼ (one-way only)
                 ┌──────────┐
                 │  Users   │
                 │  Service │
                 └──────────┘
```

### Layered Architecture

```
┌─────────────────────────────────────────────────────┐
│ API Layer (FastAPI Routes)                          │
│   - POST /api/v1/auth/login                         │
│   - GET /api/v1/auth/health                         │
└─────────────────────────────────────────────────────┘
                    ▲
                    │
┌─────────────────────────────────────────────────────┐
│ Service Layer (Business Logic)                      │
│   - AuthService.login()                             │
│   - AuthService.verify_token()                      │
└─────────────────────────────────────────────────────┘
                    ▲
           ┌────────┴────────┐
           │                 │
┌──────────▼────┐  ┌────────▼──────┐
│ Repository    │  │ Client Layer   │
│ Layer         │  │ (HTTP)         │
│ - Tokens      │  │ - User Service │
│ - Audit Logs  │  │   Internal API │
└───────┬───────┘  └────────┬───────┘
        │                   │
        └─────────┬─────────┘
                  │
        ┌─────────▼──────────┐
        │ Security Layer     │
        │ - JWT Utilities    │
        │ - Password Verify  │
        └─────────┬──────────┘
                  │
        ┌─────────▼──────────┐
        │ Database Layer     │
        │ (asyncpg)          │
        │ gdb_auth_db        │
        └────────────────────┘
```

---

## Features

### 1. **User Authentication**
- Accept login_id and password
- Verify credentials against User Service
- Support for three user roles: ADMIN, TELLER, CUSTOMER

### 2. **JWT Token Generation**
- Algorithm: HS256 (HMAC SHA-256)
- Expiry: 15-30 minutes (configurable)
- Claims: sub (user_id), login_id, role, iat, exp, jti

### 3. **Token Management**
- Store token metadata in database
- Support token revocation
- Automatic cleanup of expired tokens

### 4. **Audit Logging**
- Log all login attempts (success and failure)
- Track IP address and user agent
- Record failure reasons

### 5. **Health & Readiness Checks**
- GET /health - Service status
- GET /ready - Database connectivity check

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 12+
- pip

### 2. Install Dependencies

```bash
cd auth_service
pip install -r requirements.txt
```

### 3. Setup Database

```bash
# Create database
createdb gdb_auth_db

# Run schema
psql gdb_auth_db < ../database_schemas/auth_schema.sql
```

### 4. Configure Environment

Edit `.env` file:

```env
DATABASE_HOST=localhost
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
USER_SERVICE_URL=http://localhost:8003
```

**⚠️ CRITICAL**: JWT_SECRET_KEY MUST be identical across all services (Auth, Accounts, Transactions, Users).

### 5. Run Service

```bash
# Development (with reload)
python -m uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload

# Production
python -m uvicorn app.main:app --host 0.0.0.0 --port 8004
```

### 6. Verify Setup

```bash
# Health check
curl http://localhost:8004/health

# Readiness check
curl http://localhost:8004/ready
```

---

## API Endpoints

### POST /api/v1/auth/login

**Authenticate user and receive JWT token**

**Request:**
```json
{
  "login_id": "john_doe",
  "password": "password123"
}
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 1800,
  "user_id": "12345678-1234-1234-1234-123456789012",
  "login_id": "john_doe",
  "role": "CUSTOMER"
}
```

**Error Responses:**

- **401 (Invalid Credentials)**
```json
{
  "error": "invalid_credentials",
  "message": "Invalid login credentials"
}
```

- **401 (User Inactive)**
```json
{
  "error": "user_inactive",
  "message": "User account is inactive"
}
```

- **404 (User Not Found)**
```json
{
  "error": "user_not_found",
  "message": "User not found"
}
```

- **503 (Service Unavailable)**
```json
{
  "error": "service_unavailable",
  "message": "User service is unavailable"
}
```

**Usage in Other Services:**

Once you receive the token, use it in subsequent requests to other services:

```bash
curl -H "Authorization: Bearer <access_token>" \
     http://localhost:8001/api/v1/accounts/balance
```

---

### GET /api/v1/auth/health

**Health check endpoint**

**Response (200):**
```json
{
  "status": "ok",
  "service": "auth-service"
}
```

---

### GET /ready

**Readiness check (database connectivity)**

**Response (200):**
```json
{
  "status": "ready",
  "database": "connected"
}
```

**Response (503):**
```json
{
  "status": "not_ready",
  "database": "disconnected",
  "error": "Connection refused"
}
```

---

## JWT Token Structure

### Header
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

### Payload
```json
{
  "sub": "12345678-1234-1234-1234-123456789012",
  "login_id": "john_doe",
  "role": "CUSTOMER",
  "iat": 1703433600,
  "exp": 1703435400,
  "jti": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Claims:**
- `sub`: User ID (UUID)
- `login_id`: User login identifier
- `role`: User role (ADMIN, TELLER, CUSTOMER)
- `iat`: Issued at timestamp
- `exp`: Expiry timestamp
- `jti`: JWT ID (unique token identifier for revocation)

---

## Authentication Flow

```
1. Client → Auth Service
   POST /api/v1/auth/login
   {login_id, password}
        │
        ▼
2. Auth Service → User Service
   GET /api/v1/internal/users/by-login/{login_id}
        │
        ├─ No: USER_NOT_FOUND (404)
        │       Audit: LOGIN_FAILURE (User not found)
        │       Response: 404
        │
        └─ Yes:
           ▼
3. Auth Service checks is_active
   ├─ No: USER_INACTIVE (403)
   │       Audit: LOGIN_FAILURE (User inactive)
   │       Response: 401
   │
   └─ Yes:
      ▼
4. Auth Service verifies password (bcrypt)
   ├─ No: INVALID_CREDENTIALS (401)
   │       Audit: LOGIN_FAILURE (Invalid password)
   │       Response: 401
   │
   └─ Yes:
      ▼
5. Auth Service generates JWT token
   - Claims: sub, login_id, role, iat, exp, jti
   - Sign with HS256
        │
        ▼
6. Auth Service stores token metadata
   Table: auth_tokens
   - token_jti, user_id, login_id, expires_at
        │
        ▼
7. Auth Service logs success
   Table: auth_audit_logs
   - action: LOGIN_SUCCESS, ip_address, user_agent
        │
        ▼
8. Response: 200 + {access_token, expires_in, user_id, role}
```

---

## Database Schema

### Tables

#### auth_tokens
Stores JWT token metadata for revocation and tracking.

```sql
CREATE TABLE auth_tokens (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    login_id VARCHAR(255) NOT NULL,
    token_jti VARCHAR(255) NOT NULL UNIQUE,
    issued_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- user_id (find all tokens for user)
- token_jti (check revocation status)
- expires_at (cleanup expired tokens)
- is_revoked (quick revocation check)

#### auth_audit_logs
Complete audit trail of all authentication attempts.

```sql
CREATE TABLE auth_audit_logs (
    id UUID PRIMARY KEY,
    login_id VARCHAR(255) NOT NULL,
    user_id UUID,
    action auth_action_enum NOT NULL,  -- LOGIN_SUCCESS, LOGIN_FAILURE, TOKEN_REVOKED
    reason VARCHAR(500),
    ip_address INET,
    user_agent VARCHAR(1000),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

**Indexes:**
- user_id (audit by user)
- login_id (audit by login_id)
- action (filter by action type)
- created_at (timeline queries)

### Views

- **active_auth_tokens**: Not revoked and not expired tokens
- **recent_auth_logins**: Logins from last 30 days
- **failed_auth_logins**: All failed login attempts

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | GDB-Authentication-Service | Service name |
| `DEBUG` | False | Debug mode (enable reload) |
| `ENVIRONMENT` | development | Environment (development/production) |
| `HOST` | 0.0.0.0 | Server host |
| `PORT` | 8004 | Server port |
| `DATABASE_HOST` | localhost | PostgreSQL host |
| `DATABASE_PORT` | 5432 | PostgreSQL port |
| `DATABASE_NAME` | gdb_auth_db | Database name |
| `DATABASE_USER` | postgres | DB user |
| `DATABASE_PASSWORD` | postgres | DB password |
| `MIN_DB_POOL_SIZE` | 5 | Min connections |
| `MAX_DB_POOL_SIZE` | 20 | Max connections |
| `JWT_SECRET_KEY` | (change me) | JWT signing secret (SHARED) |
| `JWT_ALGORITHM` | HS256 | JWT algorithm |
| `JWT_EXPIRY_MINUTES` | 30 | Token expiry in minutes |
| `USER_SERVICE_URL` | http://localhost:8003 | User Service URL |
| `USER_SERVICE_TIMEOUT` | 10 | User Service timeout |
| `LOG_LEVEL` | INFO | Log level |
| `CORS_ORIGINS` | localhost:* | CORS allowed origins |

---

## Inter-Service Communication

### Auth Service → User Service (One-way)

The Auth Service calls User Service internal APIs for credential verification:

#### Get User by Login ID
```
GET /api/v1/internal/users/by-login/{login_id}

Response (200):
{
  "user_id": "uuid",
  "login_id": "john_doe",
  "password": "bcrypt_hash",
  "role": "CUSTOMER",
  "is_active": true
}
```

#### Check User Active Status
```
GET /api/v1/internal/users/{user_id}/active

Response (200):
{
  "is_active": true
}
```

**⚠️ IMPORTANT**: 
- Auth Service DOES NOT modify User Service
- Auth Service DOES NOT receive calls from other services
- Other services verify tokens independently using JWT_SECRET_KEY
- NO refresh tokens (new login = new token)

---

## Security Considerations

### 1. JWT Secret Management
- **CRITICAL**: JWT_SECRET_KEY must be identical across all services
- Use strong random key (at least 32 characters)
- Rotate periodically (requires service restart)
- Never commit to version control

### 2. Password Handling
- Auth Service DOES NOT store passwords
- Auth Service DOES NOT hash passwords
- Auth Service verifies against bcrypt hash from User Service
- Bcrypt salt is User Service's responsibility

### 3. Token Security
- No token refresh endpoint (prevent token lifetime extension)
- Tokens are short-lived (15-30 minutes)
- Revocation is optional (tokens expire automatically)
- Token JTI prevents duplicate tokens

### 4. Database Security
- Use strong PostgreSQL passwords
- Enable SSL/TLS in production
- Restrict network access to auth_service database
- Regular backups of auth_tokens and audit logs

### 5. HTTP Communication
- Use HTTPS in production (not HTTP)
- Enable CORS properly (only allowed origins)
- Validate all inputs (Pydantic validation)
- Rate limiting recommended (future feature)

### 6. Audit Logging
- All login attempts are logged
- Failed attempts include reason
- IP addresses and user agents tracked
- Helps identify suspicious patterns

---

## Troubleshooting

### Issue: Cannot connect to database

**Error:**
```
Failed to connect to database: connection refused
```

**Solution:**
1. Check PostgreSQL is running: `psql -l`
2. Verify DATABASE_HOST, DATABASE_PORT in .env
3. Verify DATABASE_USER, DATABASE_PASSWORD
4. Check if gdb_auth_db exists: `psql -l | grep gdb_auth`
5. Run schema setup: `psql gdb_auth_db < database_schemas/auth_schema.sql`

### Issue: Cannot connect to User Service

**Error:**
```
User service unavailable: Connection refused
```

**Solution:**
1. Verify User Service is running on port 8003
2. Check USER_SERVICE_URL in .env
3. Verify network connectivity: `curl http://localhost:8003/health`
4. Check User Service logs for errors

### Issue: Login fails with "Invalid credentials"

**Possible Causes:**
1. User doesn't exist in User Service
2. User account is inactive
3. Password is incorrect
4. Bcrypt hash format is invalid

**Debug:**
```bash
# Check User Service has the user
curl http://localhost:8003/api/v1/internal/users/by-login/john_doe

# Check user is active
curl http://localhost:8003/api/v1/users/john_doe/active

# Check auth logs
psql gdb_auth_db -c "SELECT * FROM failed_auth_logins LIMIT 10;"
```

### Issue: Token verification fails in other services

**Error:**
```
Invalid token: Signature verification failed
```

**Causes:**
1. JWT_SECRET_KEY is different across services
2. Token is expired
3. Token is revoked
4. Token signature is malformed

**Solution:**
1. Verify JWT_SECRET_KEY is identical in all services
2. Check token expiry: `exp` claim > current timestamp
3. Check if token_jti is in revoked tokens
4. Verify token format (decode and inspect)

### Issue: High latency during login

**Possible Causes:**
1. User Service is slow (check its logs)
2. Database connection pool is exhausted
3. Network latency between services

**Solution:**
1. Monitor User Service: `curl http://localhost:8003/health`
2. Check connection pool: `MAX_DB_POOL_SIZE` in .env
3. Add database indexes if needed
4. Use connection pooling in User Service

---

## Development Notes

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_login.py

# With coverage
pytest --cov=app tests/
```

### Database Cleanup

```bash
# Revoke expired tokens
psql gdb_auth_db -c "SELECT cleanup_expired_tokens();"

# View audit logs
psql gdb_auth_db -c "SELECT * FROM recent_auth_logins LIMIT 20;"

# Check failed login attempts
psql gdb_auth_db -c "SELECT * FROM failed_auth_logins WHERE created_at > NOW() - INTERVAL '1 hour';"
```

### Logging

Set `LOG_LEVEL` in .env:
- `DEBUG`: Detailed information
- `INFO`: General information
- `WARNING`: Warning messages
- `ERROR`: Error messages only

---

## License

Part of GDB Microservices Platform. Internal use only.
