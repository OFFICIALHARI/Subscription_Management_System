# RecurFlow — Relational Data Dictionary

**System:** RecurFlow (Subscription Operations & Revenue Management)  
**Author:** Data Architect Specialist Agent  
**Specification Version:** 1.1.0 (Refined after Gate 1 Review)  
**Engine:** PostgreSQL 17  
**Reference Document:** `agent.md` (Sections 5, 7, 8)

---

## 1. Overview & Conventions

- **Data Types:** Conforms strictly to PostgreSQL 17 native standard types (`BIGINT`, `VARCHAR`, `NUMERIC`, `INTEGER`, `DATE`, `TIMESTAMP WITH TIME ZONE`, `BOOLEAN`, `JSONB`).
- **Monetary Precision:** All currency columns use `NUMERIC(12, 2)` representing decimal currency (two decimal places, maximum \$9,999,999,999.99).
- **Percentages:** Tax and discount percentages use `NUMERIC(5, 2)` (e.g., `18.00` represents 18.00%).
- **Timezone:** All timestamps store UTC instants (`TIMESTAMP WITH TIME ZONE`).

---

## 2. Table Dictionaries

### 2.1 Table: `users`
Stores internal users and portal accounts.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique surrogate identifier for user record. |
| `email` | `VARCHAR(255)` | No | UK, Index | None | Normalized (lowercase) email address; login identifier. |
| `hashed_password` | `VARCHAR(255)` | No | None | None | Argon2/bcrypt password hash. Plaintext strictly disallowed. |
| `role` | `VARCHAR(20)` | No | Index, `CHECK IN ('ADMIN', 'STAFF', 'CUSTOMER')` | None | System authorization role. Customer role is locked to portal. |
| `is_active` | `BOOLEAN` | No | None | `TRUE` | Soft-deactivation flag; inactive accounts cannot authenticate. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC timestamp of account creation. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC timestamp of last profile modification. |

---

### 2.2 Table: `customers`
Business customer profile and billing entity.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique surrogate customer identifier. |
| `user_id` | `BIGINT` | Yes | FK -> `users(id)`, UK | `NULL` | Optional link to `users` for self-service customer portal. |
| `company_name` | `VARCHAR(255)` | No | Index | None | Registered company or trade name. |
| `contact_name` | `VARCHAR(255)` | No | None | None | Primary billing contact full name. |
| `email` | `VARCHAR(255)` | No | Index | None | Primary customer correspondence and billing email. |
| `phone` | `VARCHAR(50)` | Yes | None | `NULL` | Contact telephone number. |
| `tax_identifier` | `VARCHAR(50)` | Yes | None | `NULL` | Official corporate tax identification number (GSTIN, VAT, EIN). |
| `billing_address_line1` | `VARCHAR(255)` | No | None | None | Primary physical billing address line. |
| `billing_address_line2` | `VARCHAR(255)` | Yes | None | `NULL` | Suite, unit, or floor details. |
| `billing_city` | `VARCHAR(100)` | No | None | None | Billing city / municipality. |
| `billing_state` | `VARCHAR(100)` | No | None | None | Billing state, province, or region. |
| `billing_postal_code` | `VARCHAR(30)` | No | None | None | Postal code / ZIP code. |
| `billing_country` | `VARCHAR(100)` | No | None | `'India'` | Country of billing jurisdiction. |
| `is_active` | `BOOLEAN` | No | Index | `TRUE` | Soft-archive flag. Active customers can receive quotes/invoices. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC timestamp when record was registered. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC timestamp when record was updated. |

---

### 2.3 Table: `audit_logs`
Immutable audit ledger for security, financial actions, and debugging.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Sequential unique log ID. |
| `actor_user_id` | `BIGINT` | Yes | FK -> `users(id)` `ON DELETE SET NULL` | `NULL` | User who initiated the action (NULL for automated system jobs). |
| `action` | `VARCHAR(100)` | No | None | None | Verb describing action (e.g. `BILLING_CYCLE_EXECUTED`). |
| `entity_type` | `VARCHAR(50)` | No | Index | None | Name of the entity affected (`quotation`, `subscription`, `invoice`). |
| `entity_id` | `BIGINT` | No | Index | None | Primary key ID of the affected entity. |
| `ip_address` | `VARCHAR(45)` | Yes | None | `NULL` | Client IP address (IPv4 or IPv6). |
| `metadata` | `JSONB` | No | None | `'{}'::jsonb` | Contextual diff or metadata payload. Sanitized (no passwords). |
| `created_at` | `TIMESTAMPTZ` | No | Index | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | Exact UTC moment of event execution. |

