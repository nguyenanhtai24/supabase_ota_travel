from contextlib import contextmanager
from psycopg2.pool import ThreadedConnectionPool
from app.config import DATABASE_URL

if not DATABASE_URL or "YOUR_PASSWORD_HERE" in DATABASE_URL:
    raise ValueError("Lỗi: DATABASE_URL chưa được cấu hình đúng trong file .env")

# Khởi tạo ThreadedConnectionPool để quản lý đa luồng kết nối tới Supabase
try:
    connection_pool = ThreadedConnectionPool(
        minconn=1,
        maxconn=20,
        dsn=DATABASE_URL,
        sslmode="require"  # Đảm bảo kết nối an toàn SSL đến Supabase
    )
    print("Database Connection Pool đã được khởi tạo thành công!")
except Exception as e:
    print(f"Lỗi khởi tạo Database Connection Pool: {e}")
    raise e

@contextmanager
def get_db_connection():
    """Context manager để lấy và trả lại connection từ pool."""
    connection = None
    try:
        connection = connection_pool.getconn()
        yield connection
    finally:
        if connection:
            connection_pool.putconn(connection)

@contextmanager
def get_db_cursor(commit=False):
    """Context manager để lấy cursor thực thi truy vấn và tự động commit/rollback."""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
