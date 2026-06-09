from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.database import get_db_connection
from app.helpers import clean_param, clean_row

router = APIRouter()


@router.get("/api/hotels/{hotel_id}/combo", tags=["Combo"])
def get_hotel_combo(
    hotel_id: int,
    nights: int = Query(2, ge=1),
    guests: int = Query(2, ge=1),
    include_activities: bool = True,
):
    """Tạo gói combo từ phòng rẻ nhất đáp ứng số khách và tối đa 3 hoạt động điểm cao."""
    try:
        stay_nights = max(1, nights)
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM hotels WHERE id = %s", (hotel_id,))
                hotel = cur.fetchone()
                if not hotel:
                    raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")
                cur.execute(
                    "SELECT * FROM rooms WHERE hotel_id = %s AND COALESCE(max_occupancy, 0) >= %s ORDER BY price ASC NULLS LAST, id ASC LIMIT 1",
                    (hotel_id, guests),
                )
                room = cur.fetchone()
                if not room:
                    raise HTTPException(status_code=404, detail="Không tìm thấy phòng phù hợp số khách.")
                activities = []
                if include_activities:
                    cur.execute(
                        "SELECT * FROM activities WHERE hotel_id = %s ORDER BY review_score DESC NULLS LAST, price_amount ASC NULLS LAST LIMIT 3",
                        (hotel_id,),
                    )
                    activities = cur.fetchall()
        room_total = float(room["price"] or 0) * stay_nights
        activities_total = sum(float(activity["price_amount"] or 0) for activity in activities) * guests
        return {
            "hotel": clean_row(hotel),
            "room": clean_row(room),
            "nights": stay_nights,
            "guests": guests,
            "activities": [clean_row(activity) for activity in activities],
            "room_total": round(room_total, 2),
            "activities_total": round(activities_total, 2),
            "estimated_total": round(room_total + activities_total, 2),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/combo-suggest", tags=["Combo"])
def suggest_combo(
    city: str = Query(..., description="Thành phố muốn lưu trú."),
    budget_total: float = Query(..., ge=0),
    guests: int = Query(2, ge=1),
    nights: int = Query(2, ge=1),
    suitable_for: Optional[str] = Query(None, description="Tag trong hotel_suitability."),
    limit: int = Query(5, ge=1, le=20),
):
    """Gợi ý combo khách sạn + phòng + hoạt động theo ngân sách."""
    city_value = clean_param(city)
    suitable_value = clean_param(suitable_for)
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                params = [f"%{city_value}%"]
                suitable_clause = ""
                if suitable_value:
                    suitable_clause = "AND EXISTS (SELECT 1 FROM hotel_suitability hs WHERE hs.hotel_id = h.id AND hs.suitable_for_tag ILIKE %s)"
                    params.append(f"%{suitable_value}%")
                cur.execute(
                    f"""
                    SELECT h.*, r.id AS room_id, r.name AS room_name, r.price AS room_price,
                           r.max_occupancy, r.room_view, r.bed_type
                    FROM hotels h
                    JOIN LATERAL (
                        SELECT *
                        FROM rooms
                        WHERE rooms.hotel_id = h.id AND COALESCE(max_occupancy, 0) >= %s
                        ORDER BY price ASC NULLS LAST, id ASC
                        LIMIT 1
                    ) r ON true
                    WHERE h.city ILIKE %s
                    {suitable_clause}
                    ORDER BY h.review_score DESC NULLS LAST, r.price ASC NULLS LAST
                    LIMIT %s
                    """,
                    tuple([guests] + params + [limit]),
                )
                candidates = cur.fetchall()
                suggestions = []
                for candidate in candidates:
                    room_total = float(candidate["room_price"] or 0) * nights
                    if room_total > budget_total:
                        continue
                    cur.execute(
                        "SELECT * FROM activities WHERE hotel_id = %s ORDER BY review_score DESC NULLS LAST, price_amount ASC NULLS LAST",
                        (candidate["id"],),
                    )
                    selected = []
                    activity_total = 0.0
                    for activity in cur.fetchall():
                        price = float(activity["price_amount"] or 0) * guests
                        if room_total + activity_total + price <= budget_total:
                            selected.append(clean_row(activity))
                            activity_total += price
                        if len(selected) >= 3:
                            break
                    suggestions.append({
                        "hotel": clean_row(candidate),
                        "room": {
                            "id": candidate["room_id"],
                            "name": candidate["room_name"],
                            "price": float(candidate["room_price"] or 0),
                            "max_occupancy": candidate["max_occupancy"],
                            "room_view": candidate["room_view"],
                            "bed_type": candidate["bed_type"],
                        },
                        "activities": selected,
                        "room_total": round(room_total, 2),
                        "activities_total": round(activity_total, 2),
                        "estimated_total": round(room_total + activity_total, 2),
                        "remaining_budget": round(budget_total - room_total - activity_total, 2),
                    })
        if not suggestions:
            raise HTTPException(status_code=404, detail="Không tìm thấy combo phù hợp ngân sách.")
        return {"data": suggestions}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

