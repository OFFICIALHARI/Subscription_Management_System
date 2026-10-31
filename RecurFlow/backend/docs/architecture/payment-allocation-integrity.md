# RecurFlow — Payment Allocation Integrity Specification

**System:** RecurFlow (Subscription Operations & Revenue Management)  
**Author:** Lead Software Architect & Financial Systems Engineer  
**Component:** Payment Capture, Ledger Allocations, and Balance Reconciliation  
**Specification Reference:** `agent.md`, Hackathon Technical Invariants  

---

## 1. Architectural Principles & Financial Invariants

RecurFlow models payments and commercial invoice settlements using double-entry inspired allocation ledgers rather than single-link foreign keys. This supports the real-world commercial requirements:
- One payment allocated to one invoice.
- One payment split across multiple invoices (e.g., enterprise remittance clearing multiple monthly bills).
- Multiple payments applied to a single invoice (e.g., partial payment, deposits, milestone settlements).
- Partial payments leaving an unallocated balance on the payment or an outstanding balance on the invoice.
- Reversible allocations for auditing, payment cancellations, or corrections.

### 1.1 Mathematical Invariants

For every payment record $P$:
$$P.\text{amount} > 0$$
$$\text{total\_allocated}(P) = \sum_{a \in \text{Allocations}(P)} a.\text{allocated\_amount}$$
$$0 \le \text{total\_allocated}(P) \le P.\text{amount}$$
$$\text{unallocated\_balance}(P) = P.\text{amount} - \text{total\_allocated}(P)$$

For every invoice record $I$:
$$I.\text{total\_amount} \ge 0$$
$$\text{total\_allocated\_to\_invoice}(I) = \sum_{a \in \text{Allocations}(I)} a.\text{allocated\_amount}$$
$$0 \le \text{total\_allocated\_to\_invoice}(I) \le I.\text{total\_amount}$$
$$I.\text{amount\_paid} = \text{total\_allocated\_to\_invoice}(I)$$
$$I.\text{balance\_due} = I.\text{total\_amount} - I.\text{amount\_paid}$$

### 1.2 State Transition Matrix based on Realized Allocations

An invoice's payment status is strictly derived from its settled allocations:
- If $I.\text{amount\_paid} == 0$ and $\text{now}() \le I.\text{due\_date} \implies \text{CONFIRMED}$
- If $I.\text{amount\_paid} == 0$ and $\text{now}() > I.\text{due\_date} \implies \text{OVERDUE}$
- If $0 < I.\text{amount\_paid} < I.\text{total\_amount}$ and $\text{now}() \le I.\text{due\_date} \implies \text{PARTIALLY\_PAID}$
- If $0 < I.\text{amount\_paid} < I.\text{total\_amount}$ and $\text{now}() > I.\text{due\_date} \implies \text{OVERDUE}$
- If $I.\text{amount\_paid} == I.\text{total\_amount} \implies \text{PAID}$
- Voided / Cancelled $\implies \text{CANCELLED}$ (Allocations prohibited)

---

## 2. Source-of-Truth Resolution: Ledger vs. Aggregates

### 2.1 The Inconsistency Vulnerability
Storing mutable aggregates (`payments.amount_allocated`, `invoices.amount_paid`) risks silent divergence if background scripts, concurrent requests, or partial crashes update the parent record without recording a matching allocation ledger entry.

### 2.2 Authoritative Ledger Architecture
1. **Source of Truth:** Individual rows in `payment_allocations` constitute the immutable source of truth.
2. **Materialized Aggregates:** `payments.amount_allocated`, `invoices.amount_paid`, and `invoices.balance_due` are maintained transactionally in the same database transaction that creates or removes an allocation.
3. **Database Constraint Defense-in-Depth:**
   - PostgreSQL check constraint: `CONSTRAINT ck_payments_allocated CHECK (amount_allocated >= 0 AND amount_allocated <= amount)`
   - PostgreSQL check constraint: `CONSTRAINT ck_invoices_amounts CHECK (amount_paid >= 0 AND amount_paid <= total_amount AND balance_due = (total_amount - amount_paid))`
4. **Reconciliation Invariant Verification:** Service layer assertions continuously verify that:
   $$\text{stored\_aggregate} \equiv \sum \text{allocation\_rows}$$
   Any detected mismatch immediately aborts the transaction with an internal reconciliation error.

---

## 3. Concurrency Safety & Deadlock Prevention

### 3.1 Race Condition Scenario
If two concurrent API requests attempt to allocate remaining funds from the same payment (e.g., Payment \$1,000 has \$700 allocated, leaving \$300; Request 1 attempts to allocate \$200 to Invoice A, while Request 2 attempts to allocate \$200 to Invoice B):
- Without pessimistic locking, both read `unallocated = 300`, both pass validation, both commit \$200, resulting in \$1,100 allocated (an over-allocation of \$100).

### 3.2 Row-Level Locking Protocol (`SELECT ... FOR UPDATE`)
Every allocation operation executes within an isolated database transaction adhering to this lock protocol:

1. **Step 1: Lock Payment Record**
   ```sql
   SELECT * FROM payments WHERE id = :payment_id FOR UPDATE;
   ```
   This serializes all concurrent allocation attempts on the same payment. Only one request proceeds at a time.
2. **Step 2: Lock Invoice Records in Ascending ID Order**
   ```sql
   SELECT * FROM invoices WHERE id IN (:invoice_ids) ORDER BY id ASC FOR UPDATE;
   ```
   Sorting invoice IDs in strictly ascending order prevents cyclic wait conditions (deadlocks) when multiple transactions touch overlapping sets of invoices.
3. **Step 3: Evaluate Live Unallocated Balances**
   Query actual allocation sums or read the locked row's verified fields. If `new_amount > (payment.amount - payment.amount_allocated)`, rollback and raise `PaymentOverAllocationError`.
4. **Step 4: Evaluate Live Invoice Balance**
   If `new_amount > invoice.balance_due`, rollback and raise `InvoiceOverPaymentError`.
5. **Step 5: Insert Allocation & Update Materialized Aggregates**
   Write to `payment_allocations`, update `payments`, update `invoices`.
6. **Step 6: Atomic Commit**

---

## 4. Reversals, Refunds, and Status Auditing

### 4.1 Payment Cancellation / Reversal
- When a payment is marked `CANCELLED` (e.g., bounced cheque, chargeback, or clerical correction):
  - Any active allocations linked to that payment are reversed.
  - Target invoices have their `amount_paid` decremented and `balance_due` restored.
  - Target invoice status reverts from `PAID` $\to$ `PARTIALLY_PAID` or `CONFIRMED`/`OVERDUE`.
  - Payment updates `amount_allocated = 0.00` and `status = 'CANCELLED'`.
  - An audit record is written to `audit_logs`.

### 4.2 Invoice Cancellation
- A draft or confirmed invoice with zero payments can transition to `CANCELLED`.
- If an invoice has existing payments allocated:
  - Either allocations must be explicitly reversed first, or
  - The payment funds are credited back to the customer's unallocated payment balance.
  - Active allocations on cancelled invoices are strictly forbidden.

---

## 5. Security & Isolation Invariants

- **Customer Match Guarantee:** A payment from Customer $X$ can **never** be allocated to an invoice belonging to Customer $Y$. The service enforces:
  $$\text{assert } \text{payment.customer\_id} == \text{invoice.customer\_id}$$
  Violations raise `CustomerMismatchError` (403 Forbidden).
