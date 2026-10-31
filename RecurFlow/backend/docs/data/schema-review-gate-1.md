# RecurFlow — Phase 2 Gate 1: Initial Schema Review

**System:** RecurFlow (Subscription Operations & Revenue Management)  
**Review Type:** Architecture, Data Integrity & Security Review (Gate 1)  
**Reviewer:** Data Architect & Systems Review Lead  
**Specification Under Review:** `schema-specification.md`, `erd.mmd`, `data-dictionary.md`  
**Review Date:** October 31, 2026  
**Status:** **PASS WITH REQUIRED REFINEMENTS**

---

## 1. Executive Summary

This Gate 1 review conducts a rigorous, multi-point evaluation of the RecurFlow database architecture against the Brightloop Software engineering specifications, the Odoo Make-A-Ton hackathon problem statement, and Antigravity operating rules.

The initial schema design established solid relational fundamentals:
- PostgreSQL native types with `NUMERIC(12, 2)` monetary precision.
- Elimination of floating-point arithmetic across all financial entities.
- Snapshot immutability on quotation and invoice line items.
- Composite uniqueness for recurring billing idempotency `UNIQUE(subscription_id, billing_period_start, billing_period_end)`.
- Dedicated payment capture and multi-invoice allocation mechanisms.

However, the Gate 1 review identified **5 critical/medium refinement requirements** necessary to guarantee enterprise financial robustness, lifecycle traceability, and audit compliance prior to Gate 2 sign-off:
1. **Subscription Renewal Lineage:** Need an explicit `renewed_from_subscription_id` self-referential foreign key to trace contract extensions.
2. **Subscription Lifecycle State Machine:** Missing `QUOTATION` and `CONFIRMED` statuses in the subscription check constraint to align with the prompt's `Draft -> Quotation -> Confirmed -> Active -> Closed` sequence.
3. **Database-Level Over-Allocation Prevention:** The `payments` table requires an `amount_allocated` tracking column with a check constraint `CHECK (amount_allocated <= amount)` to block payment over-allocation at the database engine level.
4. **Subscription Pause Metadata:** Need explicit temporal columns (`paused_at`, `resumed_at`) to ensure deterministic date arithmetic during billing pause and resumption.
5. **Line Item Lineage:** Link `subscription_lines` back to `quotation_lines.id` for end-to-end pricing and specification traceability.

---

## 2. Comprehensive Requirements Checklist (25 Points)

