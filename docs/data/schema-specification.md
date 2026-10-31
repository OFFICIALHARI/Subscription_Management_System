# RecurFlow — Relational Database Schema Specification

**System:** RecurFlow (Subscription Operations & Revenue Management)  
**Author:** Data Architect Specialist Agent  
**Review Gate:** Gate 2 Review Submission  
**Reference Document:** `agent.md` (Sections 5, 7, 8, 13)

---

## 1. Architectural Foundations & Global Invariants

### 1.1 Technology Selection & Precision Standards
- **Target Engine:** PostgreSQL 16+
- **Dialect & Driver:** SQLAlchemy 2 with `psycopg` (v3 binary)
- **Monetary Representation:** Every monetary amount (prices, subtotals, discounts, tax amounts, line totals, balances) must strictly use `NUMERIC(12, 2)`. Floating point types (`REAL`, `DOUBLE PRECISION`, `FLOAT`) are forbidden across all tables.
- **Quantity Representation:** Quantities use `NUMERIC(10, 2)` or `INTEGER >= 1` depending on fractional entitlement support. In RecurFlow, standard unit quantities use `INTEGER CHECK (quantity > 0)`.
- **Temporal Handling:** All timestamps (`created_at`, `updated_at`, `event_time`, `paid_at`) are stored as `TIMESTAMP WITH TIME ZONE` strictly in `UTC`. Dates without time components (`start_date`, `end_date`, `issue_date`, `due_date`, `next_billing_date`) use `DATE`.

### 1.2 Identifier Strategy
- **Internal Primary Keys:** Every table uses a surrogate primary key `id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY` for optimal B-Tree index locality, join performance, and foreign key storage.
- **External Business Numbers:** Financial and customer-facing records use unique, sequenced business identifiers with format-enforced check constraints:
  - Quotation Number: `QUO-YYYY-XXXXX` (e.g., `QUO-2026-00001`)
  - Subscription Number: `SUB-YYYY-XXXXX` (e.g., `SUB-2026-00001`)
  - Invoice Number: `INV-YYYY-XXXXX` (e.g., `INV-2026-00001`)
  - Payment Reference: `PAY-YYYY-XXXXX` (e.g., `PAY-2026-00001`)

### 1.3 Auditability & Immutability Architecture
- **Financial Line Item Snapshots:** Quotation and Invoice lines must be completely immutable once issued. They store snapshot copies of product name, variant description, unit price, and applied tax rate. When catalog prices or tax rules change later, historical quotations, subscriptions, and invoices remain intact.
- **Deletion Prevention (Soft Delete / Archive):** Master records (`customers`, `products`, `plans`, `discounts`, `tax_rates`) must never be hard-deleted if referenced in quotes, subscriptions, or invoices. Foreign keys enforce `ON DELETE RESTRICT`. Soft deletion is achieved via `is_active BOOLEAN DEFAULT TRUE` and `archived_at TIMESTAMP WITH TIME ZONE NULL`.
- **Audit Trails:** Critical state changes in quotes, subscriptions, invoices, and payments emit immutable records into `audit_logs` and `subscription_events`.

### 1.4 Recurring Billing Idempotency
To eliminate duplicate invoice generation, a PostgreSQL composite unique constraint is enforced:
$$\text{UNIQUE}(\text{subscription\_id}, \text{billing\_period\_start}, \text{billing\_period\_end})$$
Repeated executions of the billing cycle runner within the same period are safely rejected or skipped by the engine.

---

## 2. Relational Entity Specifications

### 2.1 Identity and Customer CRM

#### Table: `users`
System actors (Admin, Staff, Customer).
```sql
CREATE TABLE users (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL, -- 'ADMIN', 'STAFF', 'CUSTOMER'
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT ck_users_role CHECK (role IN ('ADMIN', 'STAFF', 'CUSTOMER'))
);
CREATE INDEX ix_users_email ON users (email);
CREATE INDEX ix_users_role ON users (role);
```

#### Table: `customers`
Business customer profiles and address details.
```sql
CREATE TABLE customers (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id BIGINT NULL, -- linked when customer has portal login
    company_name VARCHAR(255) NOT NULL,
    contact_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50) NULL,
    tax_identifier VARCHAR(50) NULL, -- GSTIN / VAT / EIN
    billing_address_line1 VARCHAR(255) NOT NULL,
    billing_address_line2 VARCHAR(255) NULL,
    billing_city VARCHAR(100) NOT NULL,
    billing_state VARCHAR(100) NOT NULL,
    billing_postal_code VARCHAR(30) NOT NULL,
    billing_country VARCHAR(100) NOT NULL DEFAULT 'India',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_customers_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT uq_customers_user_id UNIQUE (user_id)
);
CREATE INDEX ix_customers_company_name ON customers (company_name);
CREATE INDEX ix_customers_email ON customers (email);
CREATE INDEX ix_customers_is_active ON customers (is_active);
```

