from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg2.extras import RealDictCursor

from app.database import get_db_connection
from app.helpers import clean_param, clean_row
from app.routers.common import csv_values, paginated_response, pagination_params, require_hotel_exists

router = APIRouter()


HOTEL_LIST_SELECT = """
    SELECT
        h.id,
        h.name,
        h.property_type,
        h.accommodation_type,
        h.star_rating,
        h.is_luxury,
        h.review_score,
        h.review_count,
        h.address,
        h.city,
        h.city_id,
        h.area,
        h.country,
        h.latitude,
        h.longitude,
        h.description,
        h.source_url,
        (SELECT MIN(r.price) FROM rooms r WHERE r.hotel_id = h.id) AS min_room_price,
        (SELECT hi.url FROM hotel_images hi WHERE hi.hotel_id = h.id ORDER BY hi.is_primary DESC, hi.id ASC LIMIT 1) AS primary_image,
        COALESCE((
            SELECT json_agg(json_build_object('id', a.id, 'name', a.name, 'category', a.category, 'category_id', a.category_id) ORDER BY a.name)
            FROM hotel_amenities ha
            JOIN amenities a ON a.id = ha.amenity_id
            WHERE ha.hotel_id = h.id
        ), '[]'::json) AS amenities,
        COALESCE((
            SELECT json_agg(json_build_object('id', hs.id, 'tag', hs.suitable_for_tag, 'mention_count', hs.mention_count, 'score', hs.score) ORDER BY hs.score DESC NULLS LAST, hs.suitable_for_tag)
            FROM hotel_suitability hs
            WHERE hs.hotel_id = h.id
        ), '[]'::json) AS suitability
"""


def _hotel_filters(
    city: Optional[str],
    area: Optional[str],
    country: Optional[str],
    property_type: Optional[str],
    accommodation_type: Optional[str],
    star_rating_min: Optional[float],
    star_rating_max: Optional[float],
    review_score_min: Optional[float],
    is_luxury: Optional[bool],
    price_min: Optional[float],
    price_max: Optional[float],
    amenities: Optional[str],
    suitable_for: Optional[str],
    nearby_place_name: Optional[str],
    distance_max_km: Optional[float],
) -> tuple[List[str], List[Any]]:
    clauses: List[str] = []
    params: List[Any] = []

    text_filters = [
        ("h.city ILIKE %s", city),
        ("h.area ILIKE %s", area),
        ("h.country ILIKE %s", country),
        ("h.property_type ILIKE %s", property_type),
        ("h.accommodation_type ILIKE %s", accommodation_type),
    ]
    for clause, value in text_filters:
        cleaned = clean_param(value)
        if cleaned:
            clauses.append(clause)
            params.append(f"%{cleaned}%")

    if star_rating_min is not None:
        clauses.append("h.star_rating >= %s")
        params.append(star_rating_min)
    if star_rating_max is not None:
        clauses.append("h.star_rating <= %s")
        params.append(star_rating_max)
    if review_score_min is not None:
        clauses.append("h.review_score >= %s")
        params.append(review_score_min)
    if is_luxury is not None:
        clauses.append("h.is_luxury = %s")
        params.append(is_luxury)

    if price_min is not None or price_max is not None:
        room_clauses = ["r_price.hotel_id = h.id"]
        if price_min is not None:
            room_clauses.append("r_price.price >= %s")
            params.append(price_min)
        if price_max is not None:
            room_clauses.append("r_price.price <= %s")
            params.append(price_max)
        clauses.append(f"EXISTS (SELECT 1 FROM rooms r_price WHERE {' AND '.join(room_clauses)})")

    amenity_values = csv_values(amenities)
    if amenity_values:
        clauses.append("""
            h.id IN (
                SELECT ha.hotel_id
                FROM hotel_amenities ha
                JOIN amenities a ON a.id = ha.amenity_id
                WHERE a.name = ANY(%s::text[])
                GROUP BY ha.hotel_id
                HAVING COUNT(DISTINCT a.name) = %s
            )
        """)
        params.extend([amenity_values, len(amenity_values)])

    suitable_values = csv_values(suitable_for)
    if suitable_values:
        clauses.append("""
            h.id IN (
                SELECT hs.hotel_id
                FROM hotel_suitability hs
                WHERE hs.suitable_for_tag = ANY(%s::text[])
                GROUP BY hs.hotel_id
                HAVING COUNT(DISTINCT hs.suitable_for_tag) = %s
            )
        """)
        params.extend([suitable_values, len(suitable_values)])

    nearby = clean_param(nearby_place_name)
    if nearby:
        nearby_clauses = ["np_filter.hotel_id = h.id", "np_filter.name ILIKE %s"]
        params.append(f"%{nearby}%")
        if distance_max_km is not None:
            nearby_clauses.append("np_filter.distance_km <= %s")
            params.append(distance_max_km)
        clauses.append(f"EXISTS (SELECT 1 FROM nearby_places np_filter WHERE {' AND '.join(nearby_clauses)})")

    return clauses, params


