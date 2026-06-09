from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.database import get_db_connection
from app.helpers import clean_param, clean_row
from app.routers.common import paginated_response, pagination_params, require_hotel_exists

router = APIRouter()


@router.get("/api/hotels/{hotel_id}/rooms", tags=["Rooms"])
def list_hotel_rooms(
    hotel_id: int,
    min_occupancy: Optional[int] = Query(None, ge=1),
    room_view: Optional[str] = Query(None, description="Lọc theo hướng/view phòng."),
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None, ge=0),
    sort_by: Optional[str] = Query(None, description="id:asc | price:asc | price:desc | review_score:desc"),
    page_limit: tuple[int, int, int] = Depends(pagination_params),
):
    """Lấy danh sách phòng của khách sạn, bao phủ toàn bộ trường của bảng `rooms`."""
    require_hotel_exists(hotel_id)
    page, limit, offset = page_limit
    sort_by = clean_param(sort_by) or "id:asc"
    clauses = ["hotel_id = %s"]
    params = [hotel_id]

    if min_occupancy is not None:
        clauses.append("max_occupancy >= %s")
        params.append(min_occupancy)
    view = clean_param(room_view)
    if view:
        clauses.append("room_view ILIKE %s")
        params.append(f"%{view}%")
    if price_min is not None:
        clauses.append("price >= %s")
        params.append(price_min)
    if price_max is not None:
        clauses.append("price <= %s")
        params.append(price_max)

    order_sql = "ORDER BY id ASC"
    if sort_by == "price:asc":
        order_sql = "ORDER BY price ASC NULLS LAST, id ASC"
    elif sort_by == "price:desc":
        order_sql = "ORDER BY price DESC NULLS LAST, id ASC"
    elif sort_by == "review_score:desc":
        order_sql = "ORDER BY review_score DESC NULLS LAST, id ASC"

    where_sql = " AND ".join(clauses)
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM rooms WHERE {where_sql}", tuple(params))
                total = cur.fetchone()["count"]
                cur.execute(f"SELECT * FROM rooms WHERE {where_sql} {order_sql} LIMIT %s OFFSET %s", tuple(params + [limit, offset]))
                rows = [clean_row(row) for row in cur.fetchall()]
        return paginated_response(total, page, limit, rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/rooms", tags=["Rooms"])
def list_rooms(
    hotel_id: Optional[int] = Query(None),
    city: Optional[str] = Query(None, description="Lọc phòng theo thành phố của khách sạn."),
    min_occupancy: Optional[int] = Query(None, ge=1),
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None, ge=0),
    sort_by: Optional[str] = Query(None, description="id:asc | price:asc | price:desc | review_score:desc"),
    page_limit: tuple[int, int, int] = Depends(pagination_params),
):
    """Tìm phòng toàn hệ thống, trả trường `rooms` kèm thông tin khách sạn ngắn."""
    page, limit, offset = page_limit
    sort_by = clean_param(sort_by) or "id:asc"
    clauses = []
    params = []

    if hotel_id is not None:
        clauses.append("r.hotel_id = %s")
        params.append(hotel_id)
    city_value = clean_param(city)
    if city_value:
        clauses.append("h.city ILIKE %s")
        params.append(f"%{city_value}%")
    if min_occupancy is not None:
        clauses.append("r.max_occupancy >= %s")
        params.append(min_occupancy)
    if price_min is not None:
        clauses.append("r.price >= %s")
        params.append(price_min)
    if price_max is not None:
        clauses.append("r.price <= %s")
        params.append(price_max)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    order_sql = "ORDER BY r.id ASC"
    if sort_by == "price:asc":
        order_sql = "ORDER BY r.price ASC NULLS LAST, r.id ASC"
    elif sort_by == "price:desc":
        order_sql = "ORDER BY r.price DESC NULLS LAST, r.id ASC"
    elif sort_by == "review_score:desc":
        order_sql = "ORDER BY r.review_score DESC NULLS LAST, r.id ASC"

    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM rooms r JOIN hotels h ON h.id = r.hotel_id {where_sql}", tuple(params))
                total = cur.fetchone()["count"]
                cur.execute(
                    f"""
                    SELECT r.*, h.name AS hotel_name, h.city AS hotel_city, h.area AS hotel_area, h.country AS hotel_country
                    FROM rooms r
                    JOIN hotels h ON h.id = r.hotel_id
                    {where_sql}
                    {order_sql}
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params + [limit, offset]),
                )
                rows = [clean_row(row) for row in cur.fetchall()]
        return paginated_response(total, page, limit, rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/rooms/{room_id}", tags=["Rooms"])
def get_room(room_id: int):
    """Lấy chi tiết một phòng, bao phủ toàn bộ trường của `rooms`."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT r.*, h.name AS hotel_name, h.city AS hotel_city, h.area AS hotel_area, h.country AS hotel_country
                    FROM rooms r
                    JOIN hotels h ON h.id = r.hotel_id
                    WHERE r.id = %s
                    """,
                    (room_id,),
                )
                row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy phòng.")
        return clean_row(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

