# RecurFlow --- Antigravity Multi-Agent Build Instructions

**Project:** RecurFlow\
**Product:** Subscription Operations & Revenue Management\
**Build order:** Repository setup → schema specification → PostgreSQL →
backend → verified API contract → Bolt.new frontend\
**Primary stack:** React + TypeScript + Vite + Tailwind + shadcn/ui;
Python + FastAPI; PostgreSQL; SQLAlchemy 2; Alembic.

------------------------------------------------------------------------

## 0. Mission and non-negotiable rules

Build an original, working subscription-management application for the
Brightloop Software scenario in the supplied Odoo Make-A-Ton problem
statement.

The application must connect this business workflow end to end:

**User/customer → product and plan → quotation → subscription →
recurring invoice → discount/tax → payment allocation → finance
dashboard.**

This is a business workflow application, not a static dashboard or a
collection of disconnected CRUD pages.

### Non-negotiable engineering rules

1.  **Backend and database are the source of truth.** The frontend must
    consume real backend APIs. Never invent dashboard numbers or use
    hardcoded business records in the final integrated app.
2.  **Do not start frontend implementation in Bolt.new until the backend
    API contract is published and verified.** Before that point, only
    create wireframes or a visual direction if explicitly requested.
3.  Use PostgreSQL, not Firebase, Supabase, MongoDB Atlas or a
    browser-only database.
4.  Keep a modular monolith. Do not create microservices.
5.  Keep business rules in backend services, not React components.
6.  Use `Decimal`/PostgreSQL `NUMERIC` for money. Never use binary
    floating point for monetary calculations.
7.  Use database transactions for invoice generation, payment allocation
    and other multi-record financial operations.
8.  Make billing operations idempotent. The same subscription and
    billing period must never create duplicate invoices.
9.  Enforce authorization on the backend for every protected endpoint.
    Hiding a button in the frontend is not security.
10. Validate all request data with Pydantic. Return consistent error
    responses.
11. Use migrations for schema changes. Never rely on manually editing a
    live database schema.
12. Add tests for calculations, state transitions, permissions and
    duplicate-billing protection.
13. Do not copy another project's source code, branding, screenshots,
    copy or proprietary assets. Use public projects only to study
    workflows and engineering patterns. Check and comply with the
    licence before reusing any code.
14. Do not claim a feature works until it has been implemented and
    tested.
15. Keep the build small enough to finish. Prioritize a correct
    end-to-end workflow over optional enterprise features.

### Reference projects to study, not clone

Use these projects as product and engineering references:

-   EMP Billing --- breadth of billing workflow, quotes, invoices,
    payments, subscriptions, tax, customer portal and reporting:
    https://github.com/EmpCloud/emp-billing
-   Meteroid --- subscription/pricing concepts, catalog and revenue
    analytics: https://github.com/meteroid-oss/meteroid
-   Kill Bill --- subscription lifecycle, billing-period logic, REST API
    design and audit concepts: https://github.com/killbill/killbill and
    https://docs.killbill.io/latest/
-   InvoiceShelf --- invoice, estimate, customer and payment UX:
    https://github.com/InvoiceShelf/InvoiceShelf
-   SolidInvoice --- quotation and invoicing workflow:
    https://github.com/SolidInvoice/SolidInvoice

These are reference products with different stacks, scope and licences.
Do not import their architecture wholesale. Our selected stack below
takes precedence.

------------------------------------------------------------------------

## 1. Product scope

### Required roles

-   **Admin:** full access; manages staff, products, variants, plans,
    taxes, discounts, quotations, subscriptions, invoices, payments and
    reports.
-   **Staff:** day-to-day customer, quotation, subscription, invoice and
    payment operations; no staff-account creation or system-wide
    configuration unless explicitly granted.
-   **Customer:** can view and manage only their own profile,
    quotations, subscriptions, invoices and payment history.

Only Admin can create staff accounts. A customer must never access
another customer's records.

### Required modules

1.  Authentication, users and role-based access.
2.  Customers.
3.  Products and product variants.
4.  Subscription plans.
5.  Tax rules.
6.  Quotation templates and quotations.
7.  Subscriptions and lifecycle.
8.  Discounts and discount applications.
9.  Invoices and invoice lines.
10. Payments and payment allocations.
11. Dashboard and finance reports.
12. Audit events.

### Explicitly out of scope for the first hackathon build

-   Real payment gateway/card processing.
-   Usage-based metering.
-   Multi-currency accounting.
-   Multi-tenant SaaS infrastructure.
-   AI chatbot or AI-generated financial decisions.
-   Blockchain.
-   Microservices, Kubernetes and complex queue infrastructure.
-   Full accounting/general ledger.
-   SMS, WhatsApp and elaborate notification integrations.
-   Complex refunds/credit notes unless the required workflow is already
    stable.

Record payments manually for the demo. Do not collect or store card
numbers.

------------------------------------------------------------------------

## 2. Technology decisions

