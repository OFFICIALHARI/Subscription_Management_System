# RecurFlow — Billing Cycle Rules & Date Calculation Specification

**System:** RecurFlow (Subscription Operations & Revenue Management)  
**Author:** Lead Software Architect & Financial Systems Engineer  
**Component:** Centralized Billing Engine & Date Arithmetic Engine  
**Specification Reference:** `agent.md`, Section 7 & Section 13  

---

## 1. Core Principles & Frequency Standards

Recurring billing dates in RecurFlow are deterministic, auditable, and mathematically invariant. They are centralized in `app.services.billing_date_service` to eliminate calculation drift across different API endpoints and background workers.

The engine supports four canonical billing frequencies:
1. **Daily (`DAILY`):** Re-bills every $N$ calendar days (default $N=1$).
2. **Weekly (`WEEKLY`):** Re-bills every $N \times 7$ calendar days (default $N=1$, exactly 7 days).
3. **Monthly (`MONTHLY`):** Re-bills every $N$ calendar months (default $N=1$, quarterly $N=3$, bi-annual $N=6$).
4. **Yearly (`YEARLY`):** Re-bills every $N$ calendar years (default $N=1$).

---

## 2. Monthly Billing Anchor Day Algorithm

### 2.1 The End-of-Month Drift Problem
If a customer subscribes on January 31, simple repeated month-addition algorithms (`date + 1 month`) cause catastrophic date drift:
- Jan 31 + 1 month $\to$ Feb 28.
- Feb 28 + 1 month $\to$ March 28 (Incorrect! Customer contract was for the 31st).
- March 28 + 1 month $\to$ April 28 (Customer permanently lost 3 billing days each month).

### 2.2 The RecurFlow Stable Anchor Strategy
Every subscription stores a permanent `billing_anchor_day INTEGER NOT NULL CHECK (billing_anchor_day BETWEEN 1 AND 31)` set at contract creation.

For any target calculation of cycle index $k \ge 1$ from contract start year $Y_0$ and month $M_0$:
$$\text{Total Months} = (M_0 - 1) + (k \times \text{interval\_count})$$
$$\text{Target Year } Y = Y_0 + \lfloor \text{Total Months} / 12 \rfloor$$
$$\text{Target Month } M = (\text{Total Months} \pmod{12}) + 1$$
$$\text{Max Days} = \text{days\_in\_month}(Y, M)$$
$$\text{Billing Date} = \text{DATE}(Y, M, \min(\text{billing\_anchor\_day}, \text{Max Days}))$$

### 2.3 Demonstration Example: January 31 Anchor
| Cycle | Target Year & Month | Max Days | Calculated Billing Date | Explanatory Rule |
|---|---|---|---|---|
| Initial | 2026-01 | 31 | **2026-01-31** | Contract start date |
| Cycle 1 | 2026-02 | 28 | **2026-02-28** | Clamped to Feb last day; anchor remains 31 |
| Cycle 2 | 2026-03 | 31 | **2026-03-31** | Restored to 31st (March has 31 days) |
| Cycle 3 | 2026-04 | 30 | **2026-04-30** | Clamped to April last day (30 days) |
| Cycle 4 | 2026-05 | 31 | **2026-05-31** | Restored to 31st |

### 2.4 Leap Year Month-End Demonstration (Year 2028)
- 2028-01-31 (Start)
- 2028-02-29 (Feb has 29 days in leap year 2028)
- 2028-03-31 (Restored to 31st)

---

## 3. Yearly Billing & Leap Year Anchors

When a customer subscribes on a leap day (**February 29**):
- `billing_anchor_month = 2`
- `billing_anchor_day = 29`

Calculation for Year $Y$:
- If $Y$ is a leap year $\implies$ **February 29**
- If $Y$ is a non-leap year $\implies$ **February 28**

Example:
- Start: 2024-02-29 (Leap year)
- Year 1: 2025-02-28 (Non-leap year)
- Year 2: 2026-02-28 (Non-leap year)
- Year 3: 2027-02-28 (Non-leap year)
- Year 4: 2028-02-29 (Leap year — anchor automatically restored!)

---

## 4. Weekly and Daily Frequencies

- **Weekly Billing:**
  $$\text{next\_billing\_date} = \text{current\_billing\_date} + (7 \times \text{interval\_count}) \text{ days}$$
  Exactly 7 calendar days per interval count.
- **Daily Billing:**
  $$\text{next\_billing\_date} = \text{current\_billing\_date} + (1 \times \text{interval\_count}) \text{ days}$$

---

## 5. Timezone & Temporal Boundary Policy

1. **Storage Standards:**
   - All audit logs, event occurrences, and transaction commits store UTC instants (`TIMESTAMP WITH TIME ZONE`).
   - Commercial billing periods (`billing_period_start`, `billing_period_end`) and document issuance dates (`issue_date`, `due_date`) use native `DATE` types representing pure calendar dates.
2. **Billing Timezone:** The application standardizes on `UTC` for evaluating recurring cycle eligibility.
3. **Period Interval Convention:** RecurFlow adopts the standard commercial semi-open interval:
   $$[\text{billing\_period\_start}, \text{billing\_period\_end})$$
   Where `billing_period_start` is inclusive (first day of service) and `billing_period_end` is exclusive (date of next cycle).
   Example: January Monthly Bill $\implies [2026\text{-}01\text{-}01, 2026\text{-}02\text{-}01)$.

---

## 6. Subscription Pause & Resumption Dynamics

### 6.1 Status Enforcement
- Subscriptions in `PAUSED` status are completely skipped by the billing cycle runner. No invoices are ever generated during a pause.
- Existing historical invoices remain untouched and immutable.

### 6.2 Resumption Date Arithmetic
When a customer resumes service:
1. The pause elapsed duration is calculated:
   $$\Delta \text{days} = \max(1, (\text{resumed\_date} - \text{paused\_date}).\text{days})$$
2. If the pause occurred **before** the scheduled `next_billing_date`, the `next_billing_date` is extended forward by $\Delta \text{days}$ to credit the customer with unconsumed paid days.
3. If the pause was extended past the original `next_billing_date`, the new cycle begins on `resumed_date`, with the anchor day re-aligned or preserved per customer contract terms.
4. An event is appended to `subscription_events` recording the exact transition and duration.

---

## 7. Idempotency & Repeatable Execution

1. **Composite Database Uniqueness:**
   `invoices` enforces:
   ```sql
   CONSTRAINT uq_subscription_billing_period UNIQUE (subscription_id, billing_period_start, billing_period_end)
   ```
2. **Worker Idempotency:**
   If a cron job or admin runs the billing cycle endpoint multiple times on the same date:
   - The query selects `WHERE status = 'ACTIVE' AND next_billing_date <= :run_date`.
   - Once the invoice is generated, `subscriptions.next_billing_date` is advanced atomically in the same transaction.
   - Any duplicate execution detects the existing invoice and skips processing safely with zero side effects.