@router.get("/api/hotels", tags=["Hotels"])
def list_hotels(
    city: Optional[str] = Query(None, description="Lọc theo thành phố."),
    area: Optional[str] = Query(None, description="Lọc theo khu vực."),
    country: Optional[str] = Query(None, description="Lọc theo quốc gia."),
    property_type: Optional[str] = Query(None, description="Lọc theo loại property."),
    accommodation_type: Optional[str] = Query(None, description="Lọc theo loại lưu trú."),
    star_rating_min: Optional[float] = Query(None, ge=0, le=5),
    star_rating_max: Optional[float] = Query(None, ge=0, le=5),
    review_score_min: Optional[float] = Query(None, ge=0, le=10),
    is_luxury: Optional[bool] = None,
    price_min: Optional[float] = Query(None, ge=0),
    price_max: Optional[float] = Query(None, ge=0),
    amenities: Optional[str] = Query(None, description="Danh sách tiện ích cách nhau bằng dấu phẩy."),
    suitable_for: Optional[str] = Query(None, description="Danh sách tag phù hợp cách nhau bằng dấu phẩy."),
    nearby_place_name: Optional[str] = Query(None, description="Tên địa điểm lân cận."),
    distance_max_km: Optional[float] = Query(None, ge=0),
    sort_by: Optional[str] = Query(None, description="id:asc | review_score:desc | star_rating:desc | price:asc | price:desc | distance:asc"),
    page_limit: tuple[int, int, int] = Depends(pagination_params),
):
    """Tìm kiếm danh sách khách sạn, trả toàn bộ trường cốt lõi của bảng `hotels` kèm dữ liệu tóm tắt liên quan."""
    try:
        page, limit, offset = page_limit
        sort_by = clean_param(sort_by) or "id:asc"
        clauses, params = _hotel_filters(
            city, area, country, property_type, accommodation_type, star_rating_min, star_rating_max,
            review_score_min, is_luxury, price_min, price_max, amenities, suitable_for,
            nearby_place_name, distance_max_km,
        )
        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        order_sql = "ORDER BY h.id ASC"
        order_params: List[Any] = []
        if sort_by == "review_score:desc":
            order_sql = "ORDER BY h.review_score DESC NULLS LAST, h.id ASC"
        elif sort_by == "star_rating:desc":
            order_sql = "ORDER BY h.star_rating DESC NULLS LAST, h.review_score DESC NULLS LAST"
        elif sort_by == "price:asc":
            order_sql = "ORDER BY (SELECT MIN(r.price) FROM rooms r WHERE r.hotel_id = h.id) ASC NULLS LAST"
        elif sort_by == "price:desc":
            order_sql = "ORDER BY (SELECT MIN(r.price) FROM rooms r WHERE r.hotel_id = h.id) DESC NULLS LAST"
        elif sort_by == "distance:asc" and clean_param(nearby_place_name):
            order_sql = """
                ORDER BY (
                    SELECT MIN(np_order.distance_km)
                    FROM nearby_places np_order
                    WHERE np_order.hotel_id = h.id AND np_order.name ILIKE %s
                ) ASC NULLS LAST
            """
            order_params.append(f"%{clean_param(nearby_place_name)}%")

        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM hotels h {where_sql}", tuple(params))
                total = cur.fetchone()["count"]
                cur.execute(
                    f"{HOTEL_LIST_SELECT} FROM hotels h {where_sql} {order_sql} LIMIT %s OFFSET %s",
                    tuple(params + order_params + [limit, offset]),
                )
                rows = [clean_row(row) for row in cur.fetchall()]

        return paginated_response(total, page, limit, rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/compare", tags=["Hotels"])
def compare_hotels(ids: str = Query(..., description="Hotel IDs cách nhau bằng dấu phẩy, ví dụ: 1,2,3")):
    """So sánh nhiều khách sạn với toàn bộ trường chính và dữ liệu liên quan quan trọng."""
    id_values = [int(item) for item in csv_values(ids) if item.isdigit()]
    if not id_values:
        raise HTTPException(status_code=400, detail="ids phải chứa ít nhất một số nguyên.")
    try:
        sql = f"{HOTEL_LIST_SELECT} FROM hotels h WHERE h.id = ANY(%s::int[]) ORDER BY array_position(%s::int[], h.id)"
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql, (id_values, id_values))
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"hotels": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/{hotel_id}", tags=["Hotels"])
def get_hotel_detail(hotel_id: int):
    """Lấy chi tiết khách sạn, bao phủ toàn bộ bảng quan hệ gắn với `hotel_id`."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM hotels WHERE id = %s", (hotel_id,))
                hotel = cur.fetchone()
                if not hotel:
                    raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")

                related_queries = {
                    "images": "SELECT id, hotel_id, url, is_primary FROM hotel_images WHERE hotel_id = %s ORDER BY is_primary DESC, id ASC",
                    "policy": "SELECT * FROM hotel_policies WHERE hotel_id = %s",
                    "amenities": """
                        SELECT a.id, a.name, a.category, a.category_id, ac.name AS category_name
                        FROM hotel_amenities ha
                        JOIN amenities a ON a.id = ha.amenity_id
                        LEFT JOIN amenity_categories ac ON ac.id = a.category_id
                        WHERE ha.hotel_id = %s
                        ORDER BY ac.name NULLS LAST, a.name
                    """,
                    "suitability": "SELECT * FROM hotel_suitability WHERE hotel_id = %s ORDER BY score DESC NULLS LAST, suitable_for_tag",
                    "review_grades": "SELECT * FROM review_grades WHERE hotel_id = %s ORDER BY grade_name",
                    "review_aspects": "SELECT * FROM review_aspects WHERE hotel_id = %s ORDER BY mentioned DESC NULLS LAST, aspect_name",
                    "reviews": "SELECT * FROM reviews WHERE hotel_id = %s ORDER BY review_date DESC NULLS LAST, id DESC",
                    "rooms": "SELECT * FROM rooms WHERE hotel_id = %s ORDER BY price ASC NULLS LAST, id ASC",
                    "nearby_places": """
                        SELECT np.id, np.hotel_id, np.name, np.type, np.category_id, pc.name AS category_name, np.distance_km
                        FROM nearby_places np
                        LEFT JOIN place_categories pc ON pc.id = np.category_id
                        WHERE np.hotel_id = %s
                        ORDER BY np.distance_km ASC NULLS LAST, np.id ASC
                    """,
                    "activities": "SELECT * FROM activities WHERE hotel_id = %s ORDER BY review_score DESC NULLS LAST, id ASC",
                }
                detail: Dict[str, Any] = clean_row(hotel)
                for key, query in related_queries.items():
                    cur.execute(query, (hotel_id,))
                    rows = cur.fetchall()
                    if key == "policy":
                        detail[key] = clean_row(rows[0]) if rows else None
                    else:
                        detail[key] = [clean_row(row) for row in rows]
        return detail
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/{hotel_id}/images", tags=["Hotel Images"])
def get_hotel_images(hotel_id: int):
    """Lấy toàn bộ trường của `hotel_images` theo khách sạn."""
    require_hotel_exists(hotel_id)
    rows = []
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, hotel_id, url, is_primary FROM hotel_images WHERE hotel_id = %s ORDER BY is_primary DESC, id ASC", (hotel_id,))
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"hotel_id": hotel_id, "images": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/{hotel_id}/policies", tags=["Hotel Policies"])
def get_hotel_policies(hotel_id: int):
    """Lấy toàn bộ trường của `hotel_policies`."""
    require_hotel_exists(hotel_id)
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM hotel_policies WHERE hotel_id = %s", (hotel_id,))
                row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Khách sạn này chưa có dữ liệu chính sách.")
        return clean_row(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/{hotel_id}/reviews", tags=["Reviews"])
def get_hotel_reviews(hotel_id: int, page_limit: tuple[int, int, int] = Depends(pagination_params)):
    """Lấy reviews thô, review grades và review aspects của khách sạn."""
    require_hotel_exists(hotel_id)
    page, limit, offset = page_limit
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT COUNT(*) AS count FROM reviews WHERE hotel_id = %s", (hotel_id,))
                total = cur.fetchone()["count"]
                cur.execute("SELECT * FROM reviews WHERE hotel_id = %s ORDER BY review_date DESC NULLS LAST, id DESC LIMIT %s OFFSET %s", (hotel_id, limit, offset))
                reviews = [clean_row(row) for row in cur.fetchall()]
                cur.execute("SELECT * FROM review_grades WHERE hotel_id = %s ORDER BY grade_name", (hotel_id,))
                grades = [clean_row(row) for row in cur.fetchall()]
                cur.execute("SELECT * FROM review_aspects WHERE hotel_id = %s ORDER BY mentioned DESC NULLS LAST, aspect_name", (hotel_id,))
                aspects = [clean_row(row) for row in cur.fetchall()]
        response = paginated_response(total, page, limit, reviews)
        response["grades"] = grades
        response["aspects"] = aspects
        return response
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/{hotel_id}/amenities", tags=["Amenities"])
def get_hotel_amenities(hotel_id: int):
    """Lấy tiện ích của khách sạn, bao gồm trường từ `amenities`, `amenity_categories` và quan hệ `hotel_amenities`."""
    require_hotel_exists(hotel_id)
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT ha.hotel_id, ha.amenity_id, a.name, a.category, a.category_id, ac.name AS category_name
                    FROM hotel_amenities ha
                    JOIN amenities a ON a.id = ha.amenity_id
                    LEFT JOIN amenity_categories ac ON ac.id = a.category_id
                    WHERE ha.hotel_id = %s
                    ORDER BY ac.name NULLS LAST, a.name
                    """,
                    (hotel_id,),
                )
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"hotel_id": hotel_id, "amenities": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/{hotel_id}/suitability", tags=["Suitability"])
def get_hotel_suitability(hotel_id: int):
    """Lấy toàn bộ trường của `hotel_suitability`."""
    require_hotel_exists(hotel_id)
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT * FROM hotel_suitability WHERE hotel_id = %s ORDER BY score DESC NULLS LAST, suitable_for_tag", (hotel_id,))
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"hotel_id": hotel_id, "suitability": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/{hotel_id}/location", tags=["Nearby Places"])
def get_hotel_location(hotel_id: int):
    """Lấy tọa độ khách sạn và các địa điểm lân cận."""
    require_hotel_exists(hotel_id)
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name, address, city, city_id, area, country, latitude, longitude FROM hotels WHERE id = %s", (hotel_id,))
                hotel = clean_row(cur.fetchone())
                cur.execute(
                    """
                    SELECT np.id, np.hotel_id, np.name, np.type, np.category_id, pc.name AS category_name, np.distance_km
                    FROM nearby_places np
                    LEFT JOIN place_categories pc ON pc.id = np.category_id
                    WHERE np.hotel_id = %s
                    ORDER BY np.distance_km ASC NULLS LAST
                    """,
                    (hotel_id,),
                )
                hotel["nearby_places"] = [clean_row(row) for row in cur.fetchall()]
        return hotel
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/{hotel_id}/text-chunks", tags=["Text Chunks"])
def get_hotel_text_chunks(hotel_id: int, include_embedding: bool = Query(False, description="Đặt true nếu cần trả embedding dạng text.")):
    """Lấy `text_chunks` theo khách sạn. Bảng này có thể rỗng nếu chưa insert embeddings."""
    require_hotel_exists(hotel_id)
    embedding_select = "embedding::text AS embedding" if include_embedding else "NULL AS embedding"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"SELECT id, hotel_id, chunk_type, content, {embedding_select}, metadata, created_at FROM text_chunks WHERE hotel_id = %s ORDER BY id ASC",
                    (hotel_id,),
                )
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"hotel_id": hotel_id, "text_chunks": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotels/{hotel_id}/similar", tags=["Hotels"])
def get_similar_hotels(hotel_id: int, limit: int = Query(5, ge=1, le=20)):
    """Gợi ý khách sạn tương tự theo thành phố, loại lưu trú và khoảng giá phòng tối thiểu."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT h.*, (SELECT MIN(price) FROM rooms WHERE hotel_id = h.id) AS min_room_price
                    FROM hotels h
                    WHERE h.id = %s
                    """,
                    (hotel_id,),
                )
                ref = cur.fetchone()
                if not ref:
                    raise HTTPException(status_code=404, detail="Không tìm thấy khách sạn.")
                ref_price = ref["min_room_price"]
                cur.execute(
                    f"""
                    {HOTEL_LIST_SELECT}
                    FROM hotels h
                    WHERE h.id <> %s
                      AND h.city IS NOT DISTINCT FROM %s
                      AND h.accommodation_type IS NOT DISTINCT FROM %s
                      AND (
                          %s::numeric IS NULL OR
                          (SELECT MIN(price) FROM rooms WHERE hotel_id = h.id) BETWEEN %s::numeric * 0.75 AND %s::numeric * 1.25
                      )
                    ORDER BY h.review_score DESC NULLS LAST, h.star_rating DESC NULLS LAST
                    LIMIT %s
                    """,
                    (hotel_id, ref["city"], ref["accommodation_type"], ref_price, ref_price, ref_price, limit),
                )
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"reference_hotel": clean_row(ref), "similar_hotels": rows}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/amenity-categories", tags=["Amenities"])
def list_amenity_categories():
    """Lấy toàn bộ trường của `amenity_categories`."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT id, name FROM amenity_categories ORDER BY name")
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"data": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/amenities", tags=["Amenities"])
def list_amenities(
    category_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    page_limit: tuple[int, int, int] = Depends(pagination_params),
):
    """Lấy danh mục tiện ích, bao phủ toàn bộ trường của `amenities` và tên category."""
    page, limit, offset = page_limit
    clauses = []
    params = []
    if category_id is not None:
        clauses.append("a.category_id = %s")
        params.append(category_id)
    for clause, value in [("a.category ILIKE %s", category), ("a.name ILIKE %s", name)]:
        cleaned = clean_param(value)
        if cleaned:
            clauses.append(clause)
            params.append(f"%{cleaned}%")
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM amenities a LEFT JOIN amenity_categories ac ON ac.id = a.category_id {where_sql}", tuple(params))
                total = cur.fetchone()["count"]
                cur.execute(
                    f"""
                    SELECT a.id, a.name, a.category, a.category_id, ac.name AS category_name
                    FROM amenities a
                    LEFT JOIN amenity_categories ac ON ac.id = a.category_id
                    {where_sql}
                    ORDER BY ac.name NULLS LAST, a.name
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params + [limit, offset]),
                )
                rows = [clean_row(row) for row in cur.fetchall()]
        return paginated_response(total, page, limit, rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/hotel-suitability", tags=["Suitability"])
def list_hotel_suitability(
    hotel_id: Optional[int] = Query(None),
    tag: Optional[str] = Query(None),
    page_limit: tuple[int, int, int] = Depends(pagination_params),
):
    """Lấy toàn bộ trường của `hotel_suitability` trên toàn hệ thống."""
    page, limit, offset = page_limit
    clauses = []
    params = []
    if hotel_id is not None:
        clauses.append("hs.hotel_id = %s")
        params.append(hotel_id)
    tag_value = clean_param(tag)
    if tag_value:
        clauses.append("hs.suitable_for_tag ILIKE %s")
        params.append(f"%{tag_value}%")
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM hotel_suitability hs {where_sql}", tuple(params))
                total = cur.fetchone()["count"]
                cur.execute(
                    f"""
                    SELECT hs.*, h.name AS hotel_name, h.city AS hotel_city
                    FROM hotel_suitability hs
                    JOIN hotels h ON h.id = hs.hotel_id
                    {where_sql}
                    ORDER BY hs.score DESC NULLS LAST, hs.suitable_for_tag
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params + [limit, offset]),
                )
                rows = [clean_row(row) for row in cur.fetchall()]
        return paginated_response(total, page, limit, rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/reviews", tags=["Reviews"])
def list_reviews(
    hotel_id: Optional[int] = Query(None),
    rating_min: Optional[float] = Query(None, ge=0, le=10),
    reviewer_country: Optional[str] = Query(None),
    page_limit: tuple[int, int, int] = Depends(pagination_params),
):
    """Lấy toàn bộ trường của `reviews` trên toàn hệ thống."""
    page, limit, offset = page_limit
    clauses = []
    params = []
    if hotel_id is not None:
        clauses.append("r.hotel_id = %s")
        params.append(hotel_id)
    if rating_min is not None:
        clauses.append("r.rating >= %s")
        params.append(rating_min)
    country = clean_param(reviewer_country)
    if country:
        clauses.append("r.reviewer_country ILIKE %s")
        params.append(f"%{country}%")
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM reviews r {where_sql}", tuple(params))
                total = cur.fetchone()["count"]
                cur.execute(
                    f"""
                    SELECT r.*, h.name AS hotel_name, h.city AS hotel_city
                    FROM reviews r
                    JOIN hotels h ON h.id = r.hotel_id
                    {where_sql}
                    ORDER BY r.review_date DESC NULLS LAST, r.id DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params + [limit, offset]),
                )
                rows = [clean_row(row) for row in cur.fetchall()]
        return paginated_response(total, page, limit, rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/reviews/{review_id}", tags=["Reviews"])
def get_review(review_id: int):
    """Lấy chi tiết một review theo `reviews.id`."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT r.*, h.name AS hotel_name, h.city AS hotel_city
                    FROM reviews r
                    JOIN hotels h ON h.id = r.hotel_id
                    WHERE r.id = %s
                    """,
                    (review_id,),
                )
                row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Không tìm thấy review.")
        return clean_row(row)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/review-grades", tags=["Reviews"])
