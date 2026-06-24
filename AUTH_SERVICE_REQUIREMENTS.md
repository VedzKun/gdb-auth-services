# Authentication Service - Requirements Document

**Project**: Global Digital Bank (GDB) - Authentication Service  
**Version**: 1.0.0  
**Date**: February 10, 2026  
**Author**: GDB Architecture Team

---

## 1. Executive Summary

The Authentication Service is a centralized microservice within the Global Digital Bank ecosystem responsible for user authentication and JWT token generation. It serves as the single source of truth for login operations, issuing stateless JWT tokens that other services verify independently.

### Key Capabilities
- Centralized user authentication
- JWT token generation and management
- Credential verification via Users Service
- Token metadata storage and revocation
- Comprehensive audit logging
- Health and readiness checks

### Architecture Principle
- **Centralized Authentication**: Single service handles login
- **Decentralized Authorization**: Each service enforces its own rules
- **Stateless JWT**: No session state required
- **One-way Communication**: Auth Service → Users Service only

---

## 2. Business Requirements

### 2.1 Authentication

#### 2.1.1 User Login
**Purpose**: Authenticate users and issue JWT tokens

**Requirements**:
- Accept login_id and password
- Verify credentials against Users Service
- Support three user roles: CUSTOMER, TELLER, ADMIN
- Generate JWT token on successful authentication
- Return token with user details
- Log all authentication attempts

#### 2.1.2 Credential Verification Flow
1. Receive login_id and password from client
2. Call Users Service to verify credentials
3. Check user exists
4. Check user is active
5. Verify password using bcrypt
6. Generate JWT token if valid
7. Store token metadata in database
8. Log authentication result
9. Return token to client

### 2.2 Token Management

#### 2.2.1 JWT Token Generation
**Requirements**:
- Algorithm: HS256 (HMAC SHA-256)
- Token expiry: 15-30 minutes (configurable)
- Include claims: sub (user_id), login_id, role, iat, exp, jti
- Sign with shared secret key
- Generate unique token ID (jti) for revocation

#### 2.2.2 Token Metadata Storage
**Purpose**: Track issued tokens for revocation and audit

**Requirements**:
- Store token_jti, user_id, login_id
- Store issued_at and expires_at timestamps
- Support token revocation flag
- Automatic cleanup of expired tokens

#### 2.2.3 Token Verification
**Purpose**: Validate JWT tokens (optional endpoint)

**Requirements**:
- Verify token signature
- Check token expiration
- Check token revocation status
- Return token claims if valid

### 2.3 Audit Logging

**Requirements**:
- Log all login attempts (success and failure)
- Track IP address and user agent
- Record failure reasons
- Store audit data in database
- Support audit queries by user, action, date range
- Retention period: 90 days minimum

### 2.4 Security Requirements

#### 2.4.1 Password Handling
- Auth Service DOES NOT store passwords
- Auth Service DOES NOT hash passwords
- Auth Service verifies against bcrypt hash from Users Service
- Password never logged or returned in responses

#### 2.4.2 Token Security
- No token refresh endpoint (prevent lifetime extension)
- Tokens are short-lived (15-30 minutes)
- Revocation is optional (tokens expire automatically)
- Token JTI prevents duplicate tokens
- Shared secret must be identical across all services

---

## 3. Functional Requirements

### 3.1 Public API Endpoints

#### FR-1: User Login
**Endpoint**: `POST /api/v1/auth/login`

**Purpose**: Authenticate user and issue JWT token

**Input**:
```json
{
  "login_id": "string",
  "password": "string"
}
```

**Validations**:
- login_id and password are required
- Call Users Service to verify credentials
- Check user exists
- Check user is active
- Verify password

**Success Output (200 OK)**:
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

**Error Responses**:
- 401: Invalid credentials
- 401: User inactive
- 404: User not found
- 503: Users Service unavailable

