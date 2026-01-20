import pkg from "pg";
const { Pool } = pkg;

export const pool = new Pool({
  host: "db",
  user: "upi_user",
  password: "upi_pass",
  database: "upi_fraud_db",
  port: 5432
});
