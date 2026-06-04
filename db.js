const { Pool } = require('pg');
require('dotenv').config();

const isProduction = process.env.DATABASE_URL && 
  !process.env.DATABASE_URL.includes('localhost') && 
  !process.env.DATABASE_URL.includes('127.0.0.1');

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  // Cấu hình SSL khi kết nối tới các dịch vụ cloud như Supabase để tránh lỗi từ chối bắt tay
  ssl: isProduction ? { rejectUnauthorized: false } : false,
});

module.exports = {
  query: (text, params) => pool.query(text, params),
  pool,
};
