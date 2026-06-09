from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.database import get_db_connection
from app.helpers import clean_param, clean_row
from app.routers.common import paginated_response, pagination_params, require_hotel_exists

router = APIRouter()


PLACE_SELECT = """
    SELECT np.id, np.hotel_id, np.name, np.type, np.category_id, pc.name AS category_name,
           np.distance_km, h.name AS hotel_name, h.city AS hotel_city, h.area AS hotel_area
    FROM nearby_places np
    JOIN hotels h ON h.id = np.hotel_id
    LEFT JOIN place_categories pc ON pc.id = np.category_id
"""


@router.get("/api/hotels/{hotel_id}/nearby-places", tags=["Nearby Places"])
def list_hotel_nearby_places(
    hotel_id: int,
    type: Optional[str] = Query(None, description="Lọc theo type của nearby_places."),
    category_id: Optional[int] = Query(None),
    distance_max_km: Optional[float] = Query(None, ge=0),
):
    """Lấy địa điểm lân cận của khách sạn, bao phủ `nearby_places` và tên `place_categories`."""
    require_hotel_exists(hotel_id)
    clauses = ["np.hotel_id = %s"]
    params = [hotel_id]
    place_type = clean_param(type)
    if place_type:
        clauses.append("np.type ILIKE %s")
        params.append(f"%{place_type}%")
    if category_id is not None:
        clauses.append("np.category_id = %s")
        params.append(category_id)
    if distance_max_km is not None:
        clauses.append("np.distance_km <= %s")
        params.append(distance_max_km)
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"{PLACE_SELECT} WHERE {' AND '.join(clauses)} ORDER BY np.distance_km ASC NULLS LAST, np.id ASC", tuple(params))
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"hotel_id": hotel_id, "nearby_places": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/nearby-places", tags=["Nearby Places"])
def list_nearby_places(
    city: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    distance_max_km: Optional[float] = Query(None, ge=0),
    page_limit: tuple[int, int, int] = Depends(pagination_params),
):
    """Tìm địa điểm lân cận toàn hệ thống."""
    page, limit, offset = page_limit
    clauses = []
    params = []
    for clause, value in [("h.city ILIKE %s", city), ("np.name ILIKE %s", name), ("np.type ILIKE %s", type)]:
        cleaned = clean_param(value)
        if cleaned:
            clauses.append(clause)
            params.append(f"%{cleaned}%")
    if category_id is not None:
        clauses.append("np.category_id = %s")
        params.append(category_id)
    if distance_max_km is not None:
        clauses.append("np.distance_km <= %s")
        params.append(distance_max_km)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM nearby_places np JOIN hotels h ON h.id = np.hotel_id {where_sql}", tuple(params))
                total = cur.fetchone()["count"]
                cur.execute(f"{PLACE_SELECT} {where_sql} ORDER BY np.distance_km ASC NULLS LAST, np.id ASC LIMIT %s OFFSET %s", tuple(params + [limit, offset]))
                rows = [clean_row(row) for row in cur.fetchall()]
        return paginated_response(total, page, limit, rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/place-categories", tags=["Nearby Places"])
def list_place_categories():
    """Lấy toàn bộ trường của `place_categories`."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name FROM place_categories ORDER BY name")
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"data": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