| # | Review Criteria | Evaluation | Finding / Action Required |
|---|---|---|---|
| 1 | **All Required Entities Present** | PASS | 20 tables covering auth, customer, catalogue, plans, quotes, subscriptions, discounts, taxes, invoices, payments, allocations, audit. |
| 2 | **Relationships Correct** | PASS | Cardinalities accurately modeled with explicit foreign keys. |
| 3 | **Foreign Keys Explicit** | PASS | Every relationship specifies explicit target table and column. |
| 4 | **Primary Keys Consistent** | PASS | Uniform `BIGINT GENERATED ALWAYS AS IDENTITY` across all entities. |
| 5 | **Required Unique Constraints Present** | PASS | Unique user email, product SKU, plan code, quotation number, subscription number, invoice number, payment reference. |
| 6 | **Indexes for Likely Query Patterns** | PASS | Indexes on foreign keys, status filters, expiration dates, issue dates, and customer lookups. |
| 7 | **Money Fields Decimal-Safe** | PASS | Strict `NUMERIC(12, 2)` utilized across all price, total, tax, discount, and balance columns. No floats. |
| 8 | **Historical Snapshots Preserved** | PASS | Quotation and Invoice lines capture immutable copies of description, unit price, and tax rate. |
| 9 | **All 4 Billing Frequencies Supported**| PASS | Daily, Weekly, Monthly, Yearly intervals supported with `interval_count` scaling. |
| 10| **Product Variants & Adjustments** | PASS | Configurable variant options with `price_adjustment NUMERIC(12, 2)`. Accommodates the +560 adjustment example cleanly. |
| 11| **Quote-to-Subscription Tracing** | REVISE | `originating_quotation_id` exists; add `quotation_line_id` on `subscription_lines` for line-level lineage. |
| 12| **Subscription Status Validation** | REVISE | Expand status check to include `DRAFT`, `QUOTATION`, `CONFIRMED`, `ACTIVE`, `PAUSED`, `CLOSED`. |
| 13| **Pause, Resume, Close, Renew Traceable**| REVISE | Add `renewed_from_subscription_id`, `paused_at`, and `resumed_at` to table definition. |
| 14| **Duplicate Billing Prevented at DB Level**| PASS | Enforced via `UNIQUE (subscription_id, billing_period_start, billing_period_end)`. |
| 15| **Partial & Multi-Invoice Allocations** | PASS | Cleanly modeled through dedicated `payment_allocations` associative entity. |
| 16| **Over-Allocation Blocked at DB Level** | REVISE | Add `amount_allocated` and `CHECK (amount_allocated <= amount)` on `payments`. |
| 17| **Invoice Line Reconciliation** | PASS | Line totals reconcile to invoice subtotal, tax, and discount totals. |
| 18| **Dynamic Finance Dashboard Metrics** | PASS | Schema supports pure transactional aggregation of MRR, billed, collected, receivables, and overdue counts. |
| 19| **Safe Deletion & Retention Rules** | PASS | `ON DELETE RESTRICT` on master records with financial history; soft archiving via `is_active`. |
| 20| **Timestamp Conventions Consistent** | PASS | All temporal columns use `TIMESTAMP WITH TIME ZONE` strictly stored in UTC. |
| 21| **Nullable Fields Justified** | PASS | Optional tax ID, phone, discounts, and template references are correctly nullable. |
| 22| **Enum/Status Values Documented** | PASS | Check constraints enforce allowed status states for users, quotes, subs, invoices, and payments. |
| 23| **Cascade-Delete Rules Safe** | PASS | Cascade only permitted for non-financial children (e.g. quote lines, plan items); RESTRICT for invoices/payments. |
| 24| **Avoids Unnecessary Duplication** | PASS | Normalized catalogue and pricing rules without unneeded redundant columns. |
| 25| **SQLAlchemy 2 & PG17 Implementable** | PASS | Cleanly maps to standard DeclarativeBase and Core constraints in SQLAlchemy 2. |

---

## 3. Mandatory Edge-Case Analysis

### 3.1 Monthly Billing at Month-End (e.g., January 31 $\to$ February $\to$ March)
- **Problem Statement:** Subscriptions anchored on the 29th, 30th, or 31st encounter months with fewer days (e.g., February with 28/29 days, April with 30 days). Naive addition of 1 month leads to date overflow or unintended date drift (e.g., Feb 28 $\to$ March 28 instead of March 31).
- **RecurFlow Architectural Solution:**
  1. `subscriptions.billing_anchor_day INTEGER NOT NULL CHECK (billing_anchor_day BETWEEN 1 AND 31)` permanently preserves the customer's intended billing day.
  2. The next billing date calculation algorithm evaluates:
     $$\text{Target Month} = \text{current\_billing\_month} + 1$$
     $$\text{Max Days in Target Month} = \text{days\_in\_month}(\text{Target Year}, \text{Target Month})$$
     $$\text{next\_billing\_date} = \text{DATE}(\text{Target Year}, \text{Target Month}, \min(\text{billing\_anchor\_day}, \text{Max Days}))$$
  3. Example: Subscription created Jan 31 with `billing_anchor_day = 31`:
     - Feb billing date: Feb 28 (or Feb 29 in leap year).
     - March billing date: March 31 (anchor day 31 is preserved because March has 31 days).
     - April billing date: April 30.

### 3.2 Duplicate Billing Prevention
- **Problem Statement:** A billing batch runner is invoked twice concurrently or retried following a transient network timeout.
- **RecurFlow Architectural Solution:**
  1. Relational Constraint: `invoices` enforces `CONSTRAINT uq_subscription_billing_period UNIQUE (subscription_id, billing_period_start, billing_period_end)`.
  2. Transactional Concurrency Control: The billing service initiates processing with `SELECT * FROM subscriptions WHERE id = :id FOR UPDATE`, serializing execution.
  3. If a second thread attempts insertion for an identical subscription and billing period, PostgreSQL immediately raises a unique violation error (SQLState `23505`), preventing duplicate invoice creation.