#### Table: `audit_logs`
Immutable audit ledger for system actions and mutations.
```sql
CREATE TABLE audit_logs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_user_id BIGINT NULL,
    action VARCHAR(100) NOT NULL, -- 'CREATE_QUOTE', 'CONVERT_SUB', 'RUN_BILLING', 'ALLOCATE_PAYMENT', etc.
    entity_type VARCHAR(50) NOT NULL, -- 'quotation', 'subscription', 'invoice', 'payment'
    entity_id BIGINT NOT NULL,
    ip_address VARCHAR(45) NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_audit_logs_actor FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX ix_audit_logs_entity ON audit_logs (entity_type, entity_id);
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);
```

---

### 2.2 Product Catalog, Variants, Plans & Taxes

#### Table: `products`
Base commercial goods and service catalog items.
```sql
CREATE TABLE products (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    product_type VARCHAR(50) NOT NULL DEFAULT 'SERVICE', -- 'SERVICE', 'SOFTWARE', 'PHYSICAL'
    sku VARCHAR(100) NULL,
    description TEXT NULL,
    sales_price NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    cost_price NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT uq_products_sku UNIQUE (sku),
    CONSTRAINT ck_products_sales_price CHECK (sales_price >= 0),
    CONSTRAINT ck_products_cost_price CHECK (cost_price >= 0)
);
CREATE INDEX ix_products_name ON products (name);
CREATE INDEX ix_products_is_active ON products (is_active);
```

#### Table: `product_variants`
Product options and adjustments (e.g., Enterprise Tier, Extra Seat, High Bandwidth).
```sql
CREATE TABLE product_variants (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_id BIGINT NOT NULL,
    variant_name VARCHAR(100) NOT NULL, -- e.g. "Edition", "Seats Tier"
    variant_value VARCHAR(100) NOT NULL, -- e.g. "Enterprise", "50 Users"
    sku_suffix VARCHAR(50) NULL,
    price_adjustment NUMERIC(12, 2) NOT NULL DEFAULT 0.00, -- added to base product sales price
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_product_variants_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    CONSTRAINT uq_product_variant_option UNIQUE (product_id, variant_name, variant_value)
);
CREATE INDEX ix_product_variants_product_id ON product_variants (product_id);
```

#### Table: `tax_rates`
Jurisdictional tax rules.
```sql
CREATE TABLE tax_rates (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL, -- e.g. "GST 18%", "VAT 20%", "State Tax 5%"
    rate_percentage NUMERIC(5, 2) NOT NULL, -- e.g. 18.00 for 18%
    tax_type VARCHAR(50) NOT NULL DEFAULT 'EXCLUSIVE', -- 'EXCLUSIVE', 'INCLUSIVE'
    description VARCHAR(255) NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT ck_tax_rates_rate CHECK (rate_percentage >= 0 AND rate_percentage <= 100),
    CONSTRAINT ck_tax_rates_type CHECK (tax_type IN ('EXCLUSIVE', 'INCLUSIVE'))
);
CREATE INDEX ix_tax_rates_is_active ON tax_rates (is_active);
```

#### Table: `plans`
Recurring billing plans and lifecycle frequencies.
```sql
CREATE TABLE plans (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    code VARCHAR(50) NOT NULL, -- e.g. "SaaS-MONTHLY", "SaaS-ANNUAL"
    description TEXT NULL,
    billing_interval VARCHAR(20) NOT NULL, -- 'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'
    interval_count INTEGER NOT NULL DEFAULT 1, -- e.g., 1 for every month, 3 for quarterly
    trial_period_days INTEGER NOT NULL DEFAULT 0,
    minimum_quantity INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT uq_plans_code UNIQUE (code),
    CONSTRAINT ck_plans_interval CHECK (billing_interval IN ('DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY')),
    CONSTRAINT ck_plans_interval_count CHECK (interval_count >= 1),
    CONSTRAINT ck_plans_min_qty CHECK (minimum_quantity >= 1),
    CONSTRAINT ck_plans_trial CHECK (trial_period_days >= 0)
);
CREATE INDEX ix_plans_is_active ON plans (is_active);
CREATE INDEX ix_plans_interval ON plans (billing_interval);
```