### Backend

-   Python 3.12+
-   FastAPI
-   Pydantic v2
-   SQLAlchemy 2.x (synchronous session is acceptable for this build;
    use one approach consistently)
-   PostgreSQL 16+
-   Alembic migrations
-   `psycopg` PostgreSQL driver
-   JWT access tokens
-   `pwdlib` or Argon2/bcrypt password hashing
-   Pytest
-   Ruff for lint/format
-   FastAPI OpenAPI/Swagger at `/docs`

### Frontend (to be built later in Bolt.new)

-   React
-   TypeScript
-   Vite
-   Tailwind CSS
-   shadcn/ui
-   React Router
-   TanStack Query for server state
-   React Hook Form + Zod for forms
-   Recharts for charts
-   Lucide icons

Use a single frontend app. Do not add Redux unless there is a
demonstrated need.

### Infrastructure and developer workflow

-   Docker Compose for local PostgreSQL.
-   `.env` for local secrets; commit `.env.example`, never `.env`.
-   GitHub repository with `main` branch.
-   Clear, small commits with meaningful messages.
-   OpenAPI JSON exported to `docs/openapi.json` after backend endpoints
    stabilize.

------------------------------------------------------------------------

## 3. Antigravity multi-agent operating model

Use one **Orchestrator / Lead Agent** and specialist agents. The
Orchestrator owns sequencing, integration, reviews and final decisions.

### Agent roles and ownership

  ----------------------------------------------------------------------------------
  Agent                   Responsibility          Owns
  ----------------------- ----------------------- ----------------------------------
  Orchestrator            Break work into tasks,  `AGENTS.md`, `docs/`, task
                          enforce gates, resolve  coordination
                          conflicts, review       
                          integration             

  Foundation Agent        Project scaffold,       root config, `backend/app/core/`,
                          Docker, env config,     Docker files
                          dependencies, app       
                          entrypoint              

  Data Architect Agent    ERD, schema             `docs/data/`,
                          specification,          `backend/app/models/`, migrations
                          SQLAlchemy models,      
                          constraints, Alembic    

  Backend Domain Agent    Pydantic schemas,       `backend/app/schemas/`,
                          services and API        `services/`, `api/`
                          routers                 

  QA/Security Agent       Tests, permissions,     `backend/tests/`, review reports
                          financial edge cases,   
                          security review         

  Frontend Contract Agent Reads OpenAPI and       `docs/frontend-api-contract.md`,
                          produces frontend       `docs/ui-page-map.md`
                          integration contract    
                          only                    

  Bolt Frontend Agent     Builds frontend only    separate `frontend/` project or
                          after API contract is   Bolt project
                          approved                
  ----------------------------------------------------------------------------------

**Avoid simultaneous edits to the same files.** The Orchestrator assigns
file ownership and integrates changes. Agents must not silently rewrite
another agent's work.

### Required agent workflow

For every task, the agent must report:

1.  What it inspected.
2.  Files it created or changed.
3.  Decisions and assumptions.
4.  Commands/tests run.
5.  Test results.
6.  Known gaps/blockers.
7.  Whether the work is ready for review.

Do not allow agents to mark work complete based only on generated code.
Run it.

### Phase gates

-   **Gate 1:** project scaffold runs locally.
-   **Gate 2:** schema/ERD approved before database models are
    finalized.
-   **Gate 3:** PostgreSQL starts and migrations apply cleanly.
-   **Gate 4:** backend tests pass and Swagger endpoints work.
-   **Gate 5:** OpenAPI and frontend contract are frozen for the first
    UI build.
-   **Gate 6:** Bolt frontend is connected to real endpoints and
    end-to-end flow passes.

Do not skip a gate to parallelize work.

------------------------------------------------------------------------

## 4. Phase 1 --- Repository and project setup

Create this structure:

``` text
recurflow/
├── AGENTS.md
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
├── docs/
│   ├── product/
│   │   ├── problem-understanding.md
│   │   ├── scope-and-priorities.md
│   │   └── workflow.md
│   ├── data/
│   │   ├── schema-specification.md
│   │   ├── erd.mmd
│   │   └── data-dictionary.md
│   ├── api/
│   │   ├── endpoint-inventory.md
│   │   └── openapi.json
│   ├── frontend-api-contract.md
│   └── ui-page-map.md
├── backend/
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   ├── security.py
│   │   │   ├── dependencies.py
│   │   │   └── errors.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── api/
│   │   │   ├── router.py
│   │   │   └── v1/
│   │   │       └── routers/
│   │   └── utils/
│   └── tests/
│       ├── conftest.py
│       ├── unit/
│       └── integration/
└── frontend/                 # Created by Bolt only after Gate 5
```

### Setup tasks

1.  Initialize Git and create the repository.
2.  Create Python virtual environment and backend package configuration.
3.  Add FastAPI health endpoint.
4.  Add Docker Compose PostgreSQL service with persistent volume and
    health check.