---

### 2.4 Table: `products`
Base commercial offerings, recurring services, and software licenses.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique surrogate product identifier. |
| `name` | `VARCHAR(255)` | No | Index | None | Commercial product title. |
| `product_type` | `VARCHAR(50)` | No | `CHECK IN ('SERVICE', 'SOFTWARE', 'PHYSICAL')` | `'SERVICE'` | Classification of product. |
| `sku` | `VARCHAR(100)` | Yes | UK | `NULL` | Unique Stock Keeping Unit or internal catalog code. |
| `description` | `TEXT` | Yes | None | `NULL` | Detailed customer-facing product description. |
| `sales_price` | `NUMERIC(12, 2)`| No | `CHECK (sales_price >= 0)` | `0.00` | Standard list selling price in base currency. |
| `cost_price` | `NUMERIC(12, 2)` | No | `CHECK (cost_price >= 0)` | `0.00` | Internal cost baseline for margin reporting. |
| `is_active` | `BOOLEAN` | No | Index | `TRUE` | Active flag; archived items cannot be added to new quotes. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC timestamp of item entry. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC timestamp of last item modification. |

---

### 2.5 Table: `product_variants`
Specific configurable options modifying base products (e.g. +560.00 price adjustment).

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique variant identifier. |
| `product_id` | `BIGINT` | No | FK -> `products(id)` `ON DELETE RESTRICT` | None | Parent catalog product. |
| `variant_name` | `VARCHAR(100)`| No | Compound UK | None | Name of the variation dimension (e.g., "Tier", "Bandwidth"). |
| `variant_value` | `VARCHAR(100)`| No | Compound UK | None | Specific choice (e.g., "Enterprise", "100GB"). |
| `sku_suffix` | `VARCHAR(50)` | Yes | None | `NULL` | Suffix appended to parent SKU. |
| `price_adjustment`| `NUMERIC(12, 2)`| No| None | `0.00` | Configurable price delta added to parent `products.sales_price`. |
| `is_active` | `BOOLEAN` | No | None | `TRUE` | Active flag for this variant option. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC update timestamp. |

---

### 2.6 Table: `tax_rates`
Tax jurisdiction rates and classification.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique tax rate ID. |
| `name` | `VARCHAR(100)`| No | None | None | Display title (e.g. "GST 18%", "Standard VAT 20%"). |
| `rate_percentage`| `NUMERIC(5, 2)`| No| `CHECK (rate_percentage BETWEEN 0 AND 100)` | None | Tax rate (e.g., 18.00 represents 18%). |
| `tax_type` | `VARCHAR(50)` | No | `CHECK IN ('EXCLUSIVE', 'INCLUSIVE')` | `'EXCLUSIVE'` | Calculation method (MVP standard is `'EXCLUSIVE'`). |
| `description` | `VARCHAR(255)`| Yes | None | `NULL` | Internal explanation or legal statute reference. |
| `is_active` | `BOOLEAN` | No | Index | `TRUE` | Soft-deactivation flag. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC update timestamp. |

---