#### Table: `plan_items`
Association of catalog products/variants bundled into a recurring plan.
```sql
CREATE TABLE plan_items (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plan_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price NUMERIC(12, 2) NOT NULL, -- overridden plan price or product sales price
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_plan_items_plan FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE,
    CONSTRAINT fk_plan_items_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    CONSTRAINT fk_plan_items_variant FOREIGN KEY (product_variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT,
    CONSTRAINT ck_plan_items_quantity CHECK (quantity >= 1),
    CONSTRAINT ck_plan_items_price CHECK (unit_price >= 0)
);
CREATE INDEX ix_plan_items_plan_id ON plan_items (plan_id);
```

---

### 2.3 Quotation Engine

#### Table: `quotation_templates`
Predefined quote blueprints with standard item packages and validity windows.
```sql
CREATE TABLE quotation_templates (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NULL,
    default_validity_days INTEGER NOT NULL DEFAULT 30,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT ck_quotation_templates_validity CHECK (default_validity_days >= 1)
);
```

#### Table: `quotations`
Commercial proposals issued to customers.
```sql
CREATE TABLE quotations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    quotation_number VARCHAR(50) NOT NULL,
    customer_id BIGINT NOT NULL,
    template_id BIGINT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'SENT', 'CONFIRMED', 'CANCELLED', 'EXPIRED'
    issue_date DATE NOT NULL,
    expiration_date DATE NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    is_converted BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT uq_quotations_number UNIQUE (quotation_number),
    CONSTRAINT fk_quotations_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    CONSTRAINT fk_quotations_template FOREIGN KEY (template_id) REFERENCES quotation_templates(id) ON DELETE SET NULL,
    CONSTRAINT ck_quotations_status CHECK (status IN ('DRAFT', 'SENT', 'CONFIRMED', 'CANCELLED', 'EXPIRED')),
    CONSTRAINT ck_quotations_dates CHECK (expiration_date >= issue_date),
    CONSTRAINT ck_quotations_totals CHECK (subtotal >= 0 AND discount_amount >= 0 AND tax_amount >= 0 AND total_amount >= 0)
);
CREATE INDEX ix_quotations_customer_id ON quotations (customer_id);
CREATE INDEX ix_quotations_status ON quotations (status);
CREATE INDEX ix_quotations_expiration_date ON quotations (expiration_date);
```

#### Table: `quotation_lines`
Individual line items with frozen price and tax snapshots.
```sql
CREATE TABLE quotation_lines (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    quotation_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT NULL,
    plan_id BIGINT NULL,
    description_snapshot VARCHAR(500) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price_snapshot NUMERIC(12, 2) NOT NULL,
    discount_rate NUMERIC(5, 2) NOT NULL DEFAULT 0.00, -- percentage discount on line
    tax_rate_id BIGINT NULL,
    tax_rate_snapshot NUMERIC(5, 2) NOT NULL DEFAULT 0.00, -- e.g. 18.00%
    line_subtotal NUMERIC(12, 2) NOT NULL,
    line_tax NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    line_total NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_quotation_lines_quotation FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE,
    CONSTRAINT fk_quotation_lines_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    CONSTRAINT fk_quotation_lines_variant FOREIGN KEY (product_variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT,
    CONSTRAINT fk_quotation_lines_plan FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE RESTRICT,
    CONSTRAINT fk_quotation_lines_tax FOREIGN KEY (tax_rate_id) REFERENCES tax_rates(id) ON DELETE SET NULL,
    CONSTRAINT ck_quotation_lines_quantity CHECK (quantity >= 1),
    CONSTRAINT ck_quotation_lines_amounts CHECK (unit_price_snapshot >= 0 AND line_subtotal >= 0 AND line_total >= 0)
);
CREATE INDEX ix_quotation_lines_quotation_id ON quotation_lines (quotation_id);
```

---

### 2.4 Subscriptions & Lifecycle