5.  Add `.env.example` with database URL, JWT secret, token expiry and
    app environment.
6.  Configure environment loading and fail fast if required secrets are
    missing.
7.  Add CORS configuration through environment variables. Do not use
    wildcard origins in production.
8.  Add structured logging and a consistent API error format.
9.  Add `GET /health` and `GET /ready`:
    -   `/health` checks process liveness.
    -   `/ready` checks database connectivity.
10. Document exact setup/run/test commands in README.

### Initial environment variables

``` env
APP_NAME=RecurFlow
APP_ENV=development
API_V1_PREFIX=/api/v1
DATABASE_URL=postgresql+psycopg://recurflow:change_me@localhost:5432/recurflow
JWT_SECRET_KEY=replace_with_a_long_random_secret
ACCESS_TOKEN_EXPIRE_MINUTES=30
CORS_ORIGINS=http://localhost:5173
```

Do not commit real credentials. Generate a strong random JWT secret for
local use.

### Setup acceptance criteria

-   `docker compose up -d` starts PostgreSQL.
-   Backend starts without import errors.
-   `GET /health` returns healthy.
-   `GET /ready` succeeds only when PostgreSQL is reachable.
-   README setup steps work on a clean machine.

------------------------------------------------------------------------

## 5. Phase 2 --- Create the schema specification as files BEFORE coding models

The Data Architect must first create and review:

1.  `docs/data/schema-specification.md`
2.  `docs/data/erd.mmd` (Mermaid ER diagram)
3.  `docs/data/data-dictionary.md`

Do not jump directly into ORM models. The schema specification is the
approved contract for database implementation.

### Proposed relational entities

#### Identity and customers

-   `users`: email, password hash, role, active flag, timestamps.
-   `customers`: business/customer profile, contact details, billing
    address, linked user where portal access exists.
-   `audit_logs`: actor, action, entity type/id, timestamp, safe
    metadata.

#### Product catalogue and plans

-   `products`: name, type, description, SKU, sales price, cost price,
    active state.
-   `product_variants`: product, variant name/value, price adjustment,
    active state.
-   `plans`: name, billing interval, interval count, minimum quantity,
    availability dates, lifecycle policy, active state.
-   `plan_items`: plan-to-product/variant relationship, quantity and
    pricing.
-   `tax_rates`: name, rate, tax type, jurisdiction/description, active
    dates, active state.

#### Quotations

-   `quotation_templates`: name, validity days, active state.
-   `quotations`: number, customer, template, issue/expiry dates,
    status, currency, subtotal, discount, tax, total, notes.
-   `quotation_lines`: quotation, product/variant/plan references,
    description snapshot, quantity, unit price, tax snapshot, line
    total.

#### Subscriptions

-   `subscriptions`: number, customer, plan, originating quotation,
    status, start date, end date, next billing date, billing anchor,
    payment terms, auto-close policy.
-   `subscription_lines`: subscription, product/variant, description and
    price snapshots, quantity, tax reference/snapshot.
-   `subscription_events` (or audit events): state changes, actor,
    reason and timestamp.

#### Discounts

-   `discounts`: name/code, fixed or percentage type, value, minimum
    amount/quantity, start/end dates, max uses, per-customer limit,
    active state.
-   `discount_applications`: discount, customer, subscription/invoice
    reference, applied amount, timestamp. Enforce eligibility and usage
    limits transactionally.

#### Billing and payments

-   `invoices`: invoice number, customer, subscription, billing period
    start/end, issue/due dates, status, currency, subtotal, discount
    total, tax total, total, amount paid, balance due.
-   `invoice_lines`: invoice, source subscription line, description
    snapshot, quantity, unit price, discount, tax rate/snapshot, line
    total.
-   `payments`: payment number/reference, method, amount, currency, paid
    date, note, status.
-   `payment_allocations`: payment, invoice, allocated amount. This
    supports partial payments and one payment allocated across multiple
    invoices if required.

### Required database constraints and indexes

The Data Architect must explicitly design and document:

-   Unique normalized user email.
-   Unique product SKU when SKU is provided.
-   Unique invoice number and subscription number.
-   Foreign keys with intentional delete behavior. Never cascade-delete
    financial history.
-   Non-negative quantities and monetary amounts where appropriate.
-   Valid date ranges (`end_date >= start_date`).
-   `NUMERIC(12,2)` or a documented currency-safe precision for amounts.
    Use `Decimal` in Python.
-   Billing interval enum/check constraint: daily, weekly, monthly,
    yearly.
-   Status constraints for quotations, subscriptions and invoices.
-   Indexes for customer, status, due date, next billing date,
    subscription, invoice number and payment references.
-   Unique invoice billing-period key for a subscription,
    e.g. `(subscription_id, billing_period_start, billing_period_end)`,
    where applicable.
-   Transactions and locking strategy for billing and payment
    allocation.
-   Restrict deletion of customers/products/plans with financial
    history; prefer archive/soft-delete.