### 3.3 Partial Payments & Outstanding Balance Tracking
- **Problem Statement:** An invoice of \$1,000 receives a partial payment of \$400.
- **RecurFlow Architectural Solution:**
  1. Invoice created with `total_amount = 1000.00`, `amount_paid = 0.00`, `balance_due = 1000.00`, `status = 'CONFIRMED'`.
  2. Payment of \$400 recorded in `payments`.
  3. `payment_allocations` row inserted with `allocated_amount = 400.00`.
  4. Invoice row updated transactionally:
     $$i.\text{amount\_paid} = \sum \text{allocated\_amount} = 400.00$$
     $$i.\text{balance\_due} = i.\text{total\_amount} - i.\text{amount\_paid} = 600.00$$
     $$i.\text{status} = \text{'PARTIALLY\_PAID'}$$
  5. Check constraint `CHECK (balance_due = total_amount - amount_paid)` guarantees mathematical consistency.

### 3.4 Multiple Allocations from a Single Payment
- **Problem Statement:** Customer remits \$1,500 by bank transfer to clear two invoices: Invoice A (\$1,000) and Invoice B (\$500).
- **RecurFlow Architectural Solution:**
  1. Single payment record created: `payments` with `amount = 1500.00`.
  2. Two allocation records created:
     - Allocation 1: `(payment_id, invoice_id_A, 1000.00)`
     - Allocation 2: `(payment_id, invoice_id_B, 500.00)`
  3. Both invoices update to `amount_paid = total_amount`, `balance_due = 0.00`, `status = 'PAID'`.
  4. Payment updates `amount_allocated = 1500.00`.

### 3.5 Over-Allocation Prevention
- **Problem Statement:** User or API attempts to allocate \$600 from a \$500 payment.
- **RecurFlow Architectural Solution:**
  1. Application Validation: The payment service validates that `sum(existing_allocations) + new_allocation <= payment.amount`.
  2. Database Constraint Defense-in-Depth: The `payments` table tracks `amount_allocated` enforced by:
     `CONSTRAINT ck_payments_allocated CHECK (amount_allocated >= 0 AND amount_allocated <= amount)`.
  3. If an allocation exceeds unallocated funds, PostgreSQL rejects the update with a check constraint violation.

### 3.6 Historical Catalogue Price Changes
- **Problem Statement:** Product base price increases from \$100 to \$150. Existing quotes, subscriptions, and past invoices must not alter.
- **RecurFlow Architectural Solution:**
  1. Master catalogue table `products.sales_price` updates to \$150.
  2. Existing `quotation_lines.unit_price_snapshot` retains \$100.
  3. Existing `subscription_lines.unit_price_snapshot` retains \$100 (unless contract renewal or explicit amendment is executed).
  4. Past `invoice_lines.unit_price_snapshot` retains \$100.
  5. Historical financial integrity is completely insulated from catalogue drift.

### 3.7 Tax Rate Changes
- **Problem Statement:** Jurisdiction tax rate increases from 18% to 20% on July 1. Past invoices issued in June must remain at 18%.
- **RecurFlow Architectural Solution:**
  1. `tax_rates` updates or a new rate row is registered.
  2. Past invoice lines preserve `tax_rate_snapshot = 18.00` and `line_tax = computed_tax`.
  3. The tax calculation formula is stored frozen on the document line, preventing retrospective alteration.

### 3.8 Subscription Pause & Resumption
- **Problem Statement:** Customer pauses service for 15 days. What happens to billing dates and active invoicing?
- **RecurFlow Architectural Solution:**
  1. Status transitions to `PAUSED`. `subscriptions.paused_at` records the UTC timestamp.
  2. The billing engine skips all subscriptions where `status != 'ACTIVE'`. No invoices are generated during pause.
  3. Upon resumption:
     - `subscriptions.status` returns to `ACTIVE`.
     - `subscriptions.resumed_at` is logged.
     - `next_billing_date` is extended forward by the elapsed pause duration ($\Delta t = \text{resumed\_at} - \text{paused\_at}$), preserving fair unbilled days.

