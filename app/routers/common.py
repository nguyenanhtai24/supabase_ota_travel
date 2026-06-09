from math import ceil
from typing import Any, Dict, List, Optional, Sequence, Tuple

from fastapi import HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.database import get_db_connection
from app.helpers import clean_param, clean_row


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


def pagination_params(
    page: int = Query(1, ge=1, description="Trang hiện tại, bắt đầu từ 1."),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Số bản ghi mỗi trang."),
) -> Tuple[int, int, int]:
    offset = (page - 1) * limit
    return page, limit, offset


def paginated_response(total: int, page: int, limit: int, data: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": ceil(total / limit) if limit else 0,
        "data": data,
    }


def fetch_one(sql: str, params: Sequence[Any] = ()) -> Optional[Dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, tuple(params))
            row = cur.fetchone()
    return clean_row(row)


def fetch_all(sql: str, params: Sequence[Any] = ()) -> List[Dict[str, Any]]:
    with get_db_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, tuple(params))
            rows = cur.fetchall()
    return [clean_row(row) for row in rows]


def require_hotel_exists(hotel_id: int) -> Dict[str, Any]:
    hotel = fetch_one("SELECT id, name FROM hotels WHERE id = %s", (hotel_id,))
    if not hotel:
        raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")
    return hotel


def csv_values(value: Optional[str]) -> List[str]:
    cleaned = clean_param(value)
    if not cleaned:
        return []
    return [item for item in (clean_param(part) for part in cleaned.split(",")) if item]