### 2.7 Table: `plans`
Recurring billing cadences and commitment structures across all 4 frequencies.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique plan identifier. |
| `name` | `VARCHAR(255)`| No | None | None | Display plan name (e.g. "Enterprise Annual Plan"). |
| `code` | `VARCHAR(50)` | No | UK | None | Machine-readable code (e.g. `ENT-ANNUAL`). |
| `description` | `TEXT` | Yes | None | `NULL` | Commercial description of terms. |
| `billing_interval`| `VARCHAR(20)`| No | `CHECK IN ('DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY')` | None | Recurrence period type. |
| `interval_count` | `INTEGER` | No | `CHECK (interval_count >= 1)` | `1` | Frequency factor (e.g., 1 for 1 month, 3 for quarter). |
| `trial_period_days`| `INTEGER` | No | `CHECK (trial_period_days >= 0)` | `0` | Optional complimentary trial days before first billing run. |
| `minimum_quantity`| `INTEGER` | No | `CHECK (minimum_quantity >= 1)` | `1` | Contractual minimum subscription unit commitment. |
| `is_active` | `BOOLEAN` | No | Index | `TRUE` | Plan availability state. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC update timestamp. |

---

### 2.8 Table: `plan_items`
Product bundle specification associated with a recurring plan.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique surrogate ID. |
| `plan_id` | `BIGINT` | No | FK -> `plans(id)` `ON DELETE CASCADE` | None | Associated subscription plan. |
| `product_id` | `BIGINT` | No | FK -> `products(id)` `ON DELETE RESTRICT`| None | Included catalog product. |
| `product_variant_id`| `BIGINT`| Yes| FK -> `product_variants(id)` `ON DELETE RESTRICT`| `NULL`| Specific variant if bundled. |
| `quantity` | `INTEGER` | No | `CHECK (quantity >= 1)` | `1` | Included bundle unit quantity. |
| `unit_price` | `NUMERIC(12, 2)`| No| `CHECK (unit_price >= 0)` | None | Effective unit price charged under this plan. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |

---

### 2.9 Table: `quotation_templates`
Pre-packaged proposal templates for quick sales quotation drafting.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique template identifier. |
| `name` | `VARCHAR(255)`| No | None | None | Template name (e.g. "Standard SaaS Onboarding"). |
| `description` | `TEXT` | Yes | None | `NULL` | Usage guidelines for sales staff. |
| `default_validity_days`| `INTEGER`| No | `CHECK (default_validity_days >= 1)` | `30` | Default expiration period in days. |
| `is_active` | `BOOLEAN` | No | None | `TRUE` | Availability flag. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC update timestamp. |

---

### 2.10 Table: `quotations`
Customer proposal and quotation documents.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique quotation ID. |
| `quotation_number`| `VARCHAR(50)`| No | UK | None | Formatted sequence: `QUO-YYYY-XXXXX`. |
| `customer_id` | `BIGINT` | No | FK -> `customers(id)` `ON DELETE RESTRICT`| None | Target business customer. |
| `template_id` | `BIGINT` | Yes | FK -> `quotation_templates(id)` `ON DELETE SET NULL`| `NULL`| Originating quotation template. |
| `status` | `VARCHAR(20)` | No | Index, `CHECK IN ('DRAFT', 'SENT', 'CONFIRMED', 'CANCELLED', 'EXPIRED')` | `'DRAFT'` | Workflow state machine indicator. |
| `issue_date` | `DATE` | No | None | None | Issue calendar date. |
| `expiration_date`| `DATE` | No | Index, `CHECK (expiration_date >= issue_date)` | None | Quotation validity cutoff date. |
| `currency` | `VARCHAR(3)` | No | None | `'USD'` | ISO currency code. |
| `subtotal` | `NUMERIC(12, 2)`| No| `CHECK (subtotal >= 0)` | `0.00` | Sum of pre-tax line item amounts. |
| `discount_amount`| `NUMERIC(12, 2)`| No| `CHECK (discount_amount >= 0)` | `0.00` | Total discount subtracted from subtotal. |
| `tax_amount` | `NUMERIC(12, 2)`| No| `CHECK (tax_amount >= 0)` | `0.00` | Total calculated taxes. |
| `total_amount` | `NUMERIC(12, 2)`| No| `CHECK (total_amount >= 0)` | `0.00` | Net payable quotation value. |
| `is_converted` | `BOOLEAN` | No | None | `FALSE` | Set `TRUE` when converted to subscription; prevents re-conversion. |
| `notes` | `TEXT` | Yes | None | `NULL` | Customer-visible proposal terms. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC update timestamp. |

---

