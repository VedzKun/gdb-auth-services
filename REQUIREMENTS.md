# Authentication Service Requirements

**Version**: 1.0  
**Status**: Production Ready  
**Date**: December 24, 2025

---

## Executive Summary

The Authentication Service is a centralized JWT-based authentication microservice that handles user login and token generation. It acts as a single entry point for all authentication operations in the GDB Micro Banking System.

**Key Characteristics:**
- Stateless token-based authentication using JWT (HS256)
- Centralized authentication, decentralized authorization
- Single login endpoint for all clients
- Complete audit trail of all authentication attempts
- One-way communication with User Service

---

## Functional Requirements

### FR1: User Login Endpoint

**Requirement**: The service must provide a single POST endpoint for user authentication.

**Details**:
- **Endpoint**: `POST /api/v1/auth/login`
- **Input**: 
  - `login_id` (string, 1-255 chars): User's login identifier
  - `password` (string, 1-1000 chars): User's plain text password
- **Success Response** (HTTP 200):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 1800,
    "user_id": 2,
    "login_id": "doe.doe",
    "role": "USER"
  }
  ```
- **Error Responses**:
  - HTTP 401: Invalid credentials or user inactive
  - HTTP 404: User not found
  - HTTP 503: User Service unavailable
  - HTTP 500: Internal server error
- **Request Validation**: 
  - Both fields required
  - Password min 1 character
  - login_id max 255 characters
- **Rate Limiting**: Not required (implement at gateway level)

**Acceptance Criteria**:
- ✅ Accepts valid LoginRequest
- ✅ Returns proper TokenResponse on success
- ✅ Returns appropriate error codes on failure
- ✅ Validates all input fields
- ✅ Handles missing/malformed JSON

---

### FR2: User Service Integration

**Requirement**: Auth Service must verify user credentials against User Service.

**Details**:
- **Flow**:
  1. Auth Service receives login_id and password
  2. Calls User Service POST /internal/v1/users/verify with credentials
  3. User Service returns user data or 401/404
  4. Auth Service processes response

- **User Service Response (Success)**:
  ```json
  {
    "user_id": 2,
    "login_id": "doe.doe",
    "role": "USER",
    "is_active": true
  }
  ```

- **User Service Response (Failure)**:
  - 401 Unauthorized: Invalid credentials
  - 404 Not Found: User not found

- **Service Unavailability**:
  - Connection timeout: HTTP 503
  - Network error: HTTP 503
  - Invalid response: HTTP 503

**Acceptance Criteria**:
- ✅ Sends correct payload to User Service
- ✅ Handles all response codes properly
- ✅ Extracts user data correctly
- ✅ Handles service unavailability gracefully
- ✅ Logs all communication attempts

---

### FR3: JWT Token Generation

**Requirement**: Auth Service must generate valid JWT tokens with required claims.

**Details**:
- **Algorithm**: HS256 (HMAC with SHA-256)
- **Secret Key**: From environment variable `JWT_SECRET_KEY`
- **Token Claims**:
  - `sub` (subject): User ID from User Service
  - `login_id`: User's login identifier
  - `role`: User's role from User Service
  - `iat` (issued at): Current Unix timestamp
  - `exp` (expiration): iat + JWT_EXPIRY_MINUTES
  - `jti` (JWT ID): Unique token identifier (UUID)

- **Default Expiry**: 30 minutes (configurable)
- **Token Format**: Compact serialization (3 base64 parts separated by dots)

**Acceptance Criteria**:
- ✅ All required claims present
- ✅ Claims have correct types and values
- ✅ Signature valid with configured secret
- ✅ Tokens are properly URL-safe base64 encoded
- ✅ Expiry calculated correctly

---

### FR4: Token Storage & Tracking

**Requirement**: Auth Service must store issued tokens for revocation and audit purposes.

**Details**:
- **Storage Location**: `auth_tokens` table in gdb_auth_db
- **Stored Fields**:
  - `id`: UUID (primary key)
  - `user_id`: BIGINT (from User Service)
  - `login_id`: VARCHAR(255)
  - `token_jti`: VARCHAR(255) UNIQUE (JWT ID)
  - `issued_at`: TIMESTAMP WITH TIME ZONE
  - `expires_at`: TIMESTAMP WITH TIME ZONE
  - `is_revoked`: BOOLEAN (default: false)
  - `created_at`: TIMESTAMP WITH TIME ZONE (default: now)

- **Indexes**: user_id, token_jti, expires_at, is_revoked
- **Constraints**: expires_at > issued_at

**Acceptance Criteria**:
- ✅ Token stored immediately after generation
- ✅ All fields populated correctly
- ✅ Token JTI is unique
- ✅ Expiry time consistent with JWT exp claim
- ✅ Indexes created for performance

---

### FR5: User Status Verification

**Requirement**: Auth Service must verify user is active before issuing token.

**Details**:
- **Check**: User's `is_active` field from User Service response
- **Action if Inactive**:
  - Return HTTP 401 (Unauthorized)
  - Log audit event with reason "User inactive"
  - Do NOT generate token

- **Flow**:
  1. User Service returns user data with is_active field
  2. Auth Service checks is_active == true
  3. If false, reject login
  4. If true, continue with token generation

**Acceptance Criteria**:
- ✅ Rejects inactive users
- ✅ Logs reason in audit trail
- ✅ Returns HTTP 401, not 404
- ✅ Clear error message in response

---

### FR6: Audit Logging

**Requirement**: Auth Service must log all authentication attempts for security and compliance.

**Details**:
- **Storage Location**: `auth_audit_logs` table in gdb_auth_db
- **Logged Events**:
  - LOGIN_SUCCESS: Successful authentication
  - LOGIN_FAILURE: Failed login attempt
  - TOKEN_REVOKED: Token revocation

- **Logged Fields**:
  - `id`: UUID
  - `login_id`: VARCHAR(255) - always captured
  - `user_id`: BIGINT - captured if user found
  - `action`: ENUM (LOGIN_SUCCESS, LOGIN_FAILURE, TOKEN_REVOKED)
  - `reason`: VARCHAR(500) - failure reason
  - `ip_address`: INET - client IP
  - `user_agent`: VARCHAR(1000) - client user agent
  - `created_at`: TIMESTAMP WITH TIME ZONE

- **Failure Reasons** (examples):
  - "Invalid credentials or user not found"
  - "User inactive"
  - "User service unavailable"
  - "Token generation failed"

**Acceptance Criteria**:
- ✅ All login attempts logged
- ✅ Successful logins clearly marked
- ✅ Failure reasons captured
- ✅ Client context stored (IP, user agent)
- ✅ Timestamps accurate
- ✅ Logs not lost on failure

---

### FR7: Error Handling

**Requirement**: Auth Service must return appropriate HTTP status codes and error messages.

**Details**:
- **HTTP 200**: Successful login
- **HTTP 401**: 
  - Invalid credentials
  - User inactive
- **HTTP 404**: 
  - User not found
- **HTTP 503**: 
  - User Service unavailable
  - Database unavailable
  - Service degradation
- **HTTP 500**: 
  - Unexpected errors
  - Token generation failure
  - Configuration errors

- **Error Response Format**:
  ```json
  {
    "error": "error_code",
    "message": "Human-readable description"
  }
  ```

**Acceptance Criteria**:
- ✅ Correct status codes returned
- ✅ Error messages are clear and actionable
- ✅ No sensitive information leaked
- ✅ Consistent error format
- ✅ Errors logged server-side

---

### FR8: Health Check Endpoints

**Requirement**: Auth Service must provide health check endpoints.

**Details**:
- **Health Check Endpoint**: `GET /api/v1/auth/health`
  - Response: HTTP 200
  - Body: `{"status": "ok", "service": "auth-service"}`
  - Purpose: Basic liveness check

- **Readiness Endpoint** (optional): `GET /api/v1/auth/ready`
  - Checks database connectivity
  - Response: HTTP 200 if ready, 503 if not

**Acceptance Criteria**:
- ✅ Health endpoint always responds
- ✅ Quick response time (<100ms)
- ✅ Can be used by load balancers
- ✅ Readiness checks dependencies

---

### FR9: CORS and Request Validation

**Requirement**: Auth Service must handle CORS and validate all requests.

**Details**:
- **CORS**: Configured via `CORS_ORIGINS` environment variable
- **Content-Type**: Must be application/json
- **Request Validation**: Via Pydantic models
  - Required fields enforced
  - Type checking performed
  - Length constraints applied
  - Invalid requests return 422 Unprocessable Entity

**Acceptance Criteria**:
- ✅ CORS headers present in responses
- ✅ Only configured origins accepted
- ✅ Invalid requests rejected early
- ✅ Validation errors clearly returned
- ✅ Swagger docs available at /docs

---

## Non-Functional Requirements

### NFR1: Performance

**Requirement**: Login response time must be acceptable.

**Details**:
- **Target**: <2 seconds for successful login (p95)
  - User Service call: ~500ms
  - JWT generation: <10ms
  - Database operations: <100ms
  - Network latency: ~500ms
- **Concurrent Users**: Support minimum 100 concurrent login requests
- **Token Generation Rate**: >1000 tokens/second per instance

**Acceptance Criteria**:
- ✅ Login completes within 2 seconds
- ✅ No request timeouts under normal load
- ✅ Database queries optimized (indexes present)
- ✅ No unnecessary round-trips

---

### NFR2: Security

**Requirement**: Auth Service must follow security best practices.

**Details**:
- **Password Handling**: 
  - ✅ Passwords NOT stored in Auth Service
  - ✅ Passwords verified by User Service
  - ✅ Passwords never logged or exposed

- **JWT Security**:
  - ✅ Secret key stored in environment (not in code)
  - ✅ HS256 algorithm configured
  - ✅ Tokens expire after configured time
  - ✅ JTI claims prevent token reuse

- **Audit Trail**:
  - ✅ All attempts logged with IP/user agent
  - ✅ Failed logins recorded
  - ✅ Logs queryable for security analysis

- **Database**:
  - ✅ Connection pooling configured
  - ✅ Credentials from environment
  - ✅ SQL injection prevention (parameterized queries)

- **HTTPS**: 
  - ✅ Service expects HTTPS in production
  - ✅ Enforced at gateway/proxy level

**Acceptance Criteria**:
- ✅ No plaintext passwords in logs
- ✅ Secret key never in version control
- ✅ All authentication flows audited
- ✅ Security headers configured (if applicable)

---

### NFR3: Reliability

**Requirement**: Auth Service must be highly reliable.

**Details**:
- **Uptime Target**: 99.9% (>99.9 hours per month)
- **Availability**:
  - Health checks every 10 seconds
  - Auto-restart on failure (container orchestration)
  - Graceful shutdown on SIGTERM

- **Database Resilience**:
  - Connection pooling (min 5, max 20 connections)
  - Connection retry logic
  - Timeout handling (10 seconds default)

- **User Service Resilience**:
  - Timeout: 30 seconds
  - Retry not implemented (fail fast)
  - Degradation: Return 503

**Acceptance Criteria**:
- ✅ Service recovers from brief outages
- ✅ No data loss on restart
- ✅ Database connections properly managed
- ✅ Graceful handling of dependency failures

---

### NFR4: Maintainability

**Requirement**: Code must be well-organized and documented.

**Details**:
- **Architecture**:
  - Layered architecture: API → Service → Repository → Database
  - Clear separation of concerns
  - Dependency injection where practical

- **Code Organization**:
  - `app/api/`: API routes and endpoints
  - `app/services/`: Business logic
  - `app/repository/`: Database operations
  - `app/database/`: Connection management
  - `app/security/`: JWT and crypto utilities
  - `app/models/`: Pydantic request/response models
  - `app/exceptions/`: Custom exceptions
  - `app/config/`: Environment configuration

- **Documentation**:
  - README.md: Setup and usage
  - REQUIREMENTS.md: This file
  - Docstrings: All public functions
  - Type hints: All function signatures
  - Swagger/OpenAPI: Automatic from FastAPI

**Acceptance Criteria**:
- ✅ Code follows PEP 8 style
- ✅ Clear module organization
- ✅ Docstrings on all public functions
- ✅ Type hints used consistently
- ✅ Swagger docs generated

---

### NFR5: Scalability

**Requirement**: Service must scale horizontally.

**Details**:
- **Stateless Design**: 
  - ✅ No in-memory state
  - ✅ Database is single source of truth
  - ✅ Multiple instances can run independently

- **Database Scaling**:
  - Connection pooling isolates instances
  - Read replicas possible for audit queries
  - Token table indexes support high volume

- **Deployment**:
  - Containerized (Dockerfile ready)
  - Environment-based configuration
  - Health checks for load balancer

**Acceptance Criteria**:
- ✅ Stateless (no session affinity needed)
- ✅ Can scale to 10+ instances
- ✅ Database connection pooling prevents exhaustion
- ✅ Load balancer friendly

---

## API Specifications

### Endpoint: POST /api/v1/auth/login

**Description**: Authenticate user and receive JWT token

**Request**:
```
POST /api/v1/auth/login
Content-Type: application/json

