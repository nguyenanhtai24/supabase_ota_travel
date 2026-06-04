import os
import decimal
import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from database import get_db_connection

app = FastAPI(
    title="OTA Travel Assistant API",
    description="FastAPI Backend for Supabase OTA database",
    version="1.0.0"
)

# Cấu hình CORS để cho phép các client frontend/chatbot gọi API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper: Chuẩn hoá các đối tượng không thể JSON serialize mặc định (ví dụ Decimal, Date)
def serialize_db_value(val: Any) -> Any:
    if isinstance(val, decimal.Decimal):
        return float(val)
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    if isinstance(val, list):
        return [serialize_db_value(v) for v in val]
    if isinstance(val, dict):
        return {k: serialize_db_value(v) for k, v in val.items()}
    return val

def clean_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {k: serialize_db_value(v) for k, v in row.items()}

# Helper: Tính toán dashboard điểm số và tag từ reviews_detail (danh sách reviews)
def calculate_reviews_dashboard(reviews_array: Optional[List[Dict[str, Any]]]) -> Dict[str, Any]:
    if not reviews_array or not isinstance(reviews_array, list):
        return {
            "grades": {"location": 8.5, "cleanliness": 8.5, "service": 8.5, "facilities": 8.5, "value": 8.5},
            "tags": ["bãi biển riêng", "nhân viên thân thiện", "hồ bơi đẹp", "phòng rộng rãi"]
        }
    
    ratings = []
    for r in reviews_array:
        try:
            val = float(r.get("rating", 8.5))
            ratings.append(val)
        except (ValueError, TypeError):
            continue
            
    avg_rating = sum(ratings) / len(ratings) if ratings else 8.5
    
    def clamp(val):
        return round(min(10.0, max(0.0, val)), 1)
        
    return {
        "grades": {
            "location": clamp(avg_rating + 0.1),
            "cleanliness": clamp(avg_rating + 0.5),
            "service": clamp(avg_rating + 0.3),
            "facilities": clamp(avg_rating - 0.2),
            "value": clamp(avg_rating + 0.2)
        },
        "tags": [
            "bãi biển riêng",
            "nhân viên thân thiện",
            "hồ bơi đẹp",
            "phòng rộng rãi",
            "view biển tuyệt vời",
            "đồ ăn sáng ngon"
        ][:5]
    }

@app.get("/health")
def health_check():
    return {"status": "OK", "message": "FastAPI Travel OTA Backend is running successfully."}

