from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Query
from psycopg2.extras import RealDictCursor
from app.database import get_db_connection
from app.helpers import clean_row

router = APIRouter()

# 10. GET /api/hotels/{id}/activities — Hoạt động của khách sạn
@router.get("/api/hotels/{id}/activities", tags=["Activities"])
def get_hotel_activities(
    id: int,
    price_max: Optional[float] = None,
    sort_by: Optional[str] = Query(None, description="price:asc | review_score:desc"),
    limit: Optional[int] = None
):
    """Lấy danh sách hoạt động vui chơi liên kết với khách sạn. Hỗ trợ lọc theo giá và sắp xếp."""
    try:
        where = ["hotel_id = %s"]
        params: List[Any] = [id]

        if price_max is not None:
            params.append(price_max)
            where.append("price_amount <= %s")

        order = "ORDER BY id ASC"
        if sort_by == "price:asc":
            order = "ORDER BY price_amount ASC NULLS LAST"
        elif sort_by == "review_score:desc":
            order = "ORDER BY review_score DESC NULLS LAST"

        limit_clause = ""
        if limit is not None:
            params.append(limit)
            limit_clause = "LIMIT %s"

        sql = f"SELECT * FROM activities WHERE {' AND '.join(where)} {order} {limit_clause}"

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                acts = cur.fetchall()

        return {
            "hotel_id": id,
            "activities": [clean_row(a) for a in acts]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 11. GET /api/activities — Tìm hoạt động toàn hệ thống
@router.get("/api/activities", tags=["Activities"])
def get_activities(
    city: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="review_score:desc | price:asc"),
    limit: Optional[int] = None
):
    """Tìm kiếm hoạt động giải trí trên toàn hệ thống theo thành phố, điểm, giá."""
    try:
        where = []
        params: List[Any] = []

        if city:
            params.append(city)
            where.append("hotels.city ILIKE %s")

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""

        order = "ORDER BY activities.id ASC"
        if sort_by == "review_score:desc":
            order = "ORDER BY activities.review_score DESC NULLS LAST"
        elif sort_by == "price:asc":
            order = "ORDER BY activities.price_amount ASC NULLS LAST"

        limit_clause = ""
        if limit is not None:
            params.append(limit)
            limit_clause = "LIMIT %s"

        sql = f"""
            SELECT
                activities.id,
                activities.hotel_id,
                activities.title,
                activities.description,
                activities.price_amount,
                activities.review_score,
                hotels.name AS hotel_name,
                hotels.city AS hotel_city
            FROM activities
            JOIN hotels ON activities.hotel_id = hotels.id
            {where_sql}
            {order}
            {limit_clause}
        """

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                rows = cur.fetchall()

        data = []
        for r in rows:
            cleaned = clean_row(r)
            data.append({
                "id": cleaned["id"],
                "hotel_id": cleaned["hotel_id"],
                "title": cleaned["title"],
                "description": cleaned["description"],
                "price_amount": cleaned["price_amount"],
                "review_score": cleaned["review_score"],
                "hotel": {
                    "name": r["hotel_name"],
                    "city": r["hotel_city"]
                }
            })

        return {"data": data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