{
  "login_id": "doe.doe",
  "password": "user_password"
}
```

**Success Response (200)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 1800,
  "user_id": 2,
  "login_id": "doe.doe",
  "role": "USER"
}
```

**Error Response (401)**:
```json
{
  "detail": {
    "error": "invalid_credentials",
    "message": "Invalid login credentials"
  }
}
```

**Error Response (404)**:
```json
{
  "detail": {
    "error": "user_not_found",
    "message": "User not found"
  }
}
```

**Error Response (503)**:
```json
{
  "detail": {
    "error": "service_unavailable",
    "message": "User service is unavailable"
  }
}
```

---

### Endpoint: GET /api/v1/auth/health

**Description**: Service health check

**Request**:
```
GET /api/v1/auth/health
```

**Response (200)**:
```json
{
  "status": "ok",
  "service": "auth-service"
}
```

---

## Database Schema

**Tables**: 2
- `auth_tokens`: JWT token metadata
- `auth_audit_logs`: Authentication audit trail

**Views**: Optional
- `active_auth_tokens`: Non-revoked, non-expired tokens
- `recent_auth_logins`: Recent login attempts

---

## Environment Configuration

**Required Variables**:
```env
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=gdb_auth_db
DATABASE_USER=postgres
DATABASE_PASSWORD=secret

USER_SERVICE_URL=http://127.0.0.1:8003
USER_SERVICE_TIMEOUT=30

JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=30

CORS_ORIGINS=["http://localhost:3000"]
```

