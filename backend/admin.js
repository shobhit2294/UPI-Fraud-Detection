import pkg from "pg";
const { Pool } = pkg;

const pool = new Pool({
  host: "db",
  user: "upi_user",
  password: "upi_pass",
  database: "upi_fraud_db",
  port: 5432
});

/* ---------------- FRAUD TRANSACTIONS ---------------- */

export async function getFraudTransactions(req, res) {
  const result = await pool.query(
    "SELECT * FROM transactions WHERE status = 'FRAUD' ORDER BY created_at DESC"
  );
  res.json(result.rows);
}

/* ---------------- SUSPICIOUS TRANSACTIONS ---------------- */

export async function getSuspiciousTransactions(req, res) {
  const result = await pool.query(
    "SELECT * FROM transactions WHERE status = 'SUSPICIOUS' ORDER BY created_at DESC"
  );
  res.json(result.rows);
}

/* ---------------- USER TRANSACTIONS ---------------- */

export async function getUserTransactions(req, res) {
  const { userId } = req.params;

  const result = await pool.query(
    "SELECT * FROM transactions WHERE user_id = $1 ORDER BY created_at DESC",
    [userId]
  );

  res.json(result.rows);
}

/* ---------------- FRAUD STATISTICS ---------------- */

export async function getFraudStats(req, res) {
  const result = await pool.query(`
    SELECT
      COUNT(*) FILTER (WHERE status = 'FRAUD') AS fraud_count,
      COUNT(*) FILTER (WHERE status = 'SUSPICIOUS') AS suspicious_count,
      COUNT(*) AS total_transactions
    FROM transactions
  `);

  res.json(result.rows[0]);
}