#### FR-2: Verify Token (Optional)
**Endpoint**: `POST /api/v1/auth/verify`

**Purpose**: Validate JWT token

**Input**:
```json
{
  "token": "string"
}
```

**Output**:
```json
{
  "is_valid": boolean,
  "user_id": "string",
  "login_id": "string",
  "role": "string",
  "expires_at": "datetime"
}
```

#### FR-3: Health Check
**Endpoint**: `GET /api/v1/auth/health`

**Purpose**: Service health status

**Output**:
```json
{
  "status": "ok",
  "service": "auth-service"
}
```

#### FR-4: Readiness Check
**Endpoint**: `GET /ready`

**Purpose**: Database connectivity check

**Output**:
```json
{
  "status": "ready",
  "database": "connected"
}
```

### 3.2 Internal Operations

#### FR-5: Token Metadata Storage
**Purpose**: Store token information for tracking

**Requirements**:
- Store in auth_tokens table
- Include token_jti, user_id, login_id
- Include issued_at, expires_at
- Support revocation flag

#### FR-6: Audit Logging
**Purpose**: Log all authentication attempts

**Requirements**:
- Store in auth_audit_logs table
- Include login_id, user_id, action
- Include reason, ip_address, user_agent
- Support queries by user, action, date

---

## 4. Non-Functional Requirements

### 4.1 Performance Requirements

**NFR-1: Response Time**
- Login: < 1 second (95th percentile)
- Token verification: < 200ms (95th percentile)
- Health check: < 100ms (95th percentile)

**NFR-2: Throughput**
- Support 1000 concurrent login requests
- Handle 10,000 logins per minute

**NFR-3: Database Connection Pooling**
- Minimum pool size: 5 connections
- Maximum pool size: 20 connections
- Connection timeout: 30 seconds

### 4.2 Security Requirements

**NFR-4: JWT Secret Management**
- CRITICAL: JWT_SECRET_KEY must be identical across all services
- Use strong random key (at least 32 characters)
- Rotate periodically (requires service restart)
- Never commit to version control

**NFR-5: Token Security**
- Short-lived tokens (15-30 minutes)
- No refresh tokens
- Unique token ID (jti) for each token
- Signature verification required

**NFR-6: Communication Security**
- HTTPS only in production
- Secure communication with Users Service
- TLS 1.2+ for data in transit

**NFR-7: Audit Security**
- All login attempts logged
- Failed attempts include reason
- IP addresses tracked
- User agents tracked

### 4.3 Reliability Requirements

**NFR-8: Data Consistency**
- ACID transactions for token storage
- Atomic audit logging
- Rollback on any failure

**NFR-9: Error Handling**
- Structured error responses
- Comprehensive exception handling
- Detailed logging for debugging
- User-friendly error messages

**NFR-10: Availability**
- Target uptime: 99.9% (8.76 hours downtime/year)
- Graceful degradation on Users Service failure
- Health check endpoint for monitoring
- Readiness check for database connectivity

### 4.4 Scalability Requirements

**NFR-11: Horizontal Scaling**
- Stateless service design
- Support for multiple instances behind load balancer
- Database connection pooling per instance

**NFR-12: Database Scalability**
- Indexed columns for fast queries
- Optimized query patterns
- Automatic cleanup of expired tokens

### 4.5 Maintainability Requirements

**NFR-13: Code Quality**
- Type hints for all functions
- Comprehensive docstrings
- Follows PEP 8 style guide
- Test coverage > 80%

**NFR-14: Logging**
- Structured logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Request/response logging
- Sensitive data masking (passwords)

**NFR-15: Documentation**
- OpenAPI/Swagger documentation
- README with setup instructions
- Architecture diagrams
- Troubleshooting guide

### 4.6 Compatibility Requirements

**NFR-16: Technology Stack**
- Python 3.9+
- FastAPI 0.104.1+
- PostgreSQL 12.0+
- asyncpg for async database operations

