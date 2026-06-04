from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from psycopg2.extras import RealDictCursor
from app.database import get_db_connection
from app.helpers import clean_row, calculate_reviews_dashboard

router = APIRouter()

# 1. GET /api/hotels — Tìm kiếm & lọc danh sách khách sạn
@router.get("/api/hotels", tags=["Hotels"])
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
    limit: int = 20
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
        sort_params = []
        if sort_by == "review_score:desc":
            order_sql = "ORDER BY hotels.review_score DESC NULLS LAST"
        elif sort_by == "price:asc":
            order_sql = "ORDER BY (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) ASC NULLS LAST"
        elif sort_by == "price:desc":
            order_sql = "ORDER BY (SELECT MIN(price) FROM rooms WHERE rooms.hotel_id = hotels.id) DESC NULLS LAST"
        elif sort_by == "distance:asc" and nearby_place_name:
            sort_params.append(f"%{nearby_place_name}%")
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
                page_params = list(params) + sort_params + [limit, offset]
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
                "policyNotes": (cleaned.get("policynotes") or cleaned.get("policyNotes") or []),
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


# 14. GET /api/hotels/compare
@router.get("/api/hotels/compare", tags=["Hotels"])
def compare_hotels(
    ids: str = Query(..., description="Comma-separated hotel IDs, e.g. '1,2,3'")
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


# 2. GET /api/hotels/{id} — Chi tiết đầy đủ một khách sạn
@router.get("/api/hotels/{id}", tags=["Hotels"])
def get_hotel(id: int):
    """Lấy toàn bộ thông tin chi tiết một khách sạn."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM hotels WHERE id = %s", (id,))
                row = cur.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")

        cleaned = clean_row(row)
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
            "policyNotes": cleaned.get("policynotes") or cleaned.get("policyNotes") or [],
            "images": cleaned["images"] or [],
            "reviews_detail": cleaned["reviews_detail"],
            "source_url": cleaned.get("source_url")
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 3. GET /api/hotels/{id}/images — Ảnh khách sạn
@router.get("/api/hotels/{id}/images", tags=["Hotels"])
def get_hotel_images(id: int):
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


# 4. GET /api/hotels/{id}/policies — Chính sách khách sạn
@router.get("/api/hotels/{id}/policies", tags=["Hotels"])
def get_hotel_policies(id: int):
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
            "policyNotes": row.get("policynotes") or row.get("policyNotes") or [],
            "useful_info": clean_row({"u": row["useful_info"]})["u"] or {}
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 5. GET /api/hotels/{id}/reviews — Điểm đánh giá chi tiết
@router.get("/api/hotels/{id}/reviews", tags=["Hotels"])
def get_hotel_reviews(id: int):
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


# 6. GET /api/hotels/{id}/location — Tọa độ & địa điểm lân cận
@router.get("/api/hotels/{id}/location", tags=["Hotels"])
def get_hotel_location(id: int):
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


# 15. GET /api/hotels/{id}/similar — Khách sạn tương tự rẻ hơn
@router.get("/api/hotels/{id}/similar", tags=["Hotels"])
def get_similar_hotels(id: int):
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