-   Store snapshots of descriptions, prices and tax values on
    quote/invoice lines so historical documents do not change when
    catalogue data changes.

### Important modelling decisions

-   Do not assume every invoice is paid in full by one payment.
-   Keep invoice `amount_paid` and `balance_due` consistent with
    allocations; preferably calculate from allocations or update
    transactionally with reconciliation tests.
-   Distinguish invoice status from payment status. A partially paid
    invoice remains partially paid/open, not fully paid.
-   Distinguish subscription state from invoice state.
-   Define whether a quotation converts to a subscription directly or
    only after confirmation.
-   Define tax-inclusive versus tax-exclusive prices and document the
    selected rule.
-   Define discount stacking policy. For the MVP, allow at most one
    eligible discount per invoice unless the problem requires otherwise.
-   Store timestamps in UTC; display local dates in the UI.
-   Do not store card data.

### Schema acceptance criteria

-   ERD matches the table specification.
-   Every foreign key and important index is documented.
-   No circular or ambiguous relationships.
-   All lifecycle enums and money rules are documented.
-   Orchestrator and QA Agent approve the schema before ORM
    implementation.

------------------------------------------------------------------------

## 6. Phase 3 --- PostgreSQL and migrations

After schema approval:

1.  Implement SQLAlchemy 2 models matching the approved specification.
2.  Use a single declarative Base and consistent naming conventions for
    constraints.
3.  Configure database sessions and dependency injection.
4.  Initialize Alembic and point it to the model metadata.
5.  Generate the initial migration.
6.  Review the generated migration manually.
7.  Apply migration to an empty PostgreSQL database.
8.  Verify all tables, indexes, foreign keys and constraints.
9.  Create a seed script with realistic demo records:
    -   one Admin;
    -   one Staff;
    -   two Customers;
    -   products and variants;
    -   monthly and yearly plans;
    -   tax rule;
    -   one discount;
    -   quotation, active subscription, invoice and payment examples.
10. Make seed script safe to rerun (upsert or check-before-insert).

Do not put fake metrics directly into dashboard code. Demo data must be
inserted into PostgreSQL and retrieved through APIs.

### Database acceptance criteria

-   Fresh database migration succeeds.
-   Migration can be rerun safely through normal Alembic version
    tracking.
-   Seed script can run twice without duplicate demo data.
-   Foreign-key and uniqueness constraints work.
-   Database tests cover invalid relationships and duplicate invoice
    periods.

------------------------------------------------------------------------

## 7. Phase 4 --- Backend implementation

### Backend architecture

Use this request flow:

``` text
HTTP Request
  → FastAPI Router
  → Authentication / Role Authorization
  → Pydantic Request Validation
  → Domain Service (business rules)
  → SQLAlchemy Repository / Session
  → PostgreSQL
  → Pydantic Response Schema
  → JSON Response
```

Keep routers thin. Services own business logic. Do not put SQL or
financial calculations in route handlers.

### Suggested backend structure

``` text
backend/app/
├── main.py
├── core/
│   ├── config.py
│   ├── database.py
│   ├── security.py
│   ├── permissions.py
│   ├── dependencies.py
│   └── errors.py
├── models/
│   ├── user.py
│   ├── customer.py
│   ├── product.py
│   ├── plan.py
│   ├── quotation.py
│   ├── subscription.py
│   ├── discount.py
│   ├── tax.py
│   ├── invoice.py
│   ├── payment.py
│   └── audit_log.py
├── schemas/
│   ├── auth.py
│   ├── customer.py
│   ├── product.py
│   ├── plan.py
│   ├── quotation.py
│   ├── subscription.py
│   ├── discount.py
│   ├── invoice.py
│   ├── payment.py
│   └── dashboard.py
├── services/
│   ├── auth_service.py
│   ├── customer_service.py
│   ├── catalogue_service.py
│   ├── quotation_service.py
│   ├── subscription_service.py
│   ├── pricing_service.py
│   ├── tax_service.py
│   ├── discount_service.py
│   ├── billing_service.py
│   ├── invoice_service.py
│   ├── payment_service.py
│   ├── dashboard_service.py
│   └── audit_service.py
└── api/
    ├── router.py
    └── v1/routers/
        ├── auth.py
        ├── users.py
        ├── customers.py
        ├── products.py
        ├── plans.py
        ├── taxes.py
        ├── quotation_templates.py
        ├── quotations.py
        ├── subscriptions.py
        ├── discounts.py
        ├── invoices.py
        ├── payments.py
        ├── dashboard.py
        └── billing.py
```

### Authentication requirements

-   Register customer.
-   Login and issue access token.
-   Hash passwords securely.
-   Enforce unique email case-insensitively.
-   Password must be longer than 8 characters and include uppercase,
    lowercase and a special character, as required by the problem
    statement.
-   Only Admin creates staff.
-   Role checks on all protected routes.
-   Customer endpoints must scope data to the authenticated customer's
    own customer ID.
