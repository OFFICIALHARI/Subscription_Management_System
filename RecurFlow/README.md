# RecurFlow — Subscription Operations & Revenue Management

RecurFlow is an enterprise subscription-management and revenue operations engine built for the Brightloop Software specification (Odoo Make-A-Ton Engineering Challenge).

It establishes an unbroken, transactionally safe commercial pipeline:
**User/Customer → Product & Plan → Quotation → Subscription → Recurring Invoice → Discount/Tax → Payment Allocation → Finance Dashboard**

---

## 1. Architecture & Technology Stack

- **Backend:** FastAPI, Python 3.12+, Pydantic v2, Pydantic-Settings
- **Database:** PostgreSQL 16+, SQLAlchemy 2.x (synchronous sessions), Alembic migrations, psycopg3
- **Security:** Argon2/bcrypt password hashing, JWT access tokens, role-based access control (Admin, Staff, Customer)
- **Infrastructure:** Docker Compose for local PostgreSQL containerization
- **Testing:** Pytest, HTTPX, Ruff linter/formatter
- **Frontend (Gate 5+):** React, TypeScript, Vite, Tailwind CSS, shadcn/ui (implemented strictly via Bolt.new after API contract freeze)

---

## 2. Quickstart Guide

### Prerequisites
- Python 3.12+
- `uv` (recommended) or standard `pip` + `python3-venv`
- Docker & Docker Compose (or local PostgreSQL 16 server)

### Step 1: Clone and Configure Environment
```bash
git clone <repo-url>
cd Subscription_Management_System

# Copy the example environment variables
cp .env.example .env
```

Review `.env` to verify credentials:
```env
APP_NAME=RecurFlow
APP_ENV=development
DATABASE_URL=postgresql+psycopg://recurflow:change_me@localhost:5432/recurflow
JWT_SECRET_KEY=c8f5e9d2a1b4763e0fa958d4c3b2e1f087a6543210fedcba0987654321abcdef
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Step 2: Start PostgreSQL Database

Using Docker Compose:
```bash
docker compose up -d
```

Verify PostgreSQL is running:
```bash
docker compose ps
```

*(Note for environments without Docker daemon: a local PostgreSQL 16 cluster listening on port 5432 with matching credentials satisfies connectivity).*

### Step 3: Install Backend Dependencies

Using `uv`:
```bash
cd backend
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

Using standard `pip`:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Step 4: Run Tests
```bash
cd backend
.venv/bin/pytest -v
```

### Step 5: Start FastAPI Application Server
```bash
cd backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Interactive OpenAPI Swagger UI is available at:
`http://localhost:8000/docs`

---

## 3. Health & Readiness Endpoints

- **Liveness Check:** `GET http://localhost:8000/health`
  ```json
  {
    "status": "healthy",
    "app": "RecurFlow",
    "environment": "development"
  }
  ```

- **Readiness Check (Live Database):** `GET http://localhost:8000/ready`
  ```json
  {
    "status": "ready",
    "database": "connected",
    "details": null
  }
  ```
  *(Returns HTTP 503 if PostgreSQL is disconnected or unreachable)*

---

## 4. Multi-Agent Operating Structure

RecurFlow is engineered under the Antigravity Multi-Agent operating contract (`AGENTS.md`):
- **Orchestrator:** Sequencing, task decomposition, gate enforcement, review.
- **Foundation Agent:** Project scaffold, Docker infrastructure, runtime environment, application lifecycle.
- **Data Architect Agent:** Relational schemas, Mermaid ERD, data dictionary, SQLAlchemy 2 models, Alembic migrations.
- **Backend Domain Agent:** Domain business services, request validation, API routers.
- **QA/Security Agent:** Test harnesses, permissions, financial edge cases, idempotency verification.
- **Frontend Contract Agent:** OpenAPI contract publishing and interface specifications.
- **Bolt Frontend Agent:** Isolated UI execution in Bolt.new strictly after Gate 5 API contract freeze.

### Active Gate Status
- [x] **Gate 1:** Project scaffold and health/readiness endpoints running.
- [ ] **Gate 2 (IN REVIEW):** Schema Specification, Mermaid ERD, and Data Dictionary submitted for architectural review.
- [ ] **Gate 3:** SQLAlchemy ORM models, Alembic migrations, and seed data.
- [ ] **Gate 4:** Core domain services, endpoints, and test suites.
- [ ] **Gate 5:** OpenAPI specification freeze and frontend contract export.
- [ ] **Gate 6:** Bolt.new frontend integration.
