from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Query
from psycopg2.extras import RealDictCursor
from app.database import get_db_connection
from app.helpers import clean_row, serialize_value

router = APIRouter()

# 7. GET /api/hotels/{id}/rooms — Danh sách phòng
@router.get("/api/hotels/{id}/rooms", tags=["Rooms"])
def get_hotel_rooms(
    id: int,
    min_occupancy: Optional[int] = None,
    room_view: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="price:asc | price:desc"),
    limit: int = 100
):
    """Lấy danh sách loại phòng của khách sạn. Hỗ trợ lọc theo số người, hướng view và giá."""
    try:
        where = ["hotel_id = %s"]
        params: List[Any] = [id]

        if min_occupancy is not None:
            params.append(min_occupancy)
            where.append("max_occupancy >= %s")

        if room_view:
            params.append(f"%{room_view}%")
            where.append("room_view ILIKE %s")

        order = "ORDER BY id ASC"
        if sort_by == "price:asc":
            order = "ORDER BY price ASC NULLS LAST"
        elif sort_by == "price:desc":
            order = "ORDER BY price DESC NULLS LAST"

        params.append(limit)
        sql = f"SELECT * FROM rooms WHERE {' AND '.join(where)} {order} LIMIT %s"

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                rooms = cur.fetchall()

        formatted = []
        for r in rooms:
            cleaned = clean_row(r)
            cleaned["room_type_id"] = str(r["room_type_id"]) if r["room_type_id"] else None
            cleaned["images"] = [r["images"][0]] if r["images"] else []
            formatted.append(cleaned)

        return {"hotel_id": id, "rooms": formatted}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 8. GET /api/rooms/{id} — Chi tiết một loại phòng
@router.get("/api/rooms/{id}", tags=["Rooms"])
def get_room(id: int):
    """Lấy chi tiết đầy đủ một loại phòng (diện tích, giường, view, tiện nghi, ảnh)."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM rooms WHERE id = %s", (id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy phòng.")

        cleaned = clean_row(row)
        cleaned["room_type_id"] = str(row["room_type_id"]) if row["room_type_id"] else None
        # Trả về toàn bộ ảnh phòng (khác với list, ở đây trả full)
        cleaned["images"] = serialize_value(row["images"]) or []
        return cleaned

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