-   Forgot/reset password can be implemented with a development email
    adapter or a clearly documented demo token if email delivery is
    unavailable. Never pretend an email was sent when it was not.
-   Never return password hashes.

### Core business services

#### Pricing service

-   Calculate line totals using Decimal.
-   Apply variant price adjustments.
-   Apply quantity.
-   Apply eligible discount according to the documented policy.
-   Calculate taxes according to configured tax rules.
-   Return a transparent breakdown: subtotal, discount, taxable amount,
    tax and total.
-   Add tests for rounding and boundary values.

#### Quotation service

-   Create quotation from template.
-   Add product/plan lines.
-   Calculate expiry.
-   Track Draft → Quotation/Sent → Confirmed or Expired/Cancelled as
    designed.
-   Convert a confirmed quotation into a subscription in a transaction.
-   Prevent duplicate conversion.

#### Subscription service

-   Create subscription from confirmed quotation or authorized
    admin/staff workflow.
-   Track Draft → Quotation → Confirmed → Active → Closed, with Paused
    where applicable.
-   Support pause, resume, renew and early close.
-   Calculate next billing date for daily, weekly, monthly and yearly
    plans.
-   Handle month-end dates explicitly (e.g. Jan 31 to Feb end) and test
    leap years.
-   Record state transitions in audit history.

#### Billing service --- highest-risk/highest-value module

-   Identify subscriptions due for billing.
-   Determine exact billing period.
-   Generate invoice lines from subscription line snapshots.
-   Apply valid discount and tax rules.
-   Use a database transaction.
-   Lock or otherwise serialize processing for the subscription.
-   Enforce unique subscription + billing period.
-   Make repeated execution safe (idempotent).
-   Advance next billing date only after successful invoice creation.
-   Provide an admin-triggered billing-cycle endpoint for demo and a
    command/scheduled invocation for routine operation.
-   Do not charge a payment gateway in this MVP.

#### Payment service

-   Record manual payment with method, amount, date, reference and note.
-   Allocate payment to one or more invoices.
-   Reject allocation greater than available payment amount or invoice
    balance.
-   Support partial payments.
-   Update invoice balance/status transactionally.
-   Record audit event.
-   Do not expose or store card details.

#### Dashboard service

Calculate from database records, not hardcoded values: - Active
subscriptions. - Monthly recurring revenue (normalize active recurring
plan values to monthly equivalent). - Invoiced amount in selected
period. - Payments received in selected period. - Outstanding
receivables. - Overdue invoice count and amount. - Upcoming renewals. -
Revenue trend by month.

Document the exact meaning of each metric. Do not label invoice totals
as cash received. Do not count cancelled/closed subscriptions as active
MRR.

------------------------------------------------------------------------

## 8. Phase 5 --- API endpoints to implement

Use base path `/api/v1`. Use consistent pagination, filtering, response
schemas and error responses.

The following is the initial endpoint contract. The backend team may
refine details, but must update `docs/api/endpoint-inventory.md` and the
OpenAPI document before frontend work begins.

### Common API conventions

-   JSON request and response bodies.
-   Bearer JWT authentication.
-   List endpoints support `page`, `page_size`, `search`, and relevant
    filters.
-   Use `page_size` maximum of 100.
-   Return `404` for missing resources, `401` for unauthenticated, `403`
    for forbidden, `409` for state/duplicate conflicts, `422` for
    validation errors.
-   Use consistent response shape and documented pagination metadata.
-   Use ISO-8601 dates/timestamps.
-   Return monetary values as decimal strings or a documented JSON
    numeric representation; frontend must not perform authoritative
    financial calculations.
-   Use explicit action endpoints for state transitions rather than
    allowing arbitrary status edits.

### Health and authentication

  Method   Endpoint                  Purpose                 Access
  -------- ------------------------- ----------------------- ---------------
  GET      `/health`                 Process health          Public
  GET      `/ready`                  DB readiness            Public
  POST     `/auth/register`          Customer registration   Public
  POST     `/auth/login`             Login                   Public
  GET      `/auth/me`                Current user and role   Authenticated
  POST     `/auth/forgot-password`   Start password reset    Public
  POST     `/auth/reset-password`    Reset password          Public
  POST     `/auth/change-password`   Change own password     Authenticated
  POST     `/users/staff`            Create staff user       Admin
  GET      `/users`                  List users              Admin

### Customers

  Method   Endpoint                          Purpose
  -------- --------------------------------- ------------------------
  GET      `/customers`                      Search/list customers
  POST     `/customers`                      Create customer
  GET      `/customers/{id}`                 Customer detail
  PATCH    `/customers/{id}`                 Update customer
  POST     `/customers/{id}/archive`         Archive customer
  GET      `/customers/{id}/subscriptions`   Customer subscriptions
  GET      `/customers/{id}/invoices`        Customer invoices
  GET      `/customers/{id}/payments`        Customer payments

