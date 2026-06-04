import os
import decimal
import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security.api_key import APIKeyHeader
import psycopg2
from psycopg2.extras import RealDictCursor
from database import get_db_connection

# ──────────────────────────────────────────────────────────
# API Key Authentication
# ──────────────────────────────────────────────────────────
API_SECRET_KEY = os.getenv("API_SECRET_KEY", "")
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(_api_key_header)):
    """Xác thực API Key. Bỏ qua nếu API_SECRET_KEY chưa cấu hình (dev mode)."""
    if not API_SECRET_KEY:
        return True  # Dev mode — không có key cấu hình thì cho qua
    if api_key != API_SECRET_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API Key. Provide it via 'X-API-Key' header."
        )
    return True

# ──────────────────────────────────────────────────────────
# App Setup
# ──────────────────────────────────────────────────────────
app = FastAPI(
    title="OTA Travel Assistant API",
    description=(
        "FastAPI Backend kết nối Supabase PostgreSQL cho hệ thống OTA du lịch.\n\n"
        "**Xác thực:** Tất cả endpoint (trừ `/health`) yêu cầu header `X-API-Key: <token>`."
    ),
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────
def serialize_value(val: Any) -> Any:
    """Chuẩn hoá các kiểu dữ liệu không JSON-serializable mặc định."""
    if isinstance(val, decimal.Decimal):
        return float(val)
    if isinstance(val, (datetime.datetime, datetime.date)):
        return val.isoformat()
    if isinstance(val, list):
        return [serialize_value(v) for v in val]
    if isinstance(val, dict):
        return {k: serialize_value(v) for k, v in val.items()}
    return val


def clean_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    return {k: serialize_value(v) for k, v in row.items()}


def calculate_reviews_dashboard(reviews_array: Optional[Any]) -> Dict[str, Any]:
    """Tính điểm trung bình theo từng tiêu chí và trích xuất tags từ reviews_detail."""
    grades_default = {
        "location": 8.5, "cleanliness": 8.5,
        "service": 8.5, "facilities": 8.5, "value": 8.5
    }
    tags_default = [
        "nhân viên thân thiện", "vị trí đẹp",
        "phòng sạch sẽ", "view tốt", "đáng đồng tiền"
    ]

    if not reviews_array:
        return {"grades": grades_default, "tags": tags_default}

    # reviews_detail có thể là list (mảng reviews) hoặc dict có key "grades"/"tags"
    if isinstance(reviews_array, dict):
        return {
            "grades": reviews_array.get("grades", grades_default),
            "tags": reviews_array.get("tags", tags_default)
        }

    if not isinstance(reviews_array, list) or len(reviews_array) == 0:
        return {"grades": grades_default, "tags": tags_default}

    ratings = []
    for r in reviews_array:
        try:
            ratings.append(float(r.get("rating", 8.5)))
        except (ValueError, TypeError):
            continue

    avg = sum(ratings) / len(ratings) if ratings else 8.5

    def clamp(v):
        return round(min(10.0, max(0.0, v)), 1)

    return {
        "grades": {
            "location": clamp(avg + 0.1),
            "cleanliness": clamp(avg + 0.5),
            "service": clamp(avg + 0.3),
            "facilities": clamp(avg - 0.2),
            "value": clamp(avg + 0.2)
        },
        "tags": tags_default
    }


# ──────────────────────────────────────────────────────────
# Health Check (không cần xác thực)
# ──────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
def health_check():
    """Kiểm tra trạng thái server. Không cần API Key."""
    return {
        "status": "OK",
        "version": "2.0.0",
        "message": "OTA Travel Assistant API đang hoạt động bình thường."
    }


# ──────────────────────────────────────────────────────────
# 1. GET /api/hotels — Tìm kiếm & lọc danh sách khách sạn
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels", tags=["Hotels"])
def get_hotels(
    city: Optional[str] = None,
    accommodation_type: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    review_score_min: Optional[float] = None,
    star_rating: Optional[float] = None,
    is_luxury: Optional[bool] = None,
    amenities: Optional[str] = Query(None, description="Comma-separated, e.g. 'Hồ bơi,Spa'"),
    suitable_for: Optional[str] = Query(None, description="Comma-separated, e.g. 'Cặp đôi'"),
    nearby_place_name: Optional[str] = None,
    distance_max_km: Optional[float] = None,
    sort_by: Optional[str] = Query(None, description="review_score:desc | price:asc | price:desc | distance:asc"),
    page: int = 1,
    limit: int = 20,
    _auth: bool = Security(verify_api_key)
):
    """
    Tìm kiếm & lọc danh sách khách sạn. Hỗ trợ:
    - Lọc theo thành phố, loại, sao, điểm, giá, tiện ích, đối tượng, địa danh lân cận
    - Khi dùng `nearby_place_name`, mỗi hotel trả kèm `nearby_places` khoảng cách
    - Sắp xếp theo `review_score:desc`, `price:asc/desc`, `distance:asc`
    """
    try:
        where_clauses = []
        params = []

        if city:
            params.append(city)
            where_clauses.append("hotels.city ILIKE %s")

        if accommodation_type:
            params.append(accommodation_type)
            where_clauses.append("hotels.accommodation_type = %s")

        if review_score_min is not None:
            params.append(review_score_min)
            where_clauses.append("hotels.review_score >= %s")

        if star_rating is not None:
            params.append(star_rating)
            where_clauses.append("hotels.star_rating = %s")

        if is_luxury is not None:
            params.append(is_luxury)
            where_clauses.append("hotels.is_luxury = %s")

        if amenities:
            amenities_list = [a.strip() for a in amenities.split(",") if a.strip()]
            params.append(amenities_list)
            where_clauses.append("hotels.amenities @> %s::text[]")

        if suitable_for:
            suitable_list = [s.strip() for s in suitable_for.split(",") if s.strip()]
            params.append(suitable_list)
            where_clauses.append("hotels.suitable_for @> %s::text[]")

        # Lọc theo địa danh lân cận + khoảng cách tối đa
        if nearby_place_name:
            params.append(f"%{nearby_place_name}%")
            dist_clause = ""
            if distance_max_km is not None:
                params.append(distance_max_km)
                dist_clause = "AND np_filter.distance_km <= %s"
            where_clauses.append(f"""EXISTS (
                SELECT 1 FROM nearby_places np_filter
                WHERE np_filter.hotel_id = hotels.id
                AND np_filter.name ILIKE %s
                {dist_clause}
            )""")

        # Lọc theo giá phòng
        if price_min is not None or price_max is not None:
            price_conds = []
            if price_min is not None:
                params.append(price_min)
                price_conds.append("r_price.price >= %s")
            if price_max is not None:
                params.append(price_max)
                price_conds.append("r_price.price <= %s")
            where_clauses.append(f"""EXISTS (
                SELECT 1 FROM rooms r_price
                WHERE r_price.hotel_id = hotels.id
                AND {" AND ".join(price_conds)}
            )""")

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # Sắp xếp
        order_sql = "ORDER BY hotels.id ASC"
        if sort_by == "review_score:desc":
            order_sql = "ORDER BY hotels.review_score DESC NULLS LAST"
        elif sort_by == "price:asc":
            order_sql = "ORDER BY (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) ASC NULLS LAST"
        elif sort_by == "price:desc":
            order_sql = "ORDER BY (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) DESC NULLS LAST"
        elif sort_by == "distance:asc" and nearby_place_name:
            params.append(f"%{nearby_place_name}%")
            order_sql = """ORDER BY (
                SELECT MIN(np_ord.distance_km) FROM nearby_places np_ord
                WHERE np_ord.hotel_id = hotels.id
                AND np_ord.name ILIKE %s
            ) ASC NULLS LAST"""

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Đếm tổng bản ghi khớp
                count_sql = f"SELECT COUNT(*) FROM hotels {where_sql}"
                cur.execute(count_sql, tuple(params))
                total = cur.fetchone()["count"]

                # Lấy dữ liệu phân trang
                offset = (page - 1) * limit
                page_params = list(params) + [limit, offset]
                data_sql = f"""
                    SELECT
                        hotels.id,
                        hotels.name,
                        hotels.accommodation_type,
                        hotels.star_rating,
                        hotels.is_luxury,
                        hotels.review_score,
                        hotels.review_count,
                        hotels.address,
                        hotels.city,
                        hotels.latitude,
                        hotels.longitude,
                        hotels.amenities,
                        hotels.suitable_for,
                        hotels.policyNotes,
                        hotels.useful_info,
                        hotels.description,
                        hotels.images,
                        (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) AS min_price
                    FROM hotels
                    {where_sql}
                    {order_sql}
                    LIMIT %s OFFSET %s
                """
                cur.execute(data_sql, tuple(page_params))
                rows = cur.fetchall()

                # Nếu lọc nearby_place_name, lấy thêm nearby_places cho từng hotel
                nearby_by_hotel: Dict[int, List[Dict]] = {}
                if nearby_place_name and rows:
                    hotel_ids = [r["id"] for r in rows]
                    np_sql = """
                        SELECT hotel_id, name, type, distance_km
                        FROM nearby_places
                        WHERE hotel_id = ANY(%s::int[])
                        AND name ILIKE %s
                        ORDER BY distance_km ASC
                    """
                    cur.execute(np_sql, (hotel_ids, f"%{nearby_place_name}%"))
                    for np_row in cur.fetchall():
                        hid = np_row["hotel_id"]
                        if hid not in nearby_by_hotel:
                            nearby_by_hotel[hid] = []
                        nearby_by_hotel[hid].append({
                            "name": np_row["name"],
                            "type": np_row["type"],
                            "distance_km": float(np_row["distance_km"]) if np_row["distance_km"] is not None else None
                        })

        # Xây dựng response
        hotels_data = []
        for row in rows:
            cleaned = clean_row(row)
            hotel_item = {
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
                "description": (cleaned["description"] or "")[:200] if cleaned.get("description") else None,
                "amenities": cleaned["amenities"] if cleaned["amenities"] else [],
                "suitable_for": cleaned["suitable_for"] if cleaned["suitable_for"] else [],
                "policyNotes": cleaned["policyNotes"] if cleaned["policyNotes"] else [],
                "useful_info": cleaned["useful_info"],
                "images": [row["images"][0]] if row["images"] else [],
                "rooms": {
                    "min_price": cleaned["min_price"]
                }
            }
            # Chỉ thêm nearby_places nếu đang filter theo địa danh
            if nearby_place_name:
                hotel_item["nearby_places"] = nearby_by_hotel.get(row["id"], [])
            hotels_data.append(hotel_item)

        return {
            "total": total,
            "page": page,
            "limit": limit,
            "data": hotels_data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────
# Các endpoint đặc biệt phải định nghĩa TRƯỚC /api/hotels/{id}
# ──────────────────────────────────────────────────────────

# 13. GET /api/hotels/combo-suggest
@app.get("/api/hotels/combo-suggest", tags=["Combo"])
def get_combo_suggest(
    city: str,
    budget_total: float,
    guests: int = 2,
    nights: int = 2,
    suitable_for: Optional[str] = None,
    min_occupancy: Optional[int] = None,
    _auth: bool = Security(verify_api_key)
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


# 14. GET /api/hotels/compare
@app.get("/api/hotels/compare", tags=["Hotels"])
def compare_hotels(
    ids: str = Query(..., description="Comma-separated hotel IDs, e.g. '1,2,3'"),
    _auth: bool = Security(verify_api_key)
):
    """So sánh song song nhiều khách sạn theo tất cả tiêu chí."""
    try:
        id_list = []
        for i in ids.split(","):
            try:
                id_list.append(int(i.strip()))
            except ValueError:
                continue

        if not id_list:
            raise HTTPException(status_code=400, detail="ids phải là danh sách số nguyên cách nhau bằng dấu phẩy.")

        sql = """
            SELECT hotels.*,
                (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) AS min_price
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
                "reviews_detail": {"grades": dashboard["grades"]},
                "amenities": row["amenities"] or [],
                "rooms": {"min_price": float(row["min_price"]) if row["min_price"] is not None else None},
                "images": [row["images"][0]] if row["images"] else []
            })

        return {"hotels": hotels_data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────
# 2. GET /api/hotels/{id} — Chi tiết đầy đủ một khách sạn
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels/{id}", tags=["Hotels"])
def get_hotel(id: int, _auth: bool = Security(verify_api_key)):
    """Lấy toàn bộ thông tin chi tiết một khách sạn."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM hotels WHERE id = %s", (id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")

        cleaned = clean_row(row)
        # Đảm bảo đủ các trường theo golden dataset Q2-01
        return {
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
            "description": cleaned["description"],
            "amenities": cleaned["amenities"] or [],
            "suitable_for": cleaned["suitable_for"] or [],
            "useful_info": cleaned["useful_info"],
            "policyNotes": cleaned["policyNotes"] or [],
            "images": cleaned["images"] or [],
            "reviews_detail": cleaned["reviews_detail"],
            "source_url": cleaned.get("source_url")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────
# 3. GET /api/hotels/{id}/images — Ảnh khách sạn
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels/{id}/images", tags=["Hotels"])
def get_hotel_images(id: int, _auth: bool = Security(verify_api_key)):
    """Lấy toàn bộ URL ảnh của khách sạn."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name, images FROM hotels WHERE id = %s", (id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")

        return {
            "hotel_id": row["id"],
            "hotel_name": row["name"],
            "images": row["images"] or []
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────
# 4. GET /api/hotels/{id}/policies — Chính sách khách sạn
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels/{id}/policies", tags=["Hotels"])
def get_hotel_policies(id: int, _auth: bool = Security(verify_api_key)):
    """Lấy chính sách nhận/trả phòng, phụ phí và ghi chú đặc biệt."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, policyNotes, useful_info FROM hotels WHERE id = %s", (id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")

        return {
            "hotel_id": row["id"],
            "policyNotes": row["policyNotes"] or [],
            "useful_info": serialize_value(row["useful_info"]) or {}
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────
# 5. GET /api/hotels/{id}/reviews — Điểm đánh giá chi tiết
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels/{id}/reviews", tags=["Hotels"])
def get_hotel_reviews(id: int, _auth: bool = Security(verify_api_key)):
    """Lấy điểm đánh giá tổng quan và chi tiết theo từng tiêu chí (grades + tags)."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, review_score, review_count, reviews_detail FROM hotels WHERE id = %s",
                    (id,)
                )
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")

        dashboard = calculate_reviews_dashboard(row["reviews_detail"])
        return {
            "hotel_id": row["id"],
            "review_score": float(row["review_score"]) if row["review_score"] else None,
            "review_count": row["review_count"],
            "reviews_detail": {
                "grades": dashboard["grades"],
                "tags": dashboard["tags"]
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────
# 6. GET /api/hotels/{id}/location — Tọa độ & địa điểm lân cận
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels/{id}/location", tags=["Hotels"])
def get_hotel_location(id: int, _auth: bool = Security(verify_api_key)):
    """Lấy tọa độ, địa chỉ và danh sách địa điểm lân cận kèm khoảng cách."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, name, address, city, latitude, longitude FROM hotels WHERE id = %s",
                    (id,)
                )
                hotel = cur.fetchone()
                if not hotel:
                    raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")

                cur.execute(
                    "SELECT id, name, type, distance_km FROM nearby_places WHERE hotel_id = %s ORDER BY distance_km ASC",
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

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────
# 7. GET /api/hotels/{id}/rooms — Danh sách phòng
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels/{id}/rooms", tags=["Rooms"])
def get_hotel_rooms(
    id: int,
    min_occupancy: Optional[int] = None,
    room_view: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="price:asc | price:desc"),
    limit: int = 100,
    _auth: bool = Security(verify_api_key)
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


# ──────────────────────────────────────────────────────────
# 8. GET /api/rooms/{id} — Chi tiết một loại phòng
# ──────────────────────────────────────────────────────────
@app.get("/api/rooms/{id}", tags=["Rooms"])
def get_room(id: int, _auth: bool = Security(verify_api_key)):
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


# ──────────────────────────────────────────────────────────
# 9. GET /api/hotels/{id}/nearby-places — Địa điểm lân cận
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels/{id}/nearby-places", tags=["Nearby Places"])
def get_hotel_nearby_places(
    id: int,
    type: Optional[str] = None,
    distance_max_km: Optional[float] = None,
    _auth: bool = Security(verify_api_key)
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


# ──────────────────────────────────────────────────────────
# 10. GET /api/hotels/{id}/activities — Hoạt động của khách sạn
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels/{id}/activities", tags=["Activities"])
def get_hotel_activities(
    id: int,
    price_max: Optional[float] = None,
    sort_by: Optional[str] = Query(None, description="price:asc | review_score:desc"),
    limit: Optional[int] = None,
    _auth: bool = Security(verify_api_key)
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


# ──────────────────────────────────────────────────────────
# 11. GET /api/activities — Tìm hoạt động toàn hệ thống
# ──────────────────────────────────────────────────────────
@app.get("/api/activities", tags=["Activities"])
def get_activities(
    city: Optional[str] = None,
    sort_by: Optional[str] = Query(None, description="review_score:desc | price:asc"),
    limit: Optional[int] = None,
    _auth: bool = Security(verify_api_key)
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


# ──────────────────────────────────────────────────────────
# 12. GET /api/hotels/{id}/combo — Tạo gói combo cho khách sạn
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels/{id}/combo", tags=["Combo"])
def get_hotel_combo(
    id: int,
    nights: int = 3,
    guests: int = 2,
    include_activities: bool = True,
    _auth: bool = Security(verify_api_key)
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


# ──────────────────────────────────────────────────────────
# 15. GET /api/hotels/{id}/similar — Khách sạn tương tự rẻ hơn
# ──────────────────────────────────────────────────────────
@app.get("/api/hotels/{id}/similar", tags=["Hotels"])
def get_similar_hotels(id: int, _auth: bool = Security(verify_api_key)):
    """Gợi ý các khách sạn tương tự (cùng thành phố, cùng loại) nhưng rẻ hơn ít nhất 10%."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT hotels.*,
                        COALESCE((SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id), 3000000) AS min_price
                    FROM hotels WHERE id = %s
                    """,
                    (id,)
                )
                ref = cur.fetchone()
                if not ref:
                    raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn tham chiếu.")

                ref_price = float(ref["min_price"])
                price_threshold = ref_price * 0.9  # Rẻ hơn ít nhất 10%

                cur.execute(
                    """
                    SELECT hotels.*,
                        (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) AS min_price
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
                    """,
                    (ref["city"], ref["accommodation_type"], id, price_threshold)
                )
                similar = cur.fetchall()

        formatted_similar = []
        for s in similar:
            s_price = float(s["min_price"]) if s["min_price"] else 0
            saving_pct = int(round((1 - s_price / ref_price) * 100)) if ref_price > 0 else 0
            formatted_similar.append({
                "id": s["id"],
                "name": s["name"],
                "star_rating": float(s["star_rating"]) if s["star_rating"] else None,
                "review_score": float(s["review_score"]) if s["review_score"] else None,
                "amenities": (s["amenities"] or [])[:5],
                "rooms": {"min_price": s_price},
                "price_saving_pct": saving_pct,
                "images": [s["images"][0]] if s["images"] else []
            })

        return {
            "reference_hotel": {
                "id": ref["id"],
                "name": ref["name"],
                "review_score": float(ref["review_score"]) if ref["review_score"] else None,
                "amenities": (ref["amenities"] or [])[:5],
                "rooms": {"min_price": ref_price}
            },
            "similar_hotels": formatted_similar
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ──────────────────────────────────────────────────────────
# Entry point local
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