**NFR-17: API Versioning**
- API prefix: /api/v1
- Backward compatibility within major version
- Deprecation notices for breaking changes

**NFR-18: CORS Support**
- Allow configured origins
- Support for frontend applications
- Credentials support enabled

---

## 5. Technical Architecture

### 5.1 Layered Architecture

```
┌─────────────────────────────────────┐
│     API Layer (FastAPI)             │
│  - auth_routes.py                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│     Service Layer                   │
│  - AuthService                      │
│    - login()                        │
│    - verify_token()                 │
│    - logout()                       │
└──────────────┬──────────────────────┘
               │
        ┌──────┴──────┐
        │             │
┌───────▼──────┐  ┌──▼──────────────┐
│ Repository   │  │ Client Layer    │
│ Layer        │  │ (HTTP)          │
│ - Tokens     │  │ - Users Service │
│ - Audit Logs │  │   Internal API  │
└───────┬──────┘  └──┬──────────────┘
        │            │
        └─────┬──────┘
              │
┌─────────────▼──────────────────────┐
│     Security Layer                 │
│  - JWTUtil                         │
│  - PasswordUtil                    │
│  - JWTValidator                    │
└──────────────┬─────────────────────┘
               │
┌──────────────▼──────────────────────┐
│     Database Layer (PostgreSQL)     │
│  - auth_tokens                      │
│  - auth_audit_logs                  │
└─────────────────────────────────────┘
```

### 5.2 Database Schema

#### 5.2.1 auth_tokens Table
**Purpose**: Store JWT token metadata

**Columns**:
- `id`: UUID PRIMARY KEY
- `user_id`: BIGINT NOT NULL
- `login_id`: VARCHAR(255) NOT NULL
- `token_jti`: VARCHAR(255) NOT NULL UNIQUE
- `issued_at`: TIMESTAMP WITH TIME ZONE NOT NULL
- `expires_at`: TIMESTAMP WITH TIME ZONE NOT NULL
- `is_revoked`: BOOLEAN DEFAULT FALSE
- `created_at`: TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP

**Indexes**:
- `idx_auth_tokens_user_id` on user_id
- `idx_auth_tokens_token_jti` on token_jti
- `idx_auth_tokens_expires_at` on expires_at
- `idx_auth_tokens_is_revoked` on is_revoked

**Constraints**:
- `valid_expiry`: expires_at > issued_at

#### 5.2.2 auth_audit_logs Table
**Purpose**: Audit trail for authentication

**Columns**:
- `id`: UUID PRIMARY KEY
- `login_id`: VARCHAR(255) NOT NULL
- `user_id`: BIGINT
- `action`: auth_action_enum NOT NULL
- `reason`: VARCHAR(500)
- `ip_address`: INET
- `user_agent`: VARCHAR(1000)
- `created_at`: TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP

**Indexes**:
- `idx_auth_audit_logs_user_id` on user_id
- `idx_auth_audit_logs_login_id` on login_id
- `idx_auth_audit_logs_action` on action
- `idx_auth_audit_logs_created_at` on created_at

#### 5.2.3 Enums
- `auth_action_enum`: LOGIN_SUCCESS, LOGIN_FAILURE, TOKEN_REVOKED

#### 5.2.4 Views
- `active_auth_tokens`: Not revoked and not expired tokens
- `recent_auth_logins`: Logins from last 30 days
- `failed_auth_logins`: All failed login attempts

#### 5.2.5 Functions
- `cleanup_expired_tokens()`: Revoke expired tokens

### 5.3 External Service Integrations

#### 5.3.1 Users Service Integration
**Direction**: Auth Service → Users Service (one-way)

**Purpose**: Credential verification

**Endpoints Called**:
- `POST /internal/v1/users/verify`: Verify credentials
- `GET /internal/v1/users/{login_id}/status`: Check user status