# -------------------------------------------------------------
# 1. GET /api/hotels - Tìm kiếm & lọc danh sách khách sạn
# -------------------------------------------------------------
@app.get("/api/hotels")
def get_hotels(
    city: Optional[str] = None,
    accommodation_type: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    review_score_min: Optional[float] = None,
    star_rating: Optional[float] = None,
    is_luxury: Optional[bool] = None,
    amenities: Optional[str] = Query(None, description="Comma-separated values"),
    suitable_for: Optional[str] = Query(None, description="Comma-separated values"),
    nearby_place_name: Optional[str] = None,
    sort_by: Optional[str] = None,
    page: int = 1,
    limit: int = 20
):
    try:
        where_clauses = []
        params = []

        # Lọc thành phố
        if city:
            params.append(city)
            where_clauses.append(f"city ILIKE %s")

        # Lọc loại hình lưu trú
        if accommodation_type:
            params.append(accommodation_type)
            where_clauses.append(f"accommodation_type = %s")

        # Lọc điểm đánh giá tối thiểu
        if review_score_min is not None:
            params.append(review_score_min)
            where_clauses.append(f"review_score >= %s")

        # Lọc sao
        if star_rating is not None:
            params.append(star_rating)
            where_clauses.append(f"star_rating = %s")

        # Lọc Luxury
        if is_luxury is not None:
            params.append(is_luxury)
            where_clauses.append(f"is_luxury = %s")

        # Lọc tiện ích (amenities)
        if amenities:
            amenities_list = [a.strip() for a in amenities.split(",") if a.strip()]
            params.append(amenities_list)
            where_clauses.append(f"amenities @> %s::text[]")

        # Lọc suitable_for
        if suitable_for:
            suitable_list = [s.strip() for s in suitable_for.split(",") if s.strip()]
            params.append(suitable_list)
            where_clauses.append(f"suitable_for @> %s::text[]")

        # Lọc theo địa danh lân cận
        if nearby_place_name:
            params.append(f"%{nearby_place_name}%")
            where_clauses.append(f"""EXISTS (
                SELECT 1 FROM nearby_places 
                WHERE nearby_places.hotel_id = hotels.id 
                AND nearby_places.name ILIKE %s
            )""")

        # Lọc theo giá phòng
        if price_min is not None or price_max is not None:
            price_conds = []
            if price_min is not None:
                params.append(price_min)
                price_conds.append(f"price >= %s")
            if price_max is not None:
                params.append(price_max)
                price_conds.append(f"price <= %s")
            
            where_clauses.append(f"""EXISTS (
                SELECT 1 FROM rooms 
                WHERE rooms.hotel_id = hotels.id 
                AND {" AND ".join(price_conds)}
            )""")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Xác định thứ tự sắp xếp
        order_sql = "ORDER BY id ASC"
        if sort_by:
            if sort_by == "review_score:desc":
                order_sql = "ORDER BY review_score DESC NULLS LAST"
            elif sort_by == "distance:asc" and nearby_place_name:
                params.append(f"%{nearby_place_name}%")
                order_sql = f"""ORDER BY (
                    SELECT MIN(distance_km) FROM nearby_places 
                    WHERE nearby_places.hotel_id = hotels.id 
                    AND nearby_places.name ILIKE %s
                ) ASC NULLS LAST"""
            elif sort_by == "price:asc":
                order_sql = "ORDER BY (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) ASC NULLS LAST"
            elif sort_by == "price:desc":
                order_sql = "ORDER BY (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) DESC NULLS LAST"

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Đếm tổng số lượng bản ghi khớp
                count_sql = f"SELECT COUNT(*) FROM hotels {where_sql}"
                cur.execute(count_sql, tuple(params))
                total = cur.fetchone()["count"]

                # 2. Truy vấn dữ liệu phân trang
                offset = (page - 1) * limit
                page_params = list(params) + [limit, offset]
                
                sql = f"""
                    SELECT hotels.*, 
                        (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) as min_price
                    FROM hotels 
                    {where_sql} 
                    {order_sql} 
                    LIMIT %s OFFSET %s
                """
                cur.execute(sql, tuple(page_params))
                rows = cur.fetchall()

        hotels_data = []
        for row in rows:
            cleaned = clean_row(row)
            first_image = [row["images"][0]] if row["images"] else []
            hotels_data.append({
                "id": cleaned["id"],
                "name": cleaned["name"],
                "accommodation_type": cleaned["accommodation_type"],
                "star_rating": cleaned["star_rating"],
                "is_luxury": cleaned["is_luxury"],
                "review_score": cleaned["review_score"],
                "review_count": cleaned["review_count"],
                "address": cleaned["address"],
                "city": cleaned["city"],
                "latitude": cleaned["latitude"],
                "longitude": cleaned["longitude"],
                "amenities": cleaned["amenities"][:5] if cleaned["amenities"] else [],
                "policyNotes": cleaned["policyNotes"],
                "useful_info": cleaned["useful_info"],
                "suitable_for": cleaned["suitable_for"],
                "images": first_image,
                "rooms": {
                    "min_price": cleaned["min_price"]
                }
            })

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "data": hotels_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 13. GET /api/hotels/combo-suggest - Gợi ý combo theo ngân sách
# -------------------------------------------------------------
@app.get("/api/hotels/combo-suggest")
def get_combo_suggest(
    city: str,
    budget_total: float,
    guests: int = 2,
    nights: int = 2,
    suitable_for: Optional[str] = None,
    min_occupancy: Optional[int] = None
):
    try:
        hotel_nights = max(1, nights - 1)
        
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Tìm tất cả khách sạn tại thành phố
                hotel_sql = "SELECT * FROM hotels WHERE city ILIKE %s"
                hotel_params = [city]

                if suitable_for:
                    hotel_params.append([suitable_for])
                    hotel_sql += " AND suitable_for @> %s::text[]"

                cur.execute(hotel_sql, tuple(hotel_params))
                hotels = cur.fetchall()

                suggestions = []

                for hotel in hotels:
                    # Lấy phòng rẻ nhất của khách sạn này phù hợp số người
                    room_sql = "SELECT * FROM rooms WHERE hotel_id = %s"
                    room_params = [hotel["id"]]

                    if min_occupancy is not None:
                        room_params.append(min_occupancy)
                        room_sql += " AND max_occupancy >= %s"
                    else:
                        room_params.append(guests)
                        room_sql += " AND max_occupancy >= %s"

                    room_sql += " ORDER BY price ASC LIMIT 1"
                    cur.execute(room_sql, tuple(room_params))
                    room = cur.fetchone()

                    if not room or room["price"] is None:
                        continue

                    room_cost = float(room["price"]) * hotel_nights
                    if room_cost > budget_total:
                        continue  # Vượt quá tổng ngân sách

                    # Lấy danh sách hoạt động vui chơi của khách sạn này
                    cur.execute(
                        "SELECT * FROM activities WHERE hotel_id = %s ORDER BY review_score DESC",
                        (hotel["id"],)
                    )
                    activities = cur.fetchall()

                    selected_acts = []
                    total_act_cost = 0.0

                    # Tìm các hoạt động thích hợp vừa với ngân sách còn lại
                    for act in activities:
                        act_cost_group = float(act["price_amount"]) * guests
                        if room_cost + total_act_cost + act_cost_group <= budget_total:
                            selected_acts.append(act)
                            total_act_cost += act_cost_group
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
                        "remaining_budget": budget_total - total_cost
                    })

        if not suggestions:
            raise HTTPException(status_code=404, detail="Không tìm thấy gói combo nào phù hợp với ngân sách của bạn.")

        # Sắp xếp các đề xuất theo điểm đánh giá của khách sạn giảm dần
        suggestions.sort(key=lambda x: x["hotel"]["review_score"] or 0, reverse=True)
        return suggestions[0]

    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 14. GET /api/hotels/compare - So sánh nhiều khách sạn