#### Table: `subscriptions`
Active recurring contractual commitments.
```sql
CREATE TABLE subscriptions (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subscription_number VARCHAR(50) NOT NULL,
    customer_id BIGINT NOT NULL,
    plan_id BIGINT NOT NULL,
    originating_quotation_id BIGINT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'ACTIVE', 'PAUSED', 'CLOSED'
    start_date DATE NOT NULL,
    end_date DATE NULL, -- NULL implies perpetual auto-renewing contract
    billing_anchor_day INTEGER NOT NULL, -- 1 to 31
    next_billing_date DATE NOT NULL,
    payment_terms_days INTEGER NOT NULL DEFAULT 15, -- Net 15 days
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    recurring_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    auto_close_reason VARCHAR(255) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT uq_subscriptions_number UNIQUE (subscription_number),
    CONSTRAINT fk_subscriptions_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    CONSTRAINT fk_subscriptions_plan FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE RESTRICT,
    CONSTRAINT fk_subscriptions_quotation FOREIGN KEY (originating_quotation_id) REFERENCES quotations(id) ON DELETE SET NULL,
    CONSTRAINT ck_subscriptions_status CHECK (status IN ('DRAFT', 'ACTIVE', 'PAUSED', 'CLOSED')),
    CONSTRAINT ck_subscriptions_anchor CHECK (billing_anchor_day BETWEEN 1 AND 31),
    CONSTRAINT ck_subscriptions_dates CHECK (end_date IS NULL OR end_date >= start_date),
    CONSTRAINT ck_subscriptions_recurring CHECK (recurring_amount >= 0)
);
CREATE INDEX ix_subscriptions_customer_id ON subscriptions (customer_id);
CREATE INDEX ix_subscriptions_plan_id ON subscriptions (plan_id);
CREATE INDEX ix_subscriptions_status_billing_date ON subscriptions (status, next_billing_date);
CREATE INDEX ix_subscriptions_originating_quote ON subscriptions (originating_quotation_id);
```

#### Table: `subscription_lines`
Recurring product items attached to the subscription.
```sql
CREATE TABLE subscription_lines (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subscription_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    product_variant_id BIGINT NULL,
    description_snapshot VARCHAR(500) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price_snapshot NUMERIC(12, 2) NOT NULL,
    tax_rate_id BIGINT NULL,
    tax_rate_snapshot NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_subscription_lines_sub FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE,
    CONSTRAINT fk_subscription_lines_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
    CONSTRAINT fk_subscription_lines_variant FOREIGN KEY (product_variant_id) REFERENCES product_variants(id) ON DELETE RESTRICT,
    CONSTRAINT fk_subscription_lines_tax FOREIGN KEY (tax_rate_id) REFERENCES tax_rates(id) ON DELETE SET NULL,
    CONSTRAINT ck_sub_lines_quantity CHECK (quantity >= 1),
    CONSTRAINT ck_sub_lines_price CHECK (unit_price_snapshot >= 0)
);
CREATE INDEX ix_subscription_lines_sub_id ON subscription_lines (subscription_id);
```

#### Table: `subscription_events`
Dedicated lifecycle transition timeline for subscriptions.
```sql
CREATE TABLE subscription_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    subscription_id BIGINT NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- 'CREATED', 'ACTIVATED', 'PAUSED', 'RESUMED', 'RENEWED', 'CLOSED'
    actor_user_id BIGINT NULL,
    from_status VARCHAR(20) NULL,
    to_status VARCHAR(20) NOT NULL,
    reason VARCHAR(255) NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_sub_events_sub FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE CASCADE,
    CONSTRAINT fk_sub_events_actor FOREIGN KEY (actor_user_id) REFERENCES users(id) ON DELETE SET NULL
);
CREATE INDEX ix_subscription_events_sub_id ON subscription_events (subscription_id);
```

---

### 2.5 Discounts Engine

#### Table: `discounts`
Promotional codes, percentage discounts, and fixed credits.
```sql
CREATE TABLE discounts (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code VARCHAR(50) NOT NULL, -- e.g. "SUMMER20", "FOUNDER50"
    name VARCHAR(255) NOT NULL,
    discount_type VARCHAR(20) NOT NULL, -- 'PERCENTAGE', 'FIXED_AMOUNT'
    discount_value NUMERIC(12, 2) NOT NULL, -- 20.00 for 20% or 50.00 for $50 fixed
    min_order_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    max_uses_total INTEGER NULL, -- NULL implies unlimited
    uses_count INTEGER NOT NULL DEFAULT 0,
    max_uses_per_customer INTEGER NOT NULL DEFAULT 1,
    start_date DATE NOT NULL,
    end_date DATE NULL, -- NULL implies no expiration
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT uq_discounts_code UNIQUE (code),
    CONSTRAINT ck_discounts_type CHECK (discount_type IN ('PERCENTAGE', 'FIXED_AMOUNT')),
    CONSTRAINT ck_discounts_value CHECK (
        (discount_type = 'PERCENTAGE' AND discount_value > 0 AND discount_value <= 100) OR
        (discount_type = 'FIXED_AMOUNT' AND discount_value > 0)
    ),
    CONSTRAINT ck_discounts_dates CHECK (end_date IS NULL OR end_date >= start_date)
);
CREATE INDEX ix_discounts_code ON discounts (code);
CREATE INDEX ix_discounts_is_active ON discounts (is_active);
```