**Configuration**:
- `USER_SERVICE_URL`: Users Service base URL
- `USER_SERVICE_TIMEOUT`: Request timeout (default: 10 seconds)

**Error Handling**:
- Connection refused: Return 503 Service Unavailable
- Timeout: Return 503 Service Unavailable
- 404 from Users Service: Return 404 User Not Found
- 401 from Users Service: Return 401 Invalid Credentials

---

## 6. Data Models

### 6.1 Request Models

#### LoginRequest
```python
{
  "login_id": str,
  "password": str
}
```

#### VerifyTokenRequest
```python
{
  "token": str
}
```

### 6.2 Response Models

#### LoginResponse
```python
{
  "access_token": str,
  "token_type": str (default: "Bearer"),
  "expires_in": int (seconds),
  "user_id": str (UUID),
  "login_id": str,
  "role": str
}
```

#### VerifyTokenResponse
```python
{
  "is_valid": bool,
  "user_id": str,
  "login_id": str,
  "role": str,
  "expires_at": datetime
}
```

#### ErrorResponse
```python
{
  "error": str,
  "message": str
}
```

### 6.3 JWT Token Structure

#### Header
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

#### Payload
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

**Claims**:
- `sub`: User ID (UUID)
- `login_id`: User login identifier
- `role`: User role (ADMIN, TELLER, CUSTOMER)
- `iat`: Issued at timestamp
- `exp`: Expiry timestamp
- `jti`: JWT ID (unique token identifier)

---

## 7. Error Handling

### 7.1 Error Response Format
```json
{
  "error": "error_code",
  "message": "Human-readable error message"
}
```

### 7.2 Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `invalid_credentials` | 401 | Invalid login credentials |
| `user_inactive` | 401 | User account is inactive |
| `user_not_found` | 404 | User not found |
| `service_unavailable` | 503 | Users Service unavailable |
| `invalid_token` | 401 | Token is invalid or expired |
| `token_revoked` | 401 | Token has been revoked |
| `missing_credentials` | 400 | login_id or password missing |
| `internal_error` | 500 | Unexpected server error |
| `database_error` | 500 | Database operation failed |

---

## 8. Authentication Flow

```
1. Client → Auth Service
   POST /api/v1/auth/login
   {login_id, password}
        │
        ▼
2. Auth Service → Users Service
   POST /internal/v1/users/verify
   {login_id, password}
        │
        ├─ User Not Found (404)
        │   → Audit: LOGIN_FAILURE (User not found)
        │   → Response: 404
        │
        ├─ User Inactive (401)
        │   → Audit: LOGIN_FAILURE (User inactive)
        │   → Response: 401
        │
        ├─ Invalid Password (401)
        │   → Audit: LOGIN_FAILURE (Invalid password)
        │   → Response: 401
        │
        └─ Valid Credentials (200)
           ▼
3. Auth Service generates JWT token
   - Claims: sub, login_id, role, iat, exp, jti
   - Sign with HS256
        │
        ▼
4. Auth Service stores token metadata
   Table: auth_tokens
   - token_jti, user_id, login_id, expires_at
        │
        ▼
5. Auth Service logs success
   Table: auth_audit_logs
   - action: LOGIN_SUCCESS, ip_address, user_agent
        │
        ▼
6. Response: 200 + {access_token, expires_in, user_id, role}
```

---

## 9. Testing Requirements

### 9.1 Test Coverage

**Minimum Coverage**: 80% overall

**Coverage by Layer**:
- API Layer: 85%
- Service Layer: 90%
- Repository Layer: 85%
- Security Layer: 95%

### 9.2 Test Scenarios

**Login**:
- ✅ Valid credentials
- ✅ Invalid password
- ✅ User not found
- ✅ Inactive user
- ✅ Users Service unavailable
- ✅ Database error

**Token Generation**:
- ✅ Valid token structure
- ✅ Token expiry set correctly
- ✅ Unique token JTI
- ✅ Correct claims

