-- Published views. These ARE the security boundary: a model can only ever see
-- the columns listed here, and only through these views.

-- Customers. The sensitive account_number never appears.
CREATE VIEW IF NOT EXISTS v_customers AS
SELECT id, name, region, manager_id
FROM customers;

-- Accounts. account_number is deliberately omitted from the view.
CREATE VIEW IF NOT EXISTS v_accounts AS
SELECT id, customer_id, account_type, balance
FROM accounts;

-- Aggregate by region. A model can answer "total balance by region" without
-- ever reading a raw account row.
CREATE VIEW IF NOT EXISTS v_balances_by_region AS
SELECT c.region               AS region,
       SUM(a.balance)         AS total_balance,
       COUNT(a.id)            AS account_count
FROM accounts a
JOIN customers c ON a.customer_id = c.id
GROUP BY c.region;