Admin/Staff may access business customers according to role. Customer
role may only access its own records through `/portal/...` endpoints or
a strictly enforced ownership check.

### Products, variants, plans and taxes

  Method      Endpoint                    Purpose
  ----------- --------------------------- -----------------------
  GET/POST    `/products`                 List/create products
  GET/PATCH   `/products/{id}`            Read/update product
  POST        `/products/{id}/archive`    Archive product
  GET/POST    `/products/{id}/variants`   List/create variants
  PATCH       `/variants/{id}`            Update variant
  GET/POST    `/plans`                    List/create plans
  GET/PATCH   `/plans/{id}`               Read/update plan
  POST        `/plans/{id}/archive`       Archive plan
  GET/POST    `/taxes`                    List/create tax rules
  PATCH       `/taxes/{id}`               Update tax rule

### Quotation templates and quotations

  --------------------------------------------------------------------------------------------
  Method                  Endpoint                                     Purpose
  ----------------------- -------------------------------------------- -----------------------
  GET/POST                `/quotation-templates`                       List/create templates

  GET/PATCH               `/quotation-templates/{id}`                  Read/update template

  GET/POST                `/quotations`                                List/create quotations

  GET/PATCH               `/quotations/{id}`                           Read/update draft
                                                                       quotation

  POST                    `/quotations/{id}/send`                      Mark/send quotation

  POST                    `/quotations/{id}/confirm`                   Confirm accepted
                                                                       quotation

  POST                    `/quotations/{id}/cancel`                    Cancel quotation

  POST                    `/quotations/{id}/convert-to-subscription`   Convert confirmed quote

  GET                     `/quotations/{id}/pdf`                       Download/print PDF if
                                                                       implemented
  --------------------------------------------------------------------------------------------

### Subscriptions

  Method     Endpoint                         Purpose
  ---------- -------------------------------- -----------------------------
  GET/POST   `/subscriptions`                 List/create subscriptions
  GET        `/subscriptions/{id}`            Subscription detail
  PATCH      `/subscriptions/{id}`            Edit permitted draft fields
  POST       `/subscriptions/{id}/activate`   Activate
  POST       `/subscriptions/{id}/pause`      Pause
  POST       `/subscriptions/{id}/resume`     Resume
  POST       `/subscriptions/{id}/renew`      Renew
  POST       `/subscriptions/{id}/close`      Close
  GET        `/subscriptions/{id}/invoices`   Billing history
  GET        `/subscriptions/{id}/events`     Lifecycle timeline

### Discounts

  Method      Endpoint                    Purpose
  ----------- --------------------------- -------------------------------
  GET/POST    `/discounts`                List/create discount rules
  GET/PATCH   `/discounts/{id}`           Read/update discount
  POST        `/discounts/validate`       Validate discount eligibility
  POST        `/discounts/{id}/archive`   Archive discount

### Billing and invoices

  Method     Endpoint                     Purpose
  ---------- ---------------------------- ---------------------------------------
  POST       `/billing/run-cycle`         Run due billing cycle (Admin)
  GET        `/billing/preview`           Preview subscriptions due for billing
  GET        `/billing/runs`              Billing execution history
  GET/POST   `/invoices`                  List/create permitted invoices
  GET        `/invoices/{id}`             Invoice detail
  POST       `/invoices/{id}/confirm`     Confirm invoice
  POST       `/invoices/{id}/cancel`      Cancel eligible invoice
  POST       `/invoices/{id}/mark-sent`   Mark invoice as sent
  GET        `/invoices/{id}/pdf`         Download/print invoice
  GET        `/invoices/overdue`          Overdue invoice list

Manual invoice creation must not bypass the subscription-generated
invoice rules. Clearly separate manual and recurring invoices if manual
creation is allowed.

### Payments

  Method     Endpoint                       Purpose
  ---------- ------------------------------ ---------------------------------
  GET/POST   `/payments`                    List/record payment
  GET        `/payments/{id}`               Payment detail
  POST       `/payments/{id}/allocations`   Allocate payment to invoice
  GET        `/invoices/{id}/payments`      Payments allocated to invoice
  GET        `/payments/{id}/receipt`       Receipt/download if implemented

### Dashboard, reports and audit

  Method   Endpoint                         Purpose
  -------- -------------------------------- --------------------------------
  GET      `/dashboard/summary`             KPI totals
  GET      `/dashboard/revenue-trend`       Monthly revenue series
  GET      `/dashboard/overdue`             Overdue summary/list
  GET      `/dashboard/upcoming-renewals`   Upcoming renewal list
  GET      `/reports/receivables`           Outstanding and aging report
  GET      `/audit-logs`                    Filterable audit trail (Admin)