**Token Verification**:
- ✅ Valid token
- ✅ Expired token
- ✅ Invalid signature
- ✅ Revoked token

**Audit Logging**:
- ✅ Success logged
- ✅ Failure logged with reason
- ✅ IP address captured
- ✅ User agent captured

---

## 10. Deployment Requirements

### 10.1 Environment Configuration

#### Development
- Debug mode enabled
- Verbose logging
- Local database
- Hot reload enabled

#### Staging
- Production-like configuration
- Moderate logging
- Staging database
- Performance testing

#### Production
- Debug mode disabled
- Error-level logging
- Production database
- High availability setup

### 10.2 Environment Variables

**Required**:
- `DATABASE_HOST`: PostgreSQL host
- `DATABASE_PORT`: PostgreSQL port
- `DATABASE_NAME`: Database name (gdb_auth_db)
- `DATABASE_USER`: Database user
- `DATABASE_PASSWORD`: Database password
- `JWT_SECRET_KEY`: Secret for JWT signing (SHARED with all services)
- `USER_SERVICE_URL`: Users Service base URL

**Optional**:
- `ENVIRONMENT`: development|staging|production
- `DEBUG`: true|false
- `LOG_LEVEL`: DEBUG|INFO|WARNING|ERROR
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8004)
- `MIN_DB_POOL_SIZE`: Minimum connections (default: 5)
- `MAX_DB_POOL_SIZE`: Maximum connections (default: 20)
- `JWT_ALGORITHM`: JWT algorithm (default: HS256)
- `JWT_EXPIRY_MINUTES`: Token expiry (default: 30)
- `USER_SERVICE_TIMEOUT`: Request timeout (default: 10)
- `CORS_ORIGINS`: Allowed CORS origins

### 10.3 Critical Configuration Notes

**⚠️ JWT_SECRET_KEY**:
- MUST be identical across ALL services (Auth, Accounts, Transactions, Users)
- Use strong random key (at least 32 characters)
- Never commit to version control
- Rotate periodically (requires restart of all services)

### 10.4 Deployment Options

#### Docker
- Dockerfile provided
- Multi-stage build for optimization
- Health check configuration
- Environment variable injection

#### Kubernetes
- Deployment manifest
- Service definition
- ConfigMap for configuration
- Secret for JWT_SECRET_KEY
- Horizontal Pod Autoscaler
- Liveness and readiness probes

#### Traditional Server
- Gunicorn with Uvicorn workers
- Systemd service file
- Nginx reverse proxy
- SSL/TLS termination

### 10.5 Monitoring & Observability

**Health Check**: `GET /api/v1/auth/health`
**Readiness Check**: `GET /ready`

**Metrics** (Future):
- Login success rate
- Login failure rate
- Response time (p50, p95, p99)
- Active tokens count
- Database pool utilization

**Logging**:
- Structured logs
- Request/response logging
- Error tracking
- Audit trail for authentication

**Alerting** (Future):
- High login failure rate
- Users Service unavailable
- Database connection issues
- Slow response time

---

## 11. Dependencies

### 11.1 Python Dependencies

**Core Framework**:
- fastapi==0.104.1
- uvicorn[standard]==0.24.0
- pydantic==2.4.2
- pydantic-settings==2.0.3

**Database**:
- asyncpg==0.29.0

**Security**:
- bcrypt==4.1.1
- python-jose[cryptography]==3.3.0
- PyJWT==2.8.0

**HTTP Client**:
- httpx==0.25.1

**Development**:
- pytest==7.4.3
- pytest-asyncio==0.21.1
- pytest-cov==4.1.0

### 11.2 External Services

**Required**:
- PostgreSQL 12.0+
- Users Service (for credential verification)

---

## 12. Constraints & Assumptions

### 12.1 Constraints

**Technical**:
- Python 3.9+ required
- PostgreSQL 12.0+ required
- Async/await programming model
- RESTful API design