def list_review_grades(hotel_id: Optional[int] = Query(None), grade_name: Optional[str] = Query(None)):
    """Lấy toàn bộ trường của `review_grades`."""
    clauses = []
    params = []
    if hotel_id is not None:
        clauses.append("rg.hotel_id = %s")
        params.append(hotel_id)
    grade = clean_param(grade_name)
    if grade:
        clauses.append("rg.grade_name ILIKE %s")
        params.append(f"%{grade}%")
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT rg.*, h.name AS hotel_name, h.city AS hotel_city
                    FROM review_grades rg
                    JOIN hotels h ON h.id = rg.hotel_id
                    {where_sql}
                    ORDER BY rg.hotel_id, rg.grade_name
                    """,
                    tuple(params),
                )
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"data": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/review-aspects", tags=["Reviews"])
def list_review_aspects(hotel_id: Optional[int] = Query(None), aspect_name: Optional[str] = Query(None)):
    """Lấy toàn bộ trường của `review_aspects`."""
    clauses = []
    params = []
    if hotel_id is not None:
        clauses.append("ra.hotel_id = %s")
        params.append(hotel_id)
    aspect = clean_param(aspect_name)
    if aspect:
        clauses.append("ra.aspect_name ILIKE %s")
        params.append(f"%{aspect}%")
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    f"""
                    SELECT ra.*, h.name AS hotel_name, h.city AS hotel_city
                    FROM review_aspects ra
                    JOIN hotels h ON h.id = ra.hotel_id
                    {where_sql}
                    ORDER BY ra.hotel_id, ra.mentioned DESC NULLS LAST, ra.aspect_name
                    """,
                    tuple(params),
                )
                rows = [clean_row(row) for row in cur.fetchall()]
        return {"data": rows}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/text-chunks", tags=["Text Chunks"])
def list_text_chunks(
    hotel_id: Optional[int] = Query(None),
    chunk_type: Optional[str] = Query(None),
    include_embedding: bool = Query(False, description="Đặt true nếu cần trả embedding dạng text."),
    page_limit: tuple[int, int, int] = Depends(pagination_params),
):
    """Lấy toàn bộ trường của `text_chunks`; embedding trả `null` mặc định để response nhẹ."""
    page, limit, offset = page_limit
    clauses = []
    params = []
    if hotel_id is not None:
        clauses.append("tc.hotel_id = %s")
        params.append(hotel_id)
    chunk = clean_param(chunk_type)
    if chunk:
        clauses.append("tc.chunk_type = %s")
        params.append(chunk)
    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    embedding_select = "tc.embedding::text AS embedding" if include_embedding else "NULL AS embedding"
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(f"SELECT COUNT(*) AS count FROM text_chunks tc {where_sql}", tuple(params))
                total = cur.fetchone()["count"]
                cur.execute(
                    f"""
                    SELECT tc.id, tc.hotel_id, tc.chunk_type, tc.content, {embedding_select}, tc.metadata, tc.created_at,
                           h.name AS hotel_name, h.city AS hotel_city
                    FROM text_chunks tc
                    JOIN hotels h ON h.id = tc.hotel_id
                    {where_sql}
                    ORDER BY tc.created_at DESC NULLS LAST, tc.id DESC
                    LIMIT %s OFFSET %s
                    """,
                    tuple(params + [limit, offset]),
                )
                rows = [clean_row(row) for row in cur.fetchall()]
        return paginated_response(total, page, limit, rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
