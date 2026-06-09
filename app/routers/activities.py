from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.database import get_db_connection
from app.helpers import clean_param, clean_row
from app.routers.common import paginated_response, pagination_params, require_hotel_exists

router = APIRouter()


ACTIVITY_SELECT = """
    SELECT a.id, a.hotel_id, a.activity_id, a.title, a.description, a.price_amount,
           a.review_score, h.name AS hotel_name, h.city AS hotel_city, h.area AS hotel_area,
           h.country AS hotel_country
    FROM activities a
    JOIN hotels h ON h.id = a.hotel_id
"""


@router.get("/api/hotels/{hotel_id}/activities", tags=["Activities"])
def list_hotel_activities(
    hotel_id: int,
    price_max: Optional[float] = Query(None, ge=0),
    review_score_min: Optional[float] = Query(None, ge=0, le=10),
    sort_by: Optional[str] = Query(None, description="id:asc | price:asc | price:desc | review_score:desc"),
):
    """Lấy hoạt động của một khách sạn, bao phủ toàn bộ trường của `activities`."""
    require_hotel_exists(hotel_id)
    clauses = ["a.hotel_id = %s"]
    params = [hotel_id]
    if price_max is not None:
        clauses.append("a.price_amount <= %s")
        params.append(price_max)
    if review_score_min is not None:
        clauses.append("a.review_score >= %s")
        params.append(review_score_min)
    order_sql = _activity_order(sort_by)
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"{ACTIVITY_SELECT} WHERE {' AND '.join(clauses)} {order_sql}", tuple(params))
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"hotel_id": hotel_id, "activities": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/activities", tags=["Activities"])
def list_activities(
    city: Optional[str] = Query(None),
    hotel_id: Optional[int] = Query(None),
    title: Optional[str] = Query(None),
    price_max: Optional[float] = Query(None, ge=0),
    review_score_min: Optional[float] = Query(None, ge=0, le=10),
    sort_by: Optional[str] = Query(None, description="id:asc | price:asc | price:desc | review_score:desc"),
    page_limit: tuple[int, int, int] = Depends(pagination_params),
):
    """Tìm hoạt động toàn hệ thống, trả trường `activities` kèm thông tin khách sạn."""
    page, limit, offset = page_limit
    clauses = []
    params = []
    if hotel_id is not None:
        clauses.append("a.hotel_id = %s")
        params.append(hotel_id)
    for clause, value in [("h.city ILIKE %s", city), ("a.title ILIKE %s", title)]:
        cleaned = clean_param(value)
        if cleaned:
            clauses.append(clause)
            params.append(f"%{cleaned}%")
    if price_max is not None:
        clauses.append("a.price_amount <= %s")
        params.append(price_max)
    if review_score_min is not None:
        clauses.append("a.review_score >= %s")
        params.append(review_score_min)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order_sql = _activity_order(sort_by)
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM activities a JOIN hotels h ON h.id = a.hotel_id {where_sql}", tuple(params))
                total = cur.fetchone()["count"]
                cur.execute(f"{ACTIVITY_SELECT} {where_sql} {order_sql} LIMIT %s OFFSET %s", tuple(params + [limit, offset]))
                rows = [clean_row(row) for row in cur.fetchall()]
        return paginated_response(total, page, limit, rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/activities/{activity_row_id}", tags=["Activities"])
def get_activity(activity_row_id: int):
    """Lấy chi tiết một activity theo khóa chính `activities.id`."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"{ACTIVITY_SELECT} WHERE a.id = %s", (activity_row_id,))
                row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy hoạt động.")
        return clean_row(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _activity_order(sort_by: Optional[str]) -> str:
    value = clean_param(sort_by) or "id:asc"
    if value == "price:asc":
        return "ORDER BY a.price_amount ASC NULLS LAST, a.id ASC"
    if value == "price:desc":
        return "ORDER BY a.price_amount DESC NULLS LAST, a.id ASC"
    if value == "review_score:desc":
        return "ORDER BY a.review_score DESC NULLS LAST, a.id ASC"
    return "ORDER BY a.id ASC"