### 2.11 Table: `quotation_lines`
Individual line item breakdown on a quotation with frozen snapshots.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique line identifier. |
| `quotation_id` | `BIGINT` | No | FK -> `quotations(id)` `ON DELETE CASCADE`| None | Parent quotation record. |
| `product_id` | `BIGINT` | No | FK -> `products(id)` `ON DELETE RESTRICT`| None | Referenced catalog product. |
| `product_variant_id`| `BIGINT`| Yes| FK -> `product_variants(id)` `ON DELETE RESTRICT`| `NULL`| Optional product variant. |
| `plan_id` | `BIGINT` | Yes | FK -> `plans(id)` `ON DELETE RESTRICT` | `NULL` | Associated plan if line represents recurring item. |
| `description_snapshot`| `VARCHAR(500)`| No| None | None | Immutable snapshot of product and variant text. |
| `quantity` | `INTEGER` | No | `CHECK (quantity >= 1)` | `1` | Quoted units. |
| `unit_price_snapshot`| `NUMERIC(12, 2)`| No| `CHECK (unit_price_snapshot >= 0)` | None | Frozen unit price (base + variant adjustment). |
| `discount_rate` | `NUMERIC(5, 2)` | No | `CHECK (discount_rate BETWEEN 0 AND 100)` | `0.00` | Percentage discount on line. |
| `tax_rate_id` | `BIGINT` | Yes | FK -> `tax_rates(id)` `ON DELETE SET NULL` | `NULL` | Tax rule reference. |
| `tax_rate_snapshot`| `NUMERIC(5, 2)`| No| None | `0.00` | Frozen tax percentage at quote generation. |
| `line_subtotal` | `NUMERIC(12, 2)`| No| None | None | `quantity * unit_price_snapshot * (1 - discount_rate/100)`. |
| `line_tax` | `NUMERIC(12, 2)`| No| None | `0.00` | Computed line tax amount. |
| `line_total` | `NUMERIC(12, 2)`| No| None | None | `line_subtotal + line_tax`. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |

---

### 2.12 Table: `subscriptions`
Contractual recurring subscription commitments with renewal and pause tracking.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique subscription ID. |
| `subscription_number`| `VARCHAR(50)`| No | UK | None | Formatted sequence: `SUB-YYYY-XXXXX`. |
| `customer_id` | `BIGINT` | No | FK -> `customers(id)` `ON DELETE RESTRICT`| None | Account holder. |
| `plan_id` | `BIGINT` | No | FK -> `plans(id)` `ON DELETE RESTRICT` | None | Governing billing plan. |
| `originating_quotation_id`| `BIGINT`| Yes| FK -> `quotations(id)` `ON DELETE SET NULL`| `NULL`| Upstream accepted quotation that generated this subscription. |
| `renewed_from_subscription_id`| `BIGINT`| Yes| FK -> `subscriptions(id)` `ON DELETE SET NULL`, Index | `NULL` | Parent subscription in renewal lineage chain. |
| `status` | `VARCHAR(20)` | No | Index, `CHECK IN ('DRAFT', 'QUOTATION', 'CONFIRMED', 'ACTIVE', 'PAUSED', 'CLOSED')` | `'DRAFT'` | Subscription lifecycle state. Only ACTIVE triggers billing. |
| `start_date` | `DATE` | No | None | None | Date contract begins. |
| `end_date` | `DATE` | Yes | `CHECK (end_date IS NULL OR end_date >= start_date)` | `NULL` | Cancellation or expiration date (NULL if perpetual auto-renewing). |
| `billing_anchor_day`| `INTEGER` | No | `CHECK (billing_anchor_day BETWEEN 1 AND 31)` | None | Fixed day of month for recurring billing (e.g., 15th, 31st). |
| `next_billing_date` | `DATE` | No | Index | None | Due date evaluated by billing cycle runner. |
| `payment_terms_days`| `INTEGER` | No | `CHECK (payment_terms_days >= 0)` | `15` | Days added to invoice issue date to compute `due_date`. |
| `currency` | `VARCHAR(3)` | No | None | `'USD'` | Currency code. |
| `recurring_amount` | `NUMERIC(12, 2)`| No| `CHECK (recurring_amount >= 0)` | `0.00` | Normalized recurring contract value per billing cycle. |
| `paused_at` | `TIMESTAMPTZ` | Yes | None | `NULL` | UTC timestamp when subscription was paused. |
| `resumed_at` | `TIMESTAMPTZ` | Yes | None | `NULL` | UTC timestamp when subscription was resumed from pause. |
| `auto_close_reason` | `VARCHAR(255)`| Yes| None | `NULL` | Reason text when subscription is terminated/closed. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC update timestamp. |