**Business**:
- No token refresh (new login = new token)
- Short-lived tokens (15-30 minutes)
- One-way communication (Auth → Users only)
- No password storage or hashing

**Security**:
- JWT_SECRET_KEY must be shared across services
- HS256 algorithm only
- HTTPS required in production

### 12.2 Assumptions

**Operational**:
- Users Service is available
- Network connectivity stable
- Database supports ACID transactions

**Technical**:
- Load balancer handles SSL termination
- Monitoring infrastructure exists
- Log aggregation available

**Business**:
- Users are created via Users Service
- No self-service password reset
- No multi-factor authentication (future)

---

## 13. Future Enhancements

### 13.1 Planned Features

**Authentication**:
- Multi-factor authentication (MFA)
- Biometric authentication
- Social login (OAuth2)
- SAML/SSO integration

**Token Management**:
- Refresh tokens
- Token revocation API
- Token blacklisting
- Token rotation

**Security**:
- Rate limiting
- Account lockout after failed attempts
- IP whitelisting/blacklisting
- Geo-blocking

**Audit**:
- Enhanced audit queries
- Audit report generation
- Compliance reporting
- Real-time monitoring

### 13.2 Technical Improvements

**Performance**:
- Caching layer (Redis)
- Read replicas for audit queries
- Query optimization
- Connection pooling optimization

**Observability**:
- Distributed tracing
- Metrics dashboard
- Real-time alerting
- Log aggregation

**Resilience**:
- Circuit breaker pattern
- Retry with exponential backoff
- Bulkhead isolation
- Chaos engineering

---

## 14. Troubleshooting Guide

### 14.1 Common Issues

#### Issue: Cannot connect to database
**Error**: `Failed to connect to database: connection refused`

**Solution**:
1. Check PostgreSQL is running
2. Verify DATABASE_HOST, DATABASE_PORT
3. Verify DATABASE_USER, DATABASE_PASSWORD
4. Check if gdb_auth_db exists
5. Run schema setup

#### Issue: Cannot connect to Users Service
**Error**: `User service unavailable: Connection refused`

**Solution**:
1. Verify Users Service is running on port 8003
2. Check USER_SERVICE_URL in .env
3. Verify network connectivity
4. Check Users Service logs

#### Issue: Login fails with "Invalid credentials"
**Possible Causes**:
1. User doesn't exist in Users Service
2. User account is inactive
3. Password is incorrect
4. Bcrypt hash format is invalid

**Debug**:
- Check Users Service has the user
- Check user is active
- Check auth logs for failure reason

#### Issue: Token verification fails in other services
**Error**: `Invalid token: Signature verification failed`

**Causes**:
1. JWT_SECRET_KEY is different across services
2. Token is expired
3. Token is revoked
4. Token signature is malformed

**Solution**:
1. Verify JWT_SECRET_KEY is identical in all services
2. Check token expiry
3. Check if token_jti is revoked
4. Verify token format

---

## 15. Glossary

| Term | Definition |
|------|------------|
| **JWT** | JSON Web Token for stateless authentication |
| **JTI** | JWT ID, unique identifier for each token |
| **HS256** | HMAC SHA-256 signing algorithm |
| **Bcrypt** | Password hashing algorithm with salt |
| **Audit Trail** | Record of all authentication attempts |
| **Token Revocation** | Marking token as invalid before expiry |

---

## 16. Approval & Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Owner | | | |
| Technical Lead | | | |
| Security Officer | | | |
| QA Lead | | | |

---

## 17. Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2026-02-10 | GDB Architecture Team | Initial requirements document |

---

## 18. References

- **API Documentation**: http://localhost:8004/api/v1/docs
- **Setup Guide**: README.md
- **Database Schema**: app/database/auth_schema.sql
- **JWT Specification**: RFC 7519

---

**END OF REQUIREMENTS DOCUMENT**
