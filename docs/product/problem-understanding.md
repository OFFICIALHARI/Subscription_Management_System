# Problem Understanding & System Context

**Product:** RecurFlow — Subscription Operations & Revenue Management  
**Scenario:** Brightloop Software (Odoo Make-A-Ton Engineering Challenge)  
**Standard Reference:** `agent.md`

---

## 1. Executive Summary & Problem Context

Brightloop Software is an expanding B2B digital services and software provider experiencing operational friction as its recurring revenue contracts multiply. Subscription lifecycles, contract amendments, automated recurring billing, discount compliance, tax calculations, and payment tracking are presently managed through disparate, fragmented channels. This fragmentation leads to:

1. **Revenue Leakage:** Missed renewal cycles, unbilled contract periods, and improper manual discounting without tracking usage limits.
2. **Billing Errors:** Rounding anomalies, improper tax computations across diverse jurisdictions, and floating-point errors in monetary totals.
3. **Double Billing & Non-Idempotent Invoicing:** Manual invoice creation running concurrently with automated schedules, resulting in duplicate invoices for the same customer and billing period.
4. **Data Isolation & Security Deficits:** Weak role-based access control, exposing customer billing records to unauthorized users or cross-customer leakage.
5. **Decoupled Dashboards:** Metric reporting calculated from stale or synthetic figures rather than reconcilable, immutable ledger events.

---

## 2. Core Objective

RecurFlow solves these operational vulnerabilities by delivering an end-to-end, transactionally consistent subscription and revenue management system. It establishes an unbroken chain of custody across the commercial lifecycle:

$$\text{User/Customer} \longrightarrow \text{Product \& Plan} \longrightarrow \text{Quotation} \longrightarrow \text{Subscription} \longrightarrow \text{Recurring Invoice} \longrightarrow \text{Discount / Tax} \longrightarrow \text{Payment Allocation} \longrightarrow \text{Finance Dashboard}$$

---

## 3. Guiding Architectural Principles

### 3.1 Single Source of Truth
The backend application services and relational PostgreSQL database constitute the authoritative source of truth. The frontend interface serves purely as a presentation and interaction layer. No business logic, authorization rules, or financial calculations reside in client components.

### 3.2 Exact Monetary Precision
Financial calculations must never use binary floating-point numbers (`float` or `double`). All monetary values are represented as arbitrary-precision decimals (`NUMERIC(12,2)` in PostgreSQL and `Decimal` in Python) to prevent rounding drift.

### 3.3 Transactional Consistency & Idempotency
- Invoice generation is strictly idempotent. A subscription combined with an exact billing period $(\text{subscription\_id}, \text{billing\_period\_start}, \text{billing\_period\_end})$ cannot produce duplicate invoices.
- State transitions (e.g., Quotation $\to$ Subscription, Payment $\to$ Allocation) execute inside isolated database transactions with row-level serialization where required.

### 3.4 Strict Historical Snapshots
Catalog items, variant price adjustments, and tax rules evolve over time. To ensure legal and financial reproducibility, quotation lines and invoice lines must store immutable snapshots of unit prices, item descriptions, and applied tax rates at the exact time of document creation.

### 3.5 Role-Based Security & Tenant Isolation
- **Admin:** System-wide governance, staff provisioning, master catalog, discount rules, audit inspection, and billing orchestration.
- **Staff:** Day-to-day operations across customers, quotes, subscriptions, and payment entries.
- **Customer:** Restricted strictly to self-service portal access; isolated completely from cross-customer records.