### Customer portal

  Method   Endpoint                           Purpose
  -------- ---------------------------------- ---------------------------------
  GET      `/portal/profile`                  Own profile
  PATCH    `/portal/profile`                  Update permitted profile fields
  GET      `/portal/quotations`               Own quotations
  POST     `/portal/quotations/{id}/accept`   Accept own valid quotation
  GET      `/portal/subscriptions`            Own subscriptions
  GET      `/portal/invoices`                 Own invoices
  GET      `/portal/payments`                 Own payment history

Only implement portal actions that can be securely enforced and tested.
Customers cannot activate arbitrary subscriptions, change prices or mark
invoices paid.

------------------------------------------------------------------------

## 9. Phase 6 --- Backend testing and API freeze

Before giving anything to Bolt.new, complete this checklist.

### Functional tests

-   Customer registration and duplicate email rejection.
-   Password policy.
-   Login and role authorization.
-   Customer data isolation.
-   Product and variant price calculation.
-   Plan billing intervals.
-   Quotation creation and expiry.
-   Confirmed quotation conversion.
-   Subscription state transitions.
-   Monthly billing and month-end date handling.
-   Billing cycle idempotency.
-   Duplicate invoice prevention.
-   Discount start/end and usage limits.
-   Tax calculation and rounding.
-   Partial payment allocation.
-   Overpayment rejection.
-   Invoice paid/partially paid/overdue status.
-   Dashboard metrics reconcile to underlying records.

### Security tests

-   Customer cannot access another customer's ID.
-   Staff cannot create staff accounts.
-   Unauthenticated users cannot access protected endpoints.
-   Invalid status transitions are rejected.
-   Secrets and password hashes never appear in responses or logs.
-   SQL is parameterized through ORM; do not interpolate user input into
    SQL.

### API freeze deliverables

Generate and commit:

1.  `docs/api/openapi.json`
2.  `docs/api/endpoint-inventory.md`
3.  `docs/frontend-api-contract.md`
4.  `docs/ui-page-map.md`
5.  A small set of sanitized example request/response JSON files under
    `docs/api/examples/`.

The OpenAPI file must come from the running FastAPI application, not be
manually invented.

Example export command:

``` bash
python -c "import json; from app.main import app; json.dump(app.openapi(), open('docs/api/openapi.json','w'), indent=2)"
```

Confirm the exported OpenAPI contains the actual paths, schemas,
authentication scheme and response models.

------------------------------------------------------------------------

## 10. Phase 7 --- Bolt.new frontend instructions (STRICTLY AFTER API FREEZE)

Bolt.new is responsible for frontend implementation only.

It must not: - Create a second backend. - Create or modify database
schemas. - Add Supabase/Firebase. - Invent API endpoints. - Use
hardcoded business data as final data. - Reimplement authoritative
pricing, tax, discount, MRR or invoice calculations. - Bypass backend
permissions. - Change backend response formats to suit the UI without an
agreed contract update.

### Inputs to give Bolt.new

Provide these exact files:

-   `docs/frontend-api-contract.md`
-   `docs/api/openapi.json`
-   `docs/ui-page-map.md`
-   `docs/product/scope-and-priorities.md`
-   A small set of sanitized API examples.

### Frontend page map

#### Shared application shell

-   Responsive sidebar.
-   Top navigation with page title, search, notifications placeholder
    and user menu.
-   Breadcrumbs.
-   Role-aware navigation.
-   Loading, error and empty states.
-   Responsive desktop/tablet/mobile layouts.

#### Admin/Staff pages

1.  Login.
2.  Dashboard.
3.  Customers list and customer detail.
4.  Products list, create/edit and variants.
5.  Plans list and create/edit.
6.  Quotations list, create/edit and detail.
7.  Quotation templates.
8.  Subscriptions list, detail and lifecycle actions.
9.  Billing run preview and execution history.
10. Invoices list and invoice detail.
11. Payments list and record payment flow.
12. Discounts list and create/edit.
13. Tax settings.
14. Reports.
15. Audit log.
16. Staff/user management (Admin only).

#### Customer portal pages

1.  Customer home.
2.  My profile.
3.  My quotations and accept action.
4.  My subscriptions.
5.  My invoices and PDF links.
6.  My payment history.

### UI direction

Create an original professional finance SaaS interface:

-   Product name: RecurFlow.
-   Visual tone: precise, calm, trustworthy and modern.
-   Use a restrained deep-violet or indigo accent with neutral surfaces.
-   Strong typography hierarchy and consistent spacing.
-   Clear status badges for Draft, Confirmed, Active, Paused, Closed,
    Paid, Partially Paid, Overdue.
-   Tables should support search, filters, sorting and pagination where
    endpoints support them.
-   Use charts only for real API data.
-   Use skeletons while loading.
-   Use helpful empty states and actionable error messages.
-   Forms must have field-level validation and server error display.
-   Confirm destructive or financial actions with confirmation dialogs.
-   Do not overuse gradients, glassmorphism or decorative animations.
-   Make financial values, dates and statuses easy to scan.

### Frontend integration rules