---

### 2.13 Table: `subscription_lines`
Contracted lines copied to invoice lines upon recurring billing execution.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique subscription line ID. |
| `subscription_id`| `BIGINT` | No | FK -> `subscriptions(id)` `ON DELETE CASCADE`| None | Parent subscription. |
| `product_id` | `BIGINT` | No | FK -> `products(id)` `ON DELETE RESTRICT`| None | Catalog product. |
| `product_variant_id`| `BIGINT`| Yes| FK -> `product_variants(id)` `ON DELETE RESTRICT`| `NULL`| Variant option. |
| `quotation_line_id`| `BIGINT` | Yes| FK -> `quotation_lines(id)` `ON DELETE SET NULL`, Index | `NULL` | Lineage link to originating quotation line item. |
| `description_snapshot`| `VARCHAR(500)`| No| None | None | Frozen descriptive text for billing invoices. |
| `quantity` | `INTEGER` | No | `CHECK (quantity >= 1)` | `1` | Recurring contracted quantity. |
| `unit_price_snapshot`| `NUMERIC(12, 2)`| No| `CHECK (unit_price_snapshot >= 0)` | None | Frozen contract price per unit (base + variant adjustment). |
| `tax_rate_id` | `BIGINT` | Yes | FK -> `tax_rates(id)` `ON DELETE SET NULL` | `NULL` | Applicable tax rule. |
| `tax_rate_snapshot`| `NUMERIC(5, 2)`| No| None | `0.00` | Frozen tax percentage. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC update timestamp. |

---

### 2.14 Table: `subscription_events`
Audit history of state transitions for subscriptions.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Sequential event identifier. |
| `subscription_id`| `BIGINT` | No | FK -> `subscriptions(id)` `ON DELETE CASCADE`| None | Target subscription. |
| `event_type` | `VARCHAR(50)` | No | None | None | Action name (`CREATED`, `ACTIVATED`, `PAUSED`, `RESUMED`, `CLOSED`). |
| `actor_user_id` | `BIGINT` | Yes | FK -> `users(id)` `ON DELETE SET NULL` | `NULL` | Actor user ID or NULL for system automation. |
| `from_status` | `VARCHAR(20)` | Yes | None | `NULL` | Prior status before mutation. |
| `to_status` | `VARCHAR(20)` | No | None | None | New status after mutation. |
| `reason` | `VARCHAR(255)`| Yes | None | `NULL` | Administrative or customer reason for change. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC event timestamp. |

---

### 2.15 Table: `discounts`
Promotional rules, coupons, and percentage allowances.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique discount ID. |
| `code` | `VARCHAR(50)` | No | UK, Index | None | Promotion redemption code (e.g., `STARTUP100`). |
| `name` | `VARCHAR(255)`| No | None | None | Internal campaign name. |
| `discount_type` | `VARCHAR(20)` | No | `CHECK IN ('PERCENTAGE', 'FIXED_AMOUNT')` | None | Discount calculation algorithm. |
| `discount_value`| `NUMERIC(12, 2)`| No| `CHECK (discount_value > 0)` | None | Percentage value (1..100) or fixed currency credit. |
| `min_order_amount`| `NUMERIC(12, 2)`| No| `CHECK (min_order_amount >= 0)` | `0.00` | Minimum subtotal required for discount qualification. |
| `max_uses_total`| `INTEGER` | Yes | None | `NULL` | Global maximum redemptions (NULL for unlimited). |
| `uses_count` | `INTEGER` | No | `CHECK (uses_count >= 0)` | `0` | Live counter of completed redemptions. |
| `max_uses_per_customer`| `INTEGER`| No | `CHECK (max_uses_per_customer >= 1)` | `1` | Max times a single customer can redeem this discount. |
| `start_date` | `DATE` | No | None | None | Promotion start calendar date. |
| `end_date` | `DATE` | Yes | `CHECK (end_date IS NULL OR end_date >= start_date)` | `NULL` | Expiration calendar date. |
| `is_active` | `BOOLEAN` | No | Index | `TRUE` | Administrative active state. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC update timestamp. |