---

## Testing Requirements

**Test Coverage**: Minimum 80%

**Test Categories**:
1. **Unit Tests** (20 tests)
   - JWT token generation/verification
   - Password utilities
   - Exception handling
   - Model validation

2. **Integration Tests** (15 tests)
   - Login flow with valid credentials
   - Login failures (invalid, user not found, inactive)
   - User Service unavailable
   - Database operations
   - Audit logging

3. **API Tests** (10 tests)
   - Request validation
   - Error responses
   - Health check
   - Swagger documentation

---

## Deployment Requirements

**Prerequisites**:
- Python 3.9+
- PostgreSQL 12+
- Docker (optional, for containerization)

**Dependencies**: See requirements.txt
- FastAPI 0.104.1
- asyncpg 0.29.0
- PyJWT 2.10.1
- Pydantic 2.5.0
- aiohttp 3.9.1
- python-dotenv 1.0.0

**Ports**: 
- Service: 8004
- PostgreSQL: 5432

**Database Setup**:
```bash
python setup_db.py      # Create database and tables
python reset_db.py      # Reset database (dev only)
```

---

## Monitoring & Observability

**Metrics** (to be implemented):
- Login success rate
- Login failure rate
- Response time distribution
- Active sessions
- Token revocation events

**Logs** (currently implemented):
- Authentication attempts (success/failure)
- Audit trail (IP, user agent)
- Error stack traces
- Service startup/shutdown

**Health Checks**:
- `/api/v1/auth/health` - Liveness
- `/api/v1/auth/ready` - Readiness (with DB check)

---

## Security Considerations

1. **Token Expiry**: 30 minutes default (configurable)
2. **Token Revocation**: Via is_revoked flag in database
3. **Audit Trail**: All attempts logged with context
4. **Rate Limiting**: Not implemented (use API gateway)
5. **HTTPS**: Required in production (use reverse proxy)
6. **CORS**: Configured per environment
7. **Secret Rotation**: Support via environment update + restart

---

## Compliance

- **Audit Trail**: ✅ All login attempts logged
- **Data Retention**: Configure via database policies
- **Sensitive Data**: ✅ No passwords stored or logged
- **Error Messages**: ✅ No sensitive info exposed

---

## Future Enhancements

1. Token refresh endpoint (extend expiry)
2. Token revocation endpoint (logout)
3. Multi-factor authentication (2FA)
4. Session management with Redis
5. Rate limiting at service level
6. OAuth 2.0 / OpenID Connect support
7. Social login integration
8. Passwordless authentication

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-24  
**Maintained By**: GDB Architecture Team
