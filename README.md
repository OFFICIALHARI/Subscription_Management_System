# Subscription Management System — RecurFlow

**Hackathon Challenge:** Odoo Make-A-Ton (Brightloop Software Scenario)  
**Product:** RecurFlow — Subscription Operations & Revenue Management  

---

## Repository Structure

This repository is structured as a multi-tier container for the RecurFlow enterprise application:

- **Root Directory (`Subscription_Management_System/`):** Git repository container, safety ignore policies (`.gitignore`), and repository documentation.
- **Application Root (`RecurFlow/`):** All application code, backend services, frontend application, database configuration, documentation, tests, and scripts reside here.

```text
Subscription_Management_System/
├── .git/
├── .gitignore
├── README.md                      # Repository root overview
└── RecurFlow/                     # CANONICAL APPLICATION ROOT
    ├── README.md                  # Comprehensive application guide
    ├── AGENTS.md                  # Multi-agent operating model & gates
    ├── agent.md                   # Master engineering specification
    ├── docker-compose.yml         # Canonical PostgreSQL 17 compose definition
    ├── .env.example               # Sanitized environment template
    ├── .env                       # Local secrets (git-ignored)
    ├── backend/                   # FastAPI + SQLAlchemy 2 + Alembic backend
    ├── frontend/                  # React + TypeScript + Vite + Tailwind frontend
    └── docs/                      # Architecture, API contract, and demo scripts
```

## Quick Start

All commands must be executed from the `RecurFlow/` application directory:

```bash
cd RecurFlow

# 1. Start dedicated PostgreSQL 17 container (Port 5434)
docker compose up -d

# 2. Refer to RecurFlow/README.md for backend and frontend execution instructions
```

For full setup, architecture documentation, API specifications, and demonstration scripts, see [**`RecurFlow/README.md`**](file:///home/officialhari/Downloads/DRIVE%20H/odoo%20hacks/Subscription_Management_System/RecurFlow/README.md).
