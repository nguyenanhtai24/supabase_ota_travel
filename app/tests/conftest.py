import pytest
from unittest.mock import MagicMock, patch

# Đặt biến môi trường test và mock ThreadedConnectionPool trước khi import app
import os
os.environ["DATABASE_URL"] = "postgresql://postgres:fake_pwd@fake_host:5432/postgres"
os.environ["API_SECRET_KEY"] = "ota_sk_test_token"

mock_pool = MagicMock()
with patch("psycopg2.pool.ThreadedConnectionPool", return_value=mock_pool):
    from app.main import app

from fastapi.testclient import TestClient

@pytest.fixture(scope="session")
def client():
    """Test client gửi request cho API."""
    with TestClient(app) as c:
        yield c

@pytest.fixture
def mock_db():
    """Mock get_db_connection và get_db_cursor để giả lập truy vấn SQL."""
    with patch("app.routers.hotels.get_db_connection") as mock_conn_hotels, \
         patch("app.routers.rooms.get_db_connection") as mock_conn_rooms, \
         patch("app.routers.places.get_db_connection") as mock_conn_places, \
         patch("app.routers.activities.get_db_connection") as mock_conn_activities, \
         patch("app.routers.combo.get_db_connection") as mock_conn_combo:
        
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        
        # Gắn cursor vào connection
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.__enter__.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        
        # Thiết lập context managers
        mock_conn_hotels.return_value.__enter__.return_value = mock_conn
        mock_conn_rooms.return_value.__enter__.return_value = mock_conn
        mock_conn_places.return_value.__enter__.return_value = mock_conn
        mock_conn_activities.return_value.__enter__.return_value = mock_conn
        mock_conn_combo.return_value.__enter__.return_value = mock_conn
        
        yield {
            "connection": mock_conn,
            "cursor": mock_cursor
        }