#### Table: `discount_applications`
Transactional tracking of applied discounts against customer invoices.
```sql
CREATE TABLE discount_applications (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    discount_id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    invoice_id BIGINT NOT NULL,
    applied_amount NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_discount_apps_discount FOREIGN KEY (discount_id) REFERENCES discounts(id) ON DELETE RESTRICT,
    CONSTRAINT fk_discount_apps_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    CONSTRAINT fk_discount_apps_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    CONSTRAINT ck_discount_apps_amount CHECK (applied_amount > 0)
);
CREATE INDEX ix_discount_apps_customer ON discount_applications (discount_id, customer_id);
```

---

### 2.6 Billing, Invoices & Payment Allocations

#### Table: `invoices`
Authoritative billing documents generated on recurring cycles or confirmed manually.
```sql
CREATE TABLE invoices (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_number VARCHAR(50) NOT NULL,
    customer_id BIGINT NOT NULL,
    subscription_id BIGINT NULL, -- NULL for one-off manual invoices
    billing_period_start DATE NULL,
    billing_period_end DATE NULL,
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT', -- 'DRAFT', 'CONFIRMED', 'PAID', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED'
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    subtotal NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    total_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    amount_paid NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    balance_due NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    pdf_generated_at TIMESTAMP WITH TIME ZONE NULL,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT uq_invoices_number UNIQUE (invoice_number),
    CONSTRAINT fk_invoices_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    CONSTRAINT fk_invoices_subscription FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE RESTRICT,
    CONSTRAINT ck_invoices_status CHECK (status IN ('DRAFT', 'CONFIRMED', 'PAID', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED')),
    CONSTRAINT ck_invoices_dates CHECK (due_date >= issue_date),
    CONSTRAINT ck_invoices_period CHECK (billing_period_start IS NULL OR (billing_period_end >= billing_period_start)),
    CONSTRAINT ck_invoices_amounts CHECK (
        subtotal >= 0 AND 
        discount_amount >= 0 AND 
        tax_amount >= 0 AND 
        total_amount >= 0 AND 
        amount_paid >= 0 AND 
        balance_due >= 0 AND
        amount_paid <= total_amount AND
        balance_due = (total_amount - amount_paid)
    ),
    -- Idempotency constraint preventing double-billing on recurring cycles
    CONSTRAINT uq_subscription_billing_period UNIQUE (subscription_id, billing_period_start, billing_period_end)
);
CREATE INDEX ix_invoices_customer_id ON invoices (customer_id);
CREATE INDEX ix_invoices_subscription_id ON invoices (subscription_id);
CREATE INDEX ix_invoices_status_due_date ON invoices (status, due_date);
CREATE INDEX ix_invoices_issue_date ON invoices (issue_date);
```

#### Table: `invoice_lines`
Itemized lines capturing subscription source and financial breakdown.
```sql
CREATE TABLE invoice_lines (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    invoice_id BIGINT NOT NULL,
    subscription_line_id BIGINT NULL,
    description_snapshot VARCHAR(500) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    unit_price_snapshot NUMERIC(12, 2) NOT NULL,
    discount_amount NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    tax_rate_snapshot NUMERIC(5, 2) NOT NULL DEFAULT 0.00,
    line_subtotal NUMERIC(12, 2) NOT NULL,
    line_tax NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    line_total NUMERIC(12, 2) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_invoice_lines_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    CONSTRAINT fk_invoice_lines_sub_line FOREIGN KEY (subscription_line_id) REFERENCES subscription_lines(id) ON DELETE SET NULL,
    CONSTRAINT ck_invoice_lines_quantity CHECK (quantity >= 1),
    CONSTRAINT ck_invoice_lines_amounts CHECK (unit_price_snapshot >= 0 AND line_subtotal >= 0 AND line_total >= 0)
);
CREATE INDEX ix_invoice_lines_invoice_id ON invoice_lines (invoice_id);
```

