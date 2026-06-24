# Authentication Service - Quick Start Guide

**Time to First Login**: ~5 minutes  
**Prerequisites**: PostgreSQL running, Python 3.9+

---

## 🚀 Quick Start (5 Minutes)

### Step 1: Install Dependencies (1 minute)
```bash
cd auth_service
pip install -r requirements.txt
```

### Step 2: Initialize Database (1 minute)
```bash
python setup_db.py
```

Expected output:
```
Connected to database: gdb_auth_db
✓ Created auth_tokens table
✓ Created auth_audit_logs table
✓ Created all indexes
✅ Successfully initialized auth database!
```

### Step 3: Start the Service (1 minute)
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8004 --reload
```

Expected output:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8004
```

### Step 4: Test Login (2 minutes)
```bash
curl -X POST http://localhost:8004/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "login_id": "doe.doe",
    "password": "test_password"
  }'
```

Expected response (HTTP 200):
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

**✅ Done!** Your Auth Service is running!

---

## 📖 What You Now Have

✅ **Working Authentication Service**
- Login endpoint: `POST /api/v1/auth/login`
- Health check: `GET /api/v1/auth/health`
- Swagger docs: `http://localhost:8004/docs`

✅ **JWT Token Management**
- HS256 encrypted tokens
- 30-minute expiry
- Unique token ID (JTI)
- Claim extraction

✅ **Complete Audit Trail**
- All login attempts logged
- Success/failure tracking
- Client IP and user agent
- Timestamp recording

✅ **Integrated with User Service**
- Communicates with User Service on port 8003
- Credential verification
- User status checking
- User role retrieval

---

## 🔍 Verify Setup

### Check Service Health
```bash
curl http://localhost:8004/api/v1/auth/health
```

### Check Database
```bash
python verify_db.py
```

### Check Swagger Docs
```
http://localhost:8004/docs
```

### Check Latest Login
```bash
python -c "
import asyncio
import asyncpg
from pathlib import Path
import sys

sys.path.insert(0, str(Path('.').absolute()))

async def check():
    conn = await asyncpg.connect(
        host='localhost', port=5432,
        database='gdb_auth_db',
        user='postgres', password='postgres'
    )
    record = await conn.fetchrow(
        'SELECT login_id, user_id, action, created_at FROM auth_audit_logs ORDER BY created_at DESC LIMIT 1'
    )
    print(f'Latest Login: {record}')
    await conn.close()

asyncio.run(check())
"
```

---

## 📝 API Quick Reference

### Login
```
POST /api/v1/auth/login
Content-Type: application/json

{
  "login_id": "doe.doe",
  "password": "password"
}

Response (200):
{
  "access_token": "...",
  "token_type": "Bearer",
  "expires_in": 1800,
  "user_id": 2,
  "login_id": "doe.doe",
  "role": "USER"
}
```

### Health Check
```
GET /api/v1/auth/health

Response (200):
{
  "status": "ok",
  "service": "auth-service"
}
```

### Swagger Docs
```
GET /docs

Open in browser: http://localhost:8004/docs
```

---

## 🐛 Troubleshooting

### Service Won't Start
**Issue**: `Connection refused` or `Database not found`

**Solution**:
```bash
# 1. Check PostgreSQL is running
# 2. Initialize database
python setup_db.py
# 3. Start service again
python -m uvicorn app.main:app --host 0.0.0.0 --port 8004
```

### Login Returns 503
**Issue**: "User service is unavailable"

**Solution**:
- Start User Service on port 8003
- Check User Service is responding
- Verify USER_SERVICE_URL in .env

### Login Returns 401
**Issue**: "Invalid credentials"

**Solution**:
- Verify login_id and password
- Check User Service has test users
- Review audit logs: `python verify_db.py`

### Database Already Exists
**Issue**: "database gdb_auth_db already exists"

**Solution**:
```bash
# Reset the database
python reset_db.py
# Then initialize
python setup_db.py
```

---

## 📊 Files Overview

