# RecurFlow — Dedicated Database Environment Specification

**Product:** RecurFlow — Subscription Operations & Revenue Management  
**Environment Role:** Authoritative Permanent Development Database  
**Engine:** PostgreSQL 17  
**Containerization:** Docker Compose  

---

## 1. Database Identity & Specification

| Property | Value | Description |
|---|---|---|
| **Project** | RecurFlow | Dedicated project container |
| **Docker Service Name** | `db` | Service identifier in `docker-compose.yml` |
| **Container Name** | `recurflow-db` | Standalone Docker container name |
| **PostgreSQL Image** | `postgres:17` | Official PostgreSQL 17 Debian/Alpine release |
| **Database Name** | `recurflow` | Application primary database |
| **Database Username** | `recurflow` | Application primary user |
| **Host Port** | `5434` | Explicitly isolated host port |
| **Container Port** | `5432` | Standard internal PostgreSQL port |
| **Persistent Volume** | `recurflow_postgres_data` | Named Docker volume bound to `/var/lib/postgresql/data` |
| **Restart Policy** | `unless-stopped` | Persists and automatically restarts across reboots |
| **Connection Host** | `localhost` / `127.0.0.1` | Local development host |

---

## 2. Host Connection Configuration

The backend application and developer tooling connect to RecurFlow via:

```text
postgresql+psycopg://recurflow:<PASSWORD>@localhost:5434/recurflow
```

- **Driver:** `psycopg` (v3) with SQLAlchemy 2.x
- **Password Management:** Stored securely in the local `.env` file (`POSTGRES_PASSWORD`), which is excluded from Git tracking via `.gitignore`.
- **Public Template:** `.env.example` provides the sanitized template with placeholder values.

---

## 3. Operational Commands

### 3.1 Starting the Database
Start the dedicated database container in detached mode:
```bash
docker compose up -d db
```
*(If operating in a shell requiring Docker group activation: `sg docker -c "docker compose up -d db"`)*

### 3.2 Stopping the Database Safely
Stop the database process without destroying the persistent storage volume:
```bash
docker compose stop db
```
*or*
```bash
docker compose down
```

> [!CAUTION]
> **NEVER** run destructive Docker volume commands:
> - Do NOT run `docker compose down -v`
> - Do NOT run `docker volume rm recurflow_postgres_data`
> - Do NOT run `docker volume prune` or `docker system prune -a --volumes`
> These commands will irreversibly destroy all local development data, migration state, and customer records.

### 3.3 Status & Health Inspection
Check container status and health check state:
```bash
docker ps --filter name=recurflow-db
```
Inspect health check logs directly:
```bash
docker inspect --format '{{json .State.Health}}' recurflow-db
```
Execute `pg_isready` inside the container:
```bash
docker exec -it recurflow-db pg_isready -U recurflow -d recurflow
```

### 3.4 Interactive Shell & Querying
Connect to `psql` within the running container:
```bash
docker exec -it recurflow-db psql -U recurflow -d recurflow
```

---

## 4. Backup & Restore Procedures

### 4.1 Logical Database Backup (Dump)
Export a compressed snapshot of the entire `recurflow` schema and data:
```bash
docker exec -t recurflow-db pg_dump -U recurflow -d recurflow -F c -b -v -f /tmp/recurflow_backup.dump
docker cp recurflow-db:/tmp/recurflow_backup.dump ./recurflow_backup_$(date +%Y%m%d_%H%M%S).dump
```

### 4.2 Restoring from Backup
Restore into a clean `recurflow` database:
```bash
docker cp ./recurflow_backup_<timestamp>.dump recurflow-db:/tmp/restore.dump
docker exec -t recurflow-db pg_restore -U recurflow -d recurflow -v --clean --if-exists /tmp/restore.dump
```

---

## 5. Backend Application Integration

The FastAPI backend consumes this configuration through `app.core.config.Settings`:
1. `Settings` loads `DATABASE_URL` from the local `.env` file.
2. Connection pooling is managed in `app.core.database.engine` with `pool_size=10`, `max_overflow=20`, and `pool_pre_ping=True`.
3. The `/ready` endpoint continuously validates live database readiness by executing `SELECT 1` via `check_db_connection()`.
4. Alembic migrations (`alembic.ini` and `alembic/env.py`) dynamically read `settings.DATABASE_URL` to target this database.

---

## 6. Coexistence Invariants

- **Isolated Port (5434):** The host port is intentionally mapped to `5434` to prevent collisions with any existing local PostgreSQL service running on `5432` or unrelated test containers (such as `postgres-dev` on `5433`).
- **Single Source of Truth:** `recurflow-db` is the sole, authoritative PostgreSQL database for the lifetime of the RecurFlow project. No competing database engines or instances shall be created for this service.