### 3.9 Subscription Renewal
- **Problem Statement:** A 1-year contract ends. Customer renews for another year. How is continuity maintained?
- **RecurFlow Architectural Solution:**
  1. A new subscription is created with `renewed_from_subscription_id = original_subscription.id`.
  2. The original subscription transitions to `status = 'CLOSED'` with `auto_close_reason = 'RENEWED_TO_SUB_YYYY_XXXXX'`.
  3. The renewal chain can be traversed recursively to report Customer Lifetime Value (LTV) and multi-year contract history.

### 3.10 Quotation Conversion
- **Problem Statement:** Staff confirms customer acceptance of quotation. Commercial terms must transfer to subscription atomically.
- **RecurFlow Architectural Solution:**
  1. Quotation status changes to `CONFIRMED`.
  2. Inside a single database transaction:
     - New `subscriptions` record created with `originating_quotation_id = quotations.id`.
     - Each `quotation_lines` entry is copied into `subscription_lines` with frozen snapshots (`description_snapshot`, `unit_price_snapshot`, `tax_rate_snapshot`) and `quotation_line_id`.
     - `quotations.is_converted` is set to `TRUE`.
  3. If `quotations.is_converted` is already `TRUE`, conversion requests are rejected with a conflict error (409 Conflict).

### 3.11 Discount Limits & Stacking
- **Problem Statement:** Customer attempts to redeem a promo code limited to 1 use per customer twice, or after total campaign redemptions have been exhausted.
- **RecurFlow Architectural Solution:**
  1. Discount rules specify `max_uses_total`, `max_uses_per_customer`, `min_order_amount`, `start_date`, and `end_date`.
  2. During checkout / billing execution, `discounts` row is locked (`FOR UPDATE`).
  3. Eligibility verification verifies:
     - `CURRENT_DATE BETWEEN start_date AND COALESCE(end_date, CURRENT_DATE)`
     - `subtotal >= min_order_amount`
     - `uses_count < COALESCE(max_uses_total, 2147483647)`
     - `COUNT(*) FROM discount_applications WHERE discount_id = :d AND customer_id = :c < max_uses_per_customer`
  4. Upon application, `discount_applications` row is inserted, and `discounts.uses_count` is incremented atomically.
  5. Stacking policy: At most one promotional code may be applied per invoice for MVP.

---

## 4. Issues Identified & Severity Matrix

| Issue ID | Severity | Entity / Area | Description & Architectural Impact | Required Remediation |
|---|---|---|---|---|
| **ISS-01** | **HIGH** | `payments` | Missing `amount_allocated` and over-allocation check constraint. Over-allocation was only prevented in application logic. | Add `amount_allocated NUMERIC(12, 2) NOT NULL DEFAULT 0.00` and `CHECK (amount_allocated >= 0 AND amount_allocated <= amount)`. |
| **ISS-02** | **MEDIUM** | `subscriptions` | Missing explicit self-referential foreign key for renewals. | Add `renewed_from_subscription_id BIGINT NULL REFERENCES subscriptions(id) ON DELETE SET NULL`. |
| **ISS-03** | **MEDIUM** | `subscriptions` | Status enum omitted intermediate negotiation states (`QUOTATION`, `CONFIRMED`). | Expand check constraint to: `CHECK (status IN ('DRAFT', 'QUOTATION', 'CONFIRMED', 'ACTIVE', 'PAUSED', 'CLOSED'))`. |
| **ISS-04** | **MEDIUM** | `subscriptions` | Missing temporal audit fields for pause/resume tracking. | Add `paused_at TIMESTAMP WITH TIME ZONE NULL` and `resumed_at TIMESTAMP WITH TIME ZONE NULL`. |
| **ISS-05** | **LOW** | `subscription_lines` | Lacked explicit foreign key pointing back to `quotation_lines.id`. | Add `quotation_line_id BIGINT NULL REFERENCES quotation_lines(id) ON DELETE SET NULL`. |

---

## 5. Gate 1 Review Decision

**DECISION: PASS WITH REQUIRED REFINEMENTS**

The schema architecture fulfills all core relational and business requirements. All 5 identified refinements are concrete, low-risk schema enrichments that will now be applied directly in Part 5 to produce the final, hardened specification for Gate 2 review.