| File | Purpose | Lines |
|------|---------|-------|
| `app/main.py` | FastAPI application | 150 |
| `app/api/auth_routes.py` | Login endpoint | 200 |
| `app/services/auth_service.py` | Business logic | 280 |
| `app/database/db.py` | Database connection | 155 |
| `app/repository/auth_token_repo.py` | Token storage | 241 |
| `app/repository/auth_audit_repo.py` | Audit logging | 276 |
| `setup_db.py` | Database initialization | 250 |
| `verify_db.py` | Database verification | 200 |
| `.env` | Configuration | 80 |
| `requirements.txt` | Dependencies | 20 |

---

## 🔐 Security Notes

✅ **Passwords NOT stored in Auth Service**
- User Service handles password hashing
- Auth Service only verifies via User Service API

✅ **JWT Secret in Environment**
- Never commit secrets to repository
- Store JWT_SECRET_KEY in .env (not in code)

✅ **HTTPS in Production**
- Use reverse proxy (nginx, HAProxy)
- Enable HTTPS at gateway level

✅ **Audit Trail**
- All login attempts logged
- Queryable for security analysis
- Includes client IP and user agent

---

## 🚀 Next Steps

### For Development
1. Run tests: `pytest tests/test_auth.py -v`
2. Review code: Open `app/` directory
3. Check logs: Watch service console output
4. Debug: Use `/docs` Swagger interface

### For Production
1. Set secure JWT_SECRET_KEY
2. Update CORS_ORIGINS for your domain
3. Use HTTPS at gateway level
4. Configure PostgreSQL for HA
5. Set up monitoring and alerting
6. Run load tests: `pytest tests/ -v --load`

### For Integration
1. Start this Auth Service (port 8004)
2. Ensure User Service running (port 8003)
3. Test login works
4. Get JWT token
5. Use token in other services: `Authorization: Bearer <token>`

---

## 📚 Documentation

| Document | Contains |
|----------|----------|
| `README.md` | Setup, architecture, API reference |
| `REQUIREMENTS.md` | All functional/non-functional requirements |
| `AUTHENTICATION_FLOW_VERIFICATION.md` | Complete flow with database verification |
| `COMPLETION_SUMMARY.md` | What was delivered, features, checklist |
| `QUICK_START.md` | This file - quick setup guide |

---

## 🎯 Success Indicators

After following this guide, you should see:

✅ Service running on http://0.0.0.0:8004  
✅ Health check responding with `"status": "ok"`  
✅ Login endpoint returning JWT token  
✅ Database record created in auth_tokens table  
✅ Audit log entry in auth_audit_logs table  
✅ Swagger docs available at /docs  

---

## 💡 Tips

**Tip 1**: Use curl for quick testing
```bash
curl -X POST http://localhost:8004/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login_id":"doe.doe","password":"password"}'
```

**Tip 2**: Check logs in real-time
```
Watch the console where you started the service
Log entries show all operations
```

**Tip 3**: Use Swagger for interactive testing
```
Open http://localhost:8004/docs in browser
Try out endpoints directly from docs
```

**Tip 4**: Reset database if needed
```bash
python reset_db.py
python setup_db.py
```

**Tip 5**: Verify database state
```bash
python verify_db.py
```

---

## 🆘 Getting Help

**Check these in order:**
1. Service logs in console
2. `python verify_db.py` output
3. Swagger docs at /docs
4. `README.md` for detailed setup
5. `REQUIREMENTS.md` for specifications

---

## ⏱️ Typical Flow

```
1. npm install (1 min)
   ↓
2. python setup_db.py (1 min)
   ↓
3. python -m uvicorn ... (1 min, stays running)
   ↓
4. curl POST /login (1 min, in another terminal)
   ↓
5. Get JWT token ✅
   ↓
6. Use token in other services 🎉
```

---

## 🎉 Congratulations!

You now have a fully functional, production-ready Authentication Service!

**What's working:**
- ✅ User login
- ✅ JWT token generation
- ✅ Token storage
- ✅ Audit logging
- ✅ Error handling
- ✅ Health checks
- ✅ API documentation

**What's next:**
- Integrate with other microservices
- Test with real users
- Set up monitoring
- Deploy to production

---

**Questions?** Check the documentation files or review the code comments.

**Ready to integrate?** See README.md for inter-service communication details.

**Happy authenticating! 🔐**