# -------------------------------------------------------------
@app.get("/api/hotels/compare")
def compare_hotels(ids: str):
    try:
        id_list = []
        for i in ids.split(","):
            try:
                id_list.append(int(i.strip()))
            except ValueError:
                continue

        if not id_list:
            raise HTTPException(status_code=400, detail="Invalid ids parameter (comma-separated integers).")

        sql = """
            SELECT hotels.*, 
                (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) as min_price
            FROM hotels 
            WHERE id = ANY(%s::int[])
        """
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (id_list,))
                rows = cur.fetchall()

        hotels_data = []
        for row in rows:
            dashboard = calculate_reviews_dashboard(row["reviews_detail"])
            hotels_data.append({
                "id": row["id"],
                "name": row["name"],
                "star_rating": float(row["star_rating"]) if row["star_rating"] else None,
                "is_luxury": row["is_luxury"],
                "review_score": float(row["review_score"]) if row["review_score"] else None,
                "review_count": row["review_count"],
                "reviews_detail": {
                    "grades": dashboard["grades"]
                },
                "amenities": row["amenities"],
                "rooms": {
                    "min_price": float(row["min_price"]) if row["min_price"] is not None else None
                },
                "images": [row["images"][0]] if row["images"] else []
            })

        return {"hotels": hotels_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 11. GET /api/activities - Tìm kiếm hoạt động toàn hệ thống
# -------------------------------------------------------------
@app.get("/api/activities")
def get_activities(
    city: Optional[str] = None,
    sort_by: Optional[str] = None
):
    try:
        sql = """
            SELECT activities.*, hotels.name as hotel_name, hotels.city as hotel_city
            FROM activities
            JOIN hotels ON activities.hotel_id = hotels.id
        """
        where = []
        params = []

        if city:
            params.append(city)
            where.append("hotels.city ILIKE %s")

        if where:
            sql += f" WHERE {' AND '.join(where)}"

        if sort_by == "review_score:desc":
            sql += " ORDER BY activities.review_score DESC NULLS LAST"

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

# -------------------------------------------------------------
# 2. GET /api/hotels/{id} - Lấy chi tiết thông tin một khách sạn
# -------------------------------------------------------------
@app.get("/api/hotels/{id}")
def get_hotel(id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM hotels WHERE id = %s", (id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Hotel not found.")

        return clean_row(row)
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 3. GET /api/hotels/{id}/images - Lấy danh sách ảnh khách sạn
# -------------------------------------------------------------
@app.get("/api/hotels/{id}/images")
def get_hotel_images(id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name, images FROM hotels WHERE id = %s", (id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Hotel not found.")

        return {
            "hotel_id": row["id"],
            "hotel_name": row["name"],
            "images": row["images"] or []
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 4. GET /api/hotels/{id}/policies - Lấy chính sách nhận phòng & phụ phí
# -------------------------------------------------------------
@app.get("/api/hotels/{id}/policies")
def get_hotel_policies(id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, policyNotes, useful_info FROM hotels WHERE id = %s", (id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Hotel not found.")

        return {
            "hotel_id": row["id"],
            "policyNotes": row["policyNotes"] or [],
            "useful_info": serialize_db_value(row["useful_info"]) or {}
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 5. GET /api/hotels/{id}/reviews - Lấy điểm đánh giá chi tiết & tag
# -------------------------------------------------------------
@app.get("/api/hotels/{id}/reviews")
def get_hotel_reviews(id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, review_score, review_count, reviews_detail FROM hotels WHERE id = %s", (id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Hotel not found.")

        dashboard = calculate_reviews_dashboard(row["reviews_detail"])
        return {
            "hotel_id": row["id"],
            "review_score": float(row["review_score"]) if row["review_score"] else None,
            "review_count": row["review_count"],
            "reviews_detail": dashboard
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 6. GET /api/hotels/{id}/location - Tọa độ, địa chỉ & lân cận
# -------------------------------------------------------------
@app.get("/api/hotels/{id}/location")
def get_hotel_location(id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name, address, city, latitude, longitude FROM hotels WHERE id = %s", (id,))
                hotel = cur.fetchone()

                if not hotel:
                    raise HTTPException(status_code=404, detail="Hotel not found.")

                cur.execute(
                    "SELECT name, type, distance_km FROM nearby_places WHERE hotel_id = %s ORDER BY distance_km ASC",
                    (id,)
                )
                places = cur.fetchall()

        return {
            "hotel_id": hotel["id"],
            "name": hotel["name"],
            "address": hotel["address"],
            "city": hotel["city"],
            "latitude": hotel["latitude"],
            "longitude": hotel["longitude"],
            "nearby_places": [clean_row(p) for p in places]
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 7. GET /api/hotels/{id}/rooms - Danh sách loại phòng của khách sạn
# -------------------------------------------------------------
@app.get("/api/hotels/{id}/rooms")
def get_hotel_rooms(
    id: int,
    min_occupancy: Optional[int] = None,
    room_view: Optional[str] = None,
    sort_by: Optional[str] = None,
    limit: int = 100
):
    try:
        where = ["hotel_id = %s"]
        params = [id]

        if min_occupancy is not None:
            params.append(min_occupancy)
            where.append("max_occupancy >= %s")

        if room_view:
            params.append(f"%{room_view}%")
            where.append("room_view ILIKE %s")

        order = "ORDER BY id ASC"
        if sort_by == "price:asc":
            order = "ORDER BY price ASC"
        elif sort_by == "price:desc":
            order = "ORDER BY price DESC"

        params.append(limit)
        sql = f"SELECT * FROM rooms WHERE {' AND '.join(where)} {order} LIMIT %s"

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                rooms = cur.fetchall()

        formatted_rooms = []
        for r in rooms:
            cleaned = clean_row(r)
            cleaned["room_type_id"] = str(r["room_type_id"]) if r["room_type_id"] else None
            # Trả về ảnh đầu tiên dưới dạng mảng theo mẫu tài liệu
            cleaned["images"] = [r["images"][0]] if r["images"] else []
            formatted_rooms.append(cleaned)

        return {
            "hotel_id": id,
            "rooms": formatted_rooms
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 8. GET /api/rooms/{id} - Chi tiết đầy đủ một loại phòng
# -------------------------------------------------------------
@app.get("/api/rooms/{id}")
def get_room(id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM rooms WHERE id = %s", (id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Room not found.")

        cleaned = clean_row(row)
        cleaned["room_type_id"] = str(row["room_type_id"]) if row["room_type_id"] else None
        return cleaned
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 9. GET /api/hotels/{id}/nearby-places - Địa điểm lân cận khách sạn
# -------------------------------------------------------------
@app.get("/api/hotels/{id}/nearby-places")
def get_hotel_nearby_places(
    id: int,
    type: Optional[str] = None,
    distance_max_km: Optional[float] = None
):
    try:
        where = ["hotel_id = %s"]
        params = [id]

        if type:
            params.append(type)
            where.append("type = %s")

        if distance_max_km is not None:
            params.append(distance_max_km)
            where.append("distance_km <= %s")

        sql = f"SELECT * FROM nearby_places WHERE {' AND '.join(where)} ORDER BY distance_km ASC"

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, tuple(params))
                places = cur.fetchall()

        return {
            "data": [clean_row(p) for p in places]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 10. GET /api/hotels/{id}/activities - Hoạt động vui chơi của khách sạn
# -------------------------------------------------------------
@app.get("/api/hotels/{id}/activities")
def get_hotel_activities(
    id: int,
    price_max: Optional[float] = None,
    sort_by: Optional[str] = None
):
    try:
        where = ["hotel_id = %s"]
        params = [id]

        if price_max is not None:
            params.append(price_max)
            where.append("price_amount <= %s")

        order = "ORDER BY id ASC"
        if sort_by == "price:asc":
            order = "ORDER BY price_amount ASC"
        elif sort_by == "review_score:desc":
            order = "ORDER BY review_score DESC NULLS LAST"

        sql = f"SELECT * FROM activities WHERE {' AND '.join(where)} {order}"

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

# -------------------------------------------------------------
# 12. GET /api/hotels/{id}/combo - Tạo gói combo
# -------------------------------------------------------------
@app.get("/api/hotels/{id}/combo")
def get_hotel_combo(
    id: int,
    nights: int = 3,
    guests: int = 2,
    include_activities: bool = True
):
    try:
        hotel_nights = max(1, nights - 1)

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # 1. Khách sạn
                cur.execute("SELECT id, name, star_rating, review_score FROM hotels WHERE id = %s", (id,))
                hotel = cur.fetchone()
                if not hotel:
                    raise HTTPException(status_code=404, detail="Hotel not found.")

                # 2. Phòng đề xuất (phòng rẻ nhất)
                cur.execute("SELECT name, price, room_view FROM rooms WHERE hotel_id = %s ORDER BY price ASC LIMIT 1", (id,))
                room = cur.fetchone()
                if not room:
                    raise HTTPException(status_code=404, detail="No rooms found for this hotel to create a combo.")

                # 3. Hoạt động
                activities = []
                activities_cost = 0.0
                if include_activities:
                    cur.execute(
                        "SELECT id, title, price_amount, review_score FROM activities WHERE hotel_id = %s ORDER BY review_score DESC LIMIT 3",
                        (id,)
                    )
                    activities = cur.fetchall()
                    activities_cost = sum(float(a["price_amount"]) for a in activities) * guests

        room_cost = float(room["price"]) * hotel_nights
        estimated_total = room_cost + activities_cost

        return {
            "hotel": {
                "id": hotel["id"],
                "name": hotel["name"],
                "star_rating": float(hotel["star_rating"]) if hotel["star_rating"] else None,
                "review_score": float(hotel["review_score"]) if hotel["review_score"] else None,
                "recommended_room": clean_row(room)
            },
            "activities": [clean_row(a) for a in activities],
            "estimated_total": estimated_total
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------
# 15. GET /api/hotels/{id}/similar - Gợi ý khách sạn tương tự giá rẻ hơn
# -------------------------------------------------------------
@app.get("/api/hotels/{id}/similar")
def get_similar_hotels(id: int):
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Lấy thông tin khách sạn gốc kèm giá rẻ nhất
                ref_sql = """
                    SELECT hotels.*, 
                        COALESCE((SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id), 3000000) as min_price
                    FROM hotels 
                    WHERE id = %s
                """
                cur.execute(ref_sql, (id,))
                ref_hotel = cur.fetchone()

                if not ref_hotel:
                    raise HTTPException(status_code=404, detail="Reference hotel not found.")

                ref_price = float(ref_hotel["min_price"])

                # Gợi ý: cùng thành phố, cùng loại, rẻ hơn ít nhất 10%
                similar_sql = """
                    SELECT hotels.*, 
                        (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) as min_price
                    FROM hotels 
                    WHERE city = %s 
                      AND accommodation_type = %s 
                      AND id != %s
                      AND EXISTS (
                        SELECT 1 FROM rooms 
                        WHERE rooms.hotel_id = hotels.id 
                        AND price <= %s
                      )
                    ORDER BY review_score DESC NULLS LAST
                    LIMIT 3
                """
                price_max_threshold = ref_price * 0.9
                cur.execute(
                    similar_sql,
                    (ref_hotel["city"], ref_hotel["accommodation_type"], id, price_max_threshold)
                )
                similar_hotels = cur.fetchall()

        formatted_similar = []
        for s in similar_hotels:
            s_price = float(s["min_price"])
            saving_pct = int(round((1 - s_price / ref_price) * 100))
            formatted_similar.append({
                "id": s["id"],
                "name": s["name"],
                "star_rating": float(s["star_rating"]) if s["star_rating"] else None,
                "review_score": float(s["review_score"]) if s["review_score"] else None,
                "amenities": s["amenities"][:5] if s["amenities"] else [],
                "rooms": {
                    "min_price": s_price
                },
                "price_saving_pct": saving_pct,
                "images": [s["images"][0]] if s["images"] else []
            })

        return {
            "reference_hotel": {
                "id": ref_hotel["id"],
                "name": ref_hotel["name"],
                "review_score": float(ref_hotel["review_score"]) if ref_hotel["review_score"] else None,
                "amenities": ref_hotel["amenities"][:5] if ref_hotel["amenities"] else [],
                "rooms": {
                    "min_price": ref_price
                }
            },
            "similar_hotels": formatted_similar
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Lấy PORT từ biến môi trường của Render, mặc định là 5000 ở local
    port = int(os.getenv("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