---

### 2.16 Table: `discount_applications`
Transactional audit log connecting applied discounts to generated invoices.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique application ID. |
| `discount_id` | `BIGINT` | No | FK -> `discounts(id)` `ON DELETE RESTRICT`| None | Discount rule redeemed. |
| `customer_id` | `BIGINT` | No | FK -> `customers(id)` `ON DELETE RESTRICT`| None | Redeeming customer. |
| `invoice_id` | `BIGINT` | No | FK -> `invoices(id)` `ON DELETE CASCADE` | None | Billed invoice receiving deduction. |
| `applied_amount`| `NUMERIC(12, 2)`| No| `CHECK (applied_amount > 0)` | None | Exact currency amount deducted. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC redemption timestamp. |

---

### 2.17 Table: `invoices`
Authoritative commercial billing invoices with duplicate period prevention.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique invoice ID. |
| `invoice_number`| `VARCHAR(50)`| No | UK | None | Formatted sequence: `INV-YYYY-XXXXX`. |
| `customer_id` | `BIGINT` | No | FK -> `customers(id)` `ON DELETE RESTRICT`| None | Customer billed. |
| `subscription_id`| `BIGINT` | Yes | FK -> `subscriptions(id)` `ON DELETE RESTRICT`| `NULL`| Originating subscription (NULL for ad-hoc invoices). |
| `billing_period_start`| `DATE` | Yes | Compound UK | `NULL` | Service start date covered by this invoice. |
| `billing_period_end` | `DATE` | Yes | Compound UK | `NULL` | Service end date covered by this invoice. |
| `issue_date` | `DATE` | No | Index | None | Official date invoice is issued. |
| `due_date` | `DATE` | No | Index, `CHECK (due_date >= issue_date)` | None | Payment due date. |
| `status` | `VARCHAR(20)` | No | Index, `CHECK IN ('DRAFT', 'CONFIRMED', 'PAID', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED')` | `'DRAFT'` | Status of the invoice. |
| `currency` | `VARCHAR(3)` | No | None | `'USD'` | Currency code. |
| `subtotal` | `NUMERIC(12, 2)`| No| `CHECK (subtotal >= 0)` | `0.00` | Sum of pre-tax line totals. |
| `discount_amount`| `NUMERIC(12, 2)`| No| `CHECK (discount_amount >= 0)` | `0.00` | Subtracted discount allowance. |
| `tax_amount` | `NUMERIC(12, 2)`| No| `CHECK (tax_amount >= 0)` | `0.00` | Calculated tax total. |
| `total_amount` | `NUMERIC(12, 2)`| No| `CHECK (total_amount >= 0)` | `0.00` | Net payable balance. |
| `amount_paid` | `NUMERIC(12, 2)`| No| `CHECK (amount_paid >= 0 AND amount_paid <= total_amount)` | `0.00` | Cumulative settled payments allocated to this invoice. |
| `balance_due` | `NUMERIC(12, 2)`| No| `CHECK (balance_due = total_amount - amount_paid)` | `0.00` | Outstanding unpaid balance. |
| `pdf_generated_at`| `TIMESTAMPTZ`| Yes| None | `NULL` | UTC timestamp of PDF document rendering. |
| `notes` | `TEXT` | Yes | None | `NULL` | Terms or remarks displayed on document. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC update timestamp. |

*Note on Compound Idempotency Key:*
`UNIQUE (subscription_id, billing_period_start, billing_period_end)` strictly blocks double-billing for the same subscription period.

---