-   Use one central API client with base URL from environment.
-   Add bearer token handling and a consistent unauthorized-session
    flow.
-   Use TanStack Query for fetching, caching and invalidation.
-   Use generated TypeScript types from OpenAPI where practical.
-   Keep API calls in service modules, not scattered across components.
-   Use backend response values for all business totals.
-   Use query parameters that match backend pagination and filtering.
-   After mutations, invalidate/refetch affected queries.
-   Show permission-aware actions, but rely on backend authorization.
-   Add frontend tests for critical forms and workflows.

### Required frontend demo path

The following must work against the real backend:

1.  Admin logs in.
2.  Admin creates a product and a monthly plan.
3.  Staff creates a customer and quotation.
4.  Quotation is confirmed and converted to a subscription.
5.  Admin previews and runs the billing cycle.
6.  Invoice appears with correct line items, discount and tax.
7.  Staff records a payment.
8.  Invoice status and balance update.
9.  Dashboard reflects updated subscription, invoice and payment data.
10. Customer logs in and sees only their own subscription and invoice.

------------------------------------------------------------------------

## 11. End-to-end acceptance criteria

The build is not complete until all of these are true:

-   [ ] Clean setup works using documented commands.
-   [ ] PostgreSQL starts through Docker Compose.
-   [ ] Alembic migration builds a fresh database.
-   [ ] Seed script produces usable demo data.
-   [ ] Backend starts and Swagger is accessible.
-   [ ] All implemented endpoints have request/response schemas.
-   [ ] RBAC and customer data isolation are tested.
-   [ ] Quote-to-subscription conversion works.
-   [ ] Billing cycle generates one invoice per due billing period.
-   [ ] Re-running billing does not duplicate invoices.
-   [ ] Discounts and taxes calculate correctly.
-   [ ] Partial payment allocation works.
-   [ ] Dashboard metrics reconcile with database records.
-   [ ] OpenAPI contract is exported and committed.
-   [ ] Bolt frontend uses only the documented backend APIs.
-   [ ] Main demo path works from login to dashboard.
-   [ ] No secrets, fake metrics or copied branding are present.

------------------------------------------------------------------------

## 12. First instruction to Antigravity

**Start with Phase 1 only. Do not build the frontend. Do not implement
all modules at once.**

Use the Orchestrator to:

1.  Inspect the current workspace and identify existing files before
    changing anything.
2.  Create the root `AGENTS.md` using this document as the project's
    operating contract.
3.  Create the repository skeleton and backend scaffold.
4.  Configure Docker Compose PostgreSQL and environment handling.
5.  Implement `/health` and `/ready`.
6.  Run the project and prove the setup works.
7.  Then assign the Data Architect to create the schema specification,
    Mermaid ERD and data dictionary as files.
8.  Stop for schema review before creating ORM models or migrations.

**Expected first milestone:** a clean repository, a running FastAPI
service, a healthy PostgreSQL container, and three reviewed
schema-design files. No frontend yet.

After that milestone, proceed to database models and migrations, then
backend domain services and endpoints, then tests and OpenAPI freeze,
and only then Bolt.new.

------------------------------------------------------------------------

## 13. Product and source alignment

This build brief is based on the supplied Odoo problem statement:

-   Registration, unique email, password rules and three roles.
-   Products, variants and price adjustments.
-   Plans with daily/weekly/monthly/yearly intervals and lifecycle
    rules.
-   Quotation templates and quotation-to-subscription workflow.
-   Subscription states.
-   Automatic invoice generation, taxes and duplicate prevention.
-   Fixed/percentage discounts and usage limits.
-   Payment recording and invoice matching.
-   Finance dashboard and sub-two-second page-response expectation.

The supplied Technical Expectations add relational database design,
backend APIs, dynamic data, validation, Git contributions, modularity,
security, performance and maintainability.

The supplied Solo Developers Playbook recommends a fast, focused
eight-hour execution sequence, frequent commits and a short
workflow-focused demo. Its SQLite recommendation is intentionally
superseded here by PostgreSQL to align with the Technical Expectations'
preference for MySQL/PostgreSQL.

External reference research informs feature patterns, not the
implementation stack:

-   EMP Billing documents a broad quotes-to-invoices-to-payments
    workflow, customer portal, recurring billing, reporting and a
    modular API/service structure:
    https://github.com/EmpCloud/emp-billing
-   Meteroid documents subscription, pricing, invoicing and revenue
    analytics concepts: https://github.com/meteroid-oss/meteroid
-   Kill Bill documents subscription/catalog/invoice/payment APIs and
    billing lifecycle concepts: https://docs.killbill.io/latest/
-   InvoiceShelf provides a reference for invoices, estimates, payments
    and customer-facing workflows:
    https://github.com/InvoiceShelf/InvoiceShelf

**Final principle:** build a smaller, coherent, original product with
correct business logic and a verified API contract. Do not attempt to
reproduce the entire feature set of mature billing platforms in an
eight-hour hackathon.
