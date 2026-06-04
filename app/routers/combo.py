from typing import Optional, List, Any
from fastapi import APIRouter, HTTPException, Query
from psycopg2.extras import RealDictCursor
from app.database import get_db_connection

router = APIRouter()

# 13. GET /api/hotels/combo-suggest
@router.get("/api/hotels/combo-suggest", tags=["Combo"])
def get_combo_suggest(
    city: str,
    budget_total: float,
    guests: int = 2,
    nights: int = 2,
    suitable_for: Optional[str] = None,
    min_occupancy: Optional[int] = None
):
    """Gợi ý combo khách sạn + hoạt động phù hợp ngân sách."""
    try:
        hotel_nights = max(1, nights - 1)

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                hotel_sql = "SELECT * FROM hotels WHERE city ILIKE %s"
                hotel_params: List[Any] = [city]

                if suitable_for:
                    hotel_params.append([suitable_for.strip()])
                    hotel_sql += " AND suitable_for @> %s::text[]"

                cur.execute(hotel_sql, tuple(hotel_params))
                hotels_list = cur.fetchall()

                suggestions = []
                for hotel in hotels_list:
                    occupancy_need = min_occupancy if min_occupancy is not None else guests
                    cur.execute(
                        "SELECT * FROM rooms WHERE hotel_id = %s AND max_occupancy >= %s ORDER BY price ASC LIMIT 1",
                        (hotel["id"], occupancy_need)
                    )
                    room = cur.fetchone()
                    if not room or room["price"] is None:
                        continue

                    room_cost = float(room["price"]) * hotel_nights
                    if room_cost > budget_total:
                        continue

                    cur.execute(
                        "SELECT * FROM activities WHERE hotel_id = %s ORDER BY review_score DESC",
                        (hotel["id"],)
                    )
                    activities = cur.fetchall()

                    selected_acts = []
                    total_act_cost = 0.0
                    for act in activities:
                        act_cost = float(act["price_amount"]) * guests
                        if room_cost + total_act_cost + act_cost <= budget_total:
                            selected_acts.append(act)
                            total_act_cost += act_cost
                            if len(selected_acts) >= 3:
                                break

                    total_cost = room_cost + total_act_cost
                    suggestions.append({
                        "hotel": {
                            "id": hotel["id"],
                            "name": hotel["name"],
                            "star_rating": float(hotel["star_rating"]) if hotel["star_rating"] else None,
                            "review_score": float(hotel["review_score"]) if hotel["review_score"] else None,
                            "suitable_for": hotel["suitable_for"],
                            "recommended_room": {
                                "name": room["name"],
                                "price": float(room["price"]),
                                "max_occupancy": room["max_occupancy"]
                            }
                        },
                        "activities": [
                            {
                                "id": a["id"],
                                "title": a["title"],
                                "description": a["description"],
                                "price_amount": float(a["price_amount"]),
                                "review_score": float(a["review_score"]) if a["review_score"] else None
                            } for a in selected_acts
                        ],
                        "total_cost": total_cost,
                        "remaining_budget": round(budget_total - total_cost, 2)
                    })

        if not suggestions:
            raise HTTPException(status_code=404, detail="Không tìm thấy combo nào phù hợp ngân sách của bạn.")

        suggestions.sort(key=lambda x: x["hotel"]["review_score"] or 0, reverse=True)
        return suggestions[0]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 12. GET /api/hotels/{id}/combo — Tạo gói combo cho khách sạn
@router.get("/api/hotels/{id}/combo", tags=["Combo"])
def get_hotel_combo(
    id: int,
    nights: int = 3,
    guests: int = 2,
    include_activities: bool = True
):
    """Tạo gợi ý gói combo khách sạn kèm hoạt động, tính tổng chi phí ước tính."""
    try:
        hotel_nights = max(1, nights - 1)

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, name, star_rating, review_score FROM hotels WHERE id = %s",
                    (id,)
                )
                hotel = cur.fetchone()
                if not hotel:
                    raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")

                cur.execute(
                    "SELECT name, price, room_view FROM rooms WHERE hotel_id = %s ORDER BY price ASC LIMIT 1",
                    (id,)
                )
                room = cur.fetchone()
                if not room:
                    raise HTTPException(status_code=404, detail="Khách sạn này chưa có dữ liệu phòng.")

                activities_list = []
                activities_cost = 0.0
                if include_activities:
                    cur.execute(
                        "SELECT id, title, price_amount, review_score FROM activities WHERE hotel_id = %s ORDER BY review_score DESC LIMIT 3",
                        (id,)
                    )
                    activities_list = cur.fetchall()
                    activities_cost = sum(float(a["price_amount"]) for a in activities_list) * guests

        room_cost = float(room["price"]) * hotel_nights
        estimated_total = room_cost + activities_cost

        return {
            "hotel": {
                "id": hotel["id"],
                "name": hotel["name"],
                "star_rating": float(hotel["star_rating"]) if hotel["star_rating"] else None,
                "review_score": float(hotel["review_score"]) if hotel["review_score"] else None,
                "recommended_room": {
                    "name": room["name"],
                    "price": float(room["price"]),
                    "room_view": room["room_view"]
                }
            },
            "activities": [
                {
                    "id": a["id"],
                    "title": a["title"],
                    "price_amount": float(a["price_amount"]),
                    "review_score": float(a["review_score"]) if a["review_score"] else None
                } for a in activities_list
            ],
            "estimated_total": round(estimated_total, 2)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
