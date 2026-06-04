from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException
from psycopg2.extras import RealDictCursor
from app.database import get_db_connection
from app.helpers import clean_row

router = APIRouter()

# 9. GET /api/hotels/{id}/nearby-places — Địa điểm lân cận
@router.get("/api/hotels/{id}/nearby-places", tags=["Nearby Places"])
def get_hotel_nearby_places(
    id: int,
    type: Optional[str] = None,
    distance_max_km: Optional[float] = None
):
    """Lấy danh sách địa điểm nổi bật gần khách sạn. Hỗ trợ lọc theo loại và bán kính (km)."""
    try:
        where = ["hotel_id = %s"]
        params: List[Any] = [id]

        if type:
            params.append(type)
            where.append("type ILIKE %s")

        if distance_max_km is not None:
            params.append(distance_max_km)
            where.append("distance_km <= %s")

        sql = f"SELECT * FROM nearby_places WHERE {' AND '.join(where)} ORDER BY distance_km ASC"

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                places = cur.fetchall()

        return {
            "hotel_id": id,
            "nearby_places": [clean_row(p) for p in places]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
