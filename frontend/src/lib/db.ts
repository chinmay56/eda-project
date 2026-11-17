import { Pool } from "pg";

let pool: Pool | null = null;

export function getDbPool(): Pool {
  if (!pool) {
    pool = new Pool({
      host: process.env.DB_HOST || "localhost",
      port: parseInt(process.env.DB_PORT || "5432", 10),
      database: process.env.DB_NAME || "student_performance_db",
      user: process.env.DB_USER || "postgres",
      password: process.env.DB_PASSWORD || "Chinmay@989081",
      max: 10,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
  }
  return pool;
}

export async function queryDb<T = any>(text: string, params: any[] = []): Promise<T[]> {
  const p = getDbPool();
  const res = await p.query(text, params);
  return res.rows;
}