#### Table: `payments`
Recorded customer payment receipts.
```sql
CREATE TABLE payments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_number VARCHAR(50) NOT NULL,
    customer_id BIGINT NOT NULL,
    payment_method VARCHAR(50) NOT NULL, -- 'BANK_TRANSFER', 'CHEQUE', 'CASH', 'MANUAL_OTHER'
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    paid_at DATE NOT NULL,
    transaction_reference VARCHAR(100) NULL, -- UTR / Cheque No / Bank Ref
    notes TEXT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'SUCCESS', -- 'SUCCESS', 'CANCELLED'
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT uq_payments_number UNIQUE (payment_number),
    CONSTRAINT fk_payments_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE RESTRICT,
    CONSTRAINT ck_payments_amount CHECK (amount > 0),
    CONSTRAINT ck_payments_status CHECK (status IN ('SUCCESS', 'CANCELLED')),
    CONSTRAINT ck_payments_method CHECK (payment_method IN ('BANK_TRANSFER', 'CHEQUE', 'CASH', 'MANUAL_OTHER'))
);
CREATE INDEX ix_payments_customer_id ON payments (customer_id);
CREATE INDEX ix_payments_paid_at ON payments (paid_at);
```

#### Table: `payment_allocations`
Cross-table mapping connecting payment receipts to one or more invoices.
```sql
CREATE TABLE payment_allocations (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    payment_id BIGINT NOT NULL,
    invoice_id BIGINT NOT NULL,
    allocated_amount NUMERIC(12, 2) NOT NULL,
    allocated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
    CONSTRAINT fk_payment_allocs_payment FOREIGN KEY (payment_id) REFERENCES payments(id) ON DELETE RESTRICT,
    CONSTRAINT fk_payment_allocs_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE RESTRICT,
    CONSTRAINT ck_payment_allocs_amount CHECK (allocated_amount > 0)
);
CREATE INDEX ix_payment_allocs_payment_id ON payment_allocations (payment_id);
CREATE INDEX ix_payment_allocs_invoice_id ON payment_allocations (invoice_id);
```

---

## 3. Mathematical & Business Invariants

### 3.1 Pricing & Tax Formula (Tax-Exclusive Convention)
Let a line have quantity $Q$, unit price $P$, line discount rate $D_{\%}$, and tax rate $T_{\%}$:
$$\text{Line Subtotal} = Q \times P$$
$$\text{Line Discount} = \text{round}\left(\text{Line Subtotal} \times \frac{D_{\%}}{100}, 2\right)$$
$$\text{Taxable Amount} = \text{Line Subtotal} - \text{Line Discount}$$
$$\text{Line Tax} = \text{round}\left(\text{Taxable Amount} \times \frac{T_{\%}}{100}, 2\right)$$
$$\text{Line Total} = \text{Taxable Amount} + \text{Line Tax}$$

For the invoice aggregate:
$$\text{Subtotal} = \sum \text{Line Subtotal}$$
$$\text{Total Discount} = \text{Document-level Discount} + \sum \text{Line Discount}$$
$$\text{Total Tax} = \sum \text{Line Tax}$$
$$\text{Total Amount} = \text{Subtotal} - \text{Total Discount} + \text{Total Tax}$$

### 3.2 Payment Allocation & Status Reconciliation Invariants
For any payment $p$:
$$\sum_{\text{allocations}} \text{allocated\_amount} \le p.\text{amount}$$

For any invoice $i$:
$$i.\text{amount\_paid} = \sum_{\text{allocations}} \text{allocated\_amount}$$
$$i.\text{balance\_due} = i.\text{total\_amount} - i.\text{amount\_paid}$$

Invoice status is updated transactionally upon allocation:
- If $i.\text{amount\_paid} = 0$ and $\text{current\_date} \le i.\text{due\_date} \implies \text{CONFIRMED}$
- If $i.\text{amount\_paid} = 0$ and $\text{current\_date} > i.\text{due\_date} \implies \text{OVERDUE}$
- If $0 < i.\text{amount\_paid} < i.\text{total\_amount}$ and $\text{current\_date} \le i.\text{due\_date} \implies \text{PARTIALLY\_PAID}$
- If $0 < i.\text{amount\_paid} < i.\text{total\_amount}$ and $\text{current\_date} > i.\text{due\_date} \implies \text{OVERDUE}$
- If $i.\text{amount\_paid} = i.\text{total\_amount} \implies \text{PAID}$
