# Scope, Roles & Priority Matrix

**Product:** RecurFlow — Subscription Operations & Revenue Management  
**Reference:** `agent.md` (Sections 1, 10, 11)

---

## 1. Role-Based Access Control (RBAC) Specification

| Role | Permissions & Operational Scope | Forbidden Actions |
|---|---|---|
| **Admin** | Full system control: staff provisioning, product catalogue, variant setup, plan rules, tax rates, global discounts, quotations, subscriptions, billing trigger, payment recording, financial analytics, audit log inspection. | Cannot bypass database uniqueness or transactional constraints. |
| **Staff** | Customer registration/updates, quotation drafting & issuance, subscription activation/pausing, manual payment recording, payment allocation, invoice review. | Cannot provision staff accounts; cannot alter system-wide tax or core billing configurations unless explicitly delegated. |
| **Customer** | Self-service portal access: view own customer profile, accept assigned valid quotations, view own active subscriptions, view own invoices (and download PDF), view own payment allocations. | Strict isolation: Zero access to other customer records, staff tooling, product cost prices, audit logs, or direct status mutations. |

---

## 2. Functional Modules Inventory

1. **Authentication & RBAC:** Secure password policy (>8 chars, uppercase, lowercase, special character), Argon2/bcrypt hashing, JWT bearer tokens, role checks.
2. **Customer Management:** Customer profiles, tax identifiers, billing/shipping addresses, user-linkage for portal login, soft-archive.
3. **Products & Variants:** Standard items, SKUs, sales and cost prices, variant price modifications.
4. **Subscription Plans:** Billing intervals (daily, weekly, monthly, yearly), minimum quantities, renewal policies.
5. **Tax Rules:** Tax rates, tax categories (inclusive vs. exclusive), active date ranges.
6. **Quotations & Templates:** Reusable quote templates, line items, automatic expiry, single-click transactional conversion to subscription.
7. **Subscription Lifecycle Engine:** State machine (Draft $\to$ Active $\leftrightarrow$ Paused $\to$ Closed), renewal anchors, next billing date progression.
8. **Discounts & Eligibility:** Fixed/percentage discount codes, usage counters, expiration dates, customer restrictions.
9. **Invoicing & Billing Engine:** Recurring billing runner, billing period calculation, idempotent generation, invoice line item snapshots.
10. **Payments & Multi-Invoice Allocations:** Manual payment capture (cash, bank transfer, cheque), partial allocations against invoice balances.
11. **Finance Dashboard & Analytics:** Dynamic aggregation of Active Subscriptions, Monthly Recurring Revenue (MRR), Overdue Receivables, Realized Cash Flow.
12. **Audit Trails:** Immutable event logs tracking actors, entity mutations, timestamps, and contextual metadata.

---

## 3. Scope Boundaries

### Explicitly In Scope
- Synchronous, modular monolith in FastAPI + SQLAlchemy 2.
- Local PostgreSQL 16+ via Docker Compose.
- Complete Pydantic v2 validation and OpenAPI contract generation.
- Idempotent recurring billing engine with period uniqueness.
- Exact `Decimal` / `NUMERIC(12,2)` arithmetic.
- Clean pytest suite covering calculations, isolation, and lifecycle idempotency.

### Explicitly Out of Scope
- Real external payment gateway integrations (Stripe, Adyen, Razorpay) — payments are recorded manually for this build.
- Credit card data collection or PCI-DSS storage.
- Complex multi-currency forex accounting (single currency `USD` for MVP).
- Distributed microservices, Celery/RabbitMQ clusters, or Kafka streaming.
- Usage-based metered billing or automated telephony/SMS notifications.
- Frontend implementation before Gate 5 freeze.