### 2.18 Table: `invoice_lines`
Individual itemized charges on an invoice.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique line identifier. |
| `invoice_id` | `BIGINT` | No | FK -> `invoices(id)` `ON DELETE CASCADE` | None | Parent invoice. |
| `subscription_line_id`| `BIGINT`| Yes| FK -> `subscription_lines(id)` `ON DELETE SET NULL`| `NULL`| Upstream subscription line item reference. |
| `description_snapshot`| `VARCHAR(500)`| No| None | None | Frozen descriptive snapshot. |
| `quantity` | `INTEGER` | No | `CHECK (quantity >= 1)` | `1` | Units billed. |
| `unit_price_snapshot`| `NUMERIC(12, 2)`| No| `CHECK (unit_price_snapshot >= 0)` | None | Frozen unit price (base + variant adjustment). |
| `discount_amount`| `NUMERIC(12, 2)`| No| `CHECK (discount_amount >= 0)` | `0.00` | Line-level discount deducted. |
| `tax_rate_snapshot`| `NUMERIC(5, 2)`| No| None | `0.00` | Frozen tax percentage rate. |
| `line_subtotal` | `NUMERIC(12, 2)`| No| None | None | Pre-tax line subtotal. |
| `line_tax` | `NUMERIC(12, 2)`| No| None | `0.00` | Computed line tax. |
| `line_total` | `NUMERIC(12, 2)`| No| None | None | Net line total (`line_subtotal + line_tax`). |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |

---

### 2.19 Table: `payments`
Customer payments received and recorded with over-allocation defense-in-depth.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique payment record ID. |
| `payment_number`| `VARCHAR(50)`| No | UK | None | Formatted sequence: `PAY-YYYY-XXXXX`. |
| `customer_id` | `BIGINT` | No | FK -> `customers(id)` `ON DELETE RESTRICT`| None | Remitting customer. |
| `payment_method`| `VARCHAR(50)`| No | `CHECK IN ('BANK_TRANSFER', 'CHEQUE', 'CASH', 'MANUAL_OTHER')` | None | Instrument or channel. No card numbers stored. |
| `amount` | `NUMERIC(12, 2)`| No| `CHECK (amount > 0)` | None | Total funds received in this payment. |
| `amount_allocated`| `NUMERIC(12, 2)`| No| `CHECK (amount_allocated >= 0 AND amount_allocated <= amount)` | `0.00` | Cumulative amount allocated across invoices. |
| `currency` | `VARCHAR(3)` | No | None | `'USD'` | Currency code. |
| `paid_at` | `DATE` | No | Index | None | Calendar date funds were cleared / received. |
| `transaction_reference`| `VARCHAR(100)`| Yes| None | `NULL` | Bank reference, UTR, or cheque clearance code. |
| `notes` | `TEXT` | Yes | None | `NULL` | Internal verification or ledger notes. |
| `status` | `VARCHAR(20)` | No | `CHECK IN ('SUCCESS', 'CANCELLED')` | `'SUCCESS'` | Payment settlement status. |
| `created_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC creation timestamp. |
| `updated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC update timestamp. |

---

### 2.20 Table: `payment_allocations`
Apportionment of payment funds to invoices.

| Column | Data Type | Nullable | Keys / Constraints | Default | Business Definition & Validation Rules |
|---|---|---|---|---|---|
| `id` | `BIGINT` | No | PK | `GENERATED ALWAYS AS IDENTITY` | Unique allocation ID. |
| `payment_id` | `BIGINT` | No | FK -> `payments(id)` `ON DELETE RESTRICT`| None | Funding payment record. |
| `invoice_id` | `BIGINT` | No | FK -> `invoices(id)` `ON DELETE RESTRICT`| None | Settled invoice document. |
| `allocated_amount`| `NUMERIC(12, 2)`| No| `CHECK (allocated_amount > 0)` | None | Currency portion credited against `invoice_id`. |
| `allocated_at` | `TIMESTAMPTZ` | No | None | `CURRENT_TIMESTAMP AT TIME ZONE 'UTC'` | UTC timestamp of allocation execution. |
