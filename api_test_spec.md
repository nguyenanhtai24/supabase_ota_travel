# API Test Spec V2 - Based on 520 `cleaned_test` Hotels

Tài liệu này dùng để test Swagger/Postman cho backend FastAPI hiện tại.

Nguồn dữ liệu test: 520 file JSON trong `cleaned_test/*.json`, đã sinh ra `insert_data.sql`.

Golden hotel dùng xuyên suốt spec:

```json
{
  "hotel_id": 1015998,
  "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "property_type": "Hotel",
  "accommodation_type": "Resort",
  "star_rating": 5.0,
  "is_luxury": true,
  "review_score": 9.0,
  "review_count": 4121,
  "address": "Đảo Rều, Bãi Cháy, Hạ Long, Hạ Long, Việt Nam",
  "area": "Hạ Long",
  "city": "Hạ Long",
  "country": "Việt Nam",
  "city_id": 10779,
  "latitude": 20.941213607788086,
  "longitude": 107.02555084228516,
  "check_in_from": "15:00",
  "check_out_until": "12:00"
}
```

Golden related data từ `cleaned_test/hotel_1015998.json`:

- Amenity: `Bàn tiếp tân 24 giờ`
- Amenity category: `Tiện nghi phổ biến`
- Suitability tag: `Cặp đôi`
- Nearby place: `Bến tàu du lịch Bãi Cháy`, type `Bến Cảng và Bến Đò`, distance `0.82`
- Room type id: `7558808`, room name `Phòng Deluxe Có Giường Cỡ King (deluxe king)`
- Activity id: `1587993`, title `[MỚI RA MẮT] Du thuyền hạng sang Diamond Era - Vịnh Hạ Long, Hang Sửng Sốt & Đảo Ti Tốp`
- Review grade: `Sự thoải mái và chất lượng phòng`, score `9.4`
- Review aspect: `Dịch vụ`, mentioned `146`, positive_pct `74.0`
- First reviewer: `Nak`, country `Hàn Quốc`, rating `10.0`

Assumption để test các endpoint dùng `SERIAL id`:

- Chạy `init_db.sql` trước, sau đó chạy `insert_data.sql` trên database trống.
- Khi đó các bản ghi đầu tiên trong các bảng serial thuộc hotel `1015998`:
  - `hotel_images.id = 1`
  - `reviews.id = 1`
  - `rooms.id = 1`
  - `nearby_places.id = 1`
  - `activities.id = 1`
- Nếu DB của bạn đã import nhiều lần hoặc sequence khác, hãy gọi endpoint list trước rồi dùng `id` trả về cho endpoint detail.

Base URL:

```text
http://localhost:5000
```

Render URL:

```text
https://<render-service-url>
```

Header chung, trừ `/health`:

```http
X-API-Key: <API_SECRET_KEY>
```

## 1. Health

Input:

```http
GET /health
```

Expected status: `200`

Expected output:

```json
{
  "status": "OK",
  "version": "2.0.0",
  "message": "OTA Travel Assistant API đang hoạt động bình thường."
}
```

## 2. List Hotels By City

Input:

```http
GET /api/hotels?city=Hạ%20Long&accommodation_type=Resort&star_rating_min=5&review_score_min=9&is_luxury=true&page=1&limit=20&sort_by=review_score:desc
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "total_pages": 1,
  "data": [
    {
      "id": 1015998,
      "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "property_type": "Hotel",
      "accommodation_type": "Resort",
      "star_rating": 5.0,
      "is_luxury": true,
      "review_score": 9.0,
      "review_count": 4121,
      "address": "Đảo Rều, Bãi Cháy, Hạ Long, Hạ Long, Việt Nam",
      "city": "Hạ Long",
      "city_id": 10779,
      "area": "Hạ Long",
      "country": "Việt Nam",
      "latitude": 20.941213607788086,
      "longitude": 107.02555084228516,
      "source_url": "https://www.agoda.com/vinpearl-resort-spa-h-long/hotel/halong-vn.html?hotel=1015998&currency=VND&checkIn=2026-06-13&checkOut=2026-06-14&rooms=1&adults=2&children=0",
      "min_room_price": 5000000.0,
      "primary_image": "https://pix8.agoda.net/hotelImages/1015998/-1/5393e9bfae5b5927c4f3f3d2dd5088d7.jpg?ce=0&s=1024x768",
      "amenities": [
        {
          "name": "Bàn tiếp tân 24 giờ"
        }
      ],
      "suitability": [
        {
          "tag": "Cặp đôi"
        }
      ]
    }
  ]
}
```

## 3. List Hotels With Amenity, Suitability, Nearby Place

Input:

```http
GET /api/hotels?city=Hạ%20Long&amenities=Bàn%20tiếp%20tân%2024%20giờ&suitable_for=Cặp%20đôi&nearby_place_name=Bến%20tàu%20du%20lịch%20Bãi%20Cháy&distance_max_km=1&sort_by=distance:asc&page=1&limit=10
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 10,
  "data": [
    {
      "id": 1015998,
      "city": "Hạ Long",
      "amenities": [
        {
          "name": "Bàn tiếp tân 24 giờ"
        }
      ],
      "suitability": [
        {
          "tag": "Cặp đôi"
        }
      ]
    }
  ]
}
```

## 4. Compare Hotels

Input:

```http
GET /api/hotels/compare?ids=1015998,4947690
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "hotels": [
    {
      "id": 1015998,
      "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "city": "Hạ Long",
      "accommodation_type": "Resort",
      "review_score": 9.0
    },
    {
      "id": 4947690,
      "name": "Melia Vinpearl Riverfront Đà Nẵng (Melia Vinpearl Danang Riverfront)",
      "city": "Đà Nẵng",
      "accommodation_type": "Khách sạn",
      "review_score": 8.9
    }
  ]
}
```

## 5. Hotel Detail

Input:

```http
GET /api/hotels/1015998
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "id": 1015998,
  "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "property_type": "Hotel",
  "accommodation_type": "Resort",
  "star_rating": 5.0,
  "is_luxury": true,
  "review_score": 9.0,
  "review_count": 4121,
  "address": "Đảo Rều, Bãi Cháy, Hạ Long, Hạ Long, Việt Nam",
  "city": "Hạ Long",
  "area": "Hạ Long",
  "country": "Việt Nam",
  "images": [
    {
      "hotel_id": 1015998,
      "is_primary": true
    }
  ],
  "policy": {
    "hotel_id": 1015998,
    "check_in_from": "15:00",
    "check_out_until": "12:00",
    "service_fee_pct": 5.0,
    "pet_policy": "Không được phép đưa thú nuôi vào",
    "deposit_required": false
  },
  "amenities": [
    {
      "name": "Bàn tiếp tân 24 giờ"
    }
  ],
  "suitability": [
    {
      "suitable_for_tag": "Cặp đôi"
    }
  ],
  "review_grades": [
    {
      "grade_name": "Sự thoải mái và chất lượng phòng",
      "grade_score": 9.4
    }
  ],
  "review_aspects": [
    {
      "aspect_name": "Dịch vụ",
      "mentioned": 146,
      "positive_pct": 74.0
    }
  ],
  "reviews": [
    {
      "reviewer_name": "Nak",
      "reviewer_country": "Hàn Quốc",
      "rating": 10.0
    }
  ],
  "rooms": [
    {
      "room_type_id": 7558808,
      "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)"
    }
  ],
  "nearby_places": [
    {
      "name": "Bến tàu du lịch Bãi Cháy",
      "distance_km": 0.82
    }
  ],
  "activities": [
    {
      "activity_id": 1587993
    }
  ]
}
```

## 6. Hotel Images

Input:

```http
GET /api/hotels/1015998/images
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "images": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "url": "https://pix8.agoda.net/hotelImages/1015998/-1/5393e9bfae5b5927c4f3f3d2dd5088d7.jpg?ce=0&s=1024x768",
      "is_primary": true
    }
  ]
}
```

## 7. Hotel Policies

Input:

```http
GET /api/hotels/1015998/policies
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "check_in_from": "15:00",
  "check_out_until": "12:00",
  "service_fee_pct": 5.0,
  "child_policy": "Không có thông tin",
  "pet_policy": "Không được phép đưa thú nuôi vào",
  "deposit_required": false,
  "policy_notes": [
    "Giường phụ và Phụ phí cho người ở thêm"
  ]
}
```

## 8. Hotel Amenities

Input:

```http
GET /api/hotels/1015998/amenities
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "amenities": [
    {
      "hotel_id": 1015998,
      "amenity_id": 1,
      "name": "Bàn tiếp tân 24 giờ",
      "category": "Tiện nghi phổ biến",
      "category_id": 1,
      "category_name": "Tiện nghi phổ biến"
    }
  ]
}
```

## 9. Hotel Suitability

Input:

```http
GET /api/hotels/1015998/suitability
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "suitability": [
    {
      "hotel_id": 1015998,
      "suitable_for_tag": "Khách đi công tác"
    },
    {
      "hotel_id": 1015998,
      "suitable_for_tag": "Cặp đôi"
    }
  ]
}
```

## 10. Hotel Reviews Bundle

Input:

```http
GET /api/hotels/1015998/reviews?page=1&limit=20
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "total": 10,
  "page": 1,
  "limit": 20,
  "total_pages": 1,
  "data": [
    {
      "hotel_id": 1015998,
      "reviewer_name": "Nak",
      "reviewer_country": "Hàn Quốc",
      "rating": 10.0,
      "title": "Vịnh Hạ Long hòn đảo xinh đẹp"
    }
  ],
  "grades": [
    {
      "hotel_id": 1015998,
      "grade_name": "Sự thoải mái và chất lượng phòng",
      "grade_score": 9.4
    }
  ],
  "aspects": [
    {
      "hotel_id": 1015998,
      "aspect_name": "Dịch vụ",
      "mentioned": 146,
      "positive_pct": 74.0
    }
  ]
}
```

## 11. Hotel Rooms

Input:

```http
GET /api/hotels/1015998/rooms?min_occupancy=2&room_view=Hướng%20Vườn&price_max=5000000&sort_by=price:asc&page=1&limit=20
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "room_type_id": 7558808,
      "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
      "price": 5000000.0,
      "room_size": "38 m²",
      "max_occupancy": 3,
      "bed_type": "1 giường lớn",
      "room_view": "Hướng Vườn",
      "review_score": 9.353
    }
  ]
}
```

## 12. Hotel Nearby Places

Input:

```http
GET /api/hotels/1015998/nearby-places?type=Bến%20Cảng%20và%20Bến%20Đò&distance_max_km=1
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "nearby_places": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "name": "Bến tàu du lịch Bãi Cháy",
      "type": "Bến Cảng và Bến Đò",
      "distance_km": 0.82,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 13. Hotel Activities

Input:

```http
GET /api/hotels/1015998/activities?price_max=1000000&review_score_min=4.5&sort_by=review_score:desc
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "hotel_id": 1015998,
  "activities": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "activity_id": 1587993,
      "title": "[MỚI RA MẮT] Du thuyền hạng sang Diamond Era - Vịnh Hạ Long, Hang Sửng Sốt & Đảo Ti Tốp",
      "price_amount": 853886.0,
      "review_score": 4.9,
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 14. Hotel Location

Input:

```http
GET /api/hotels/1015998/location
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "id": 1015998,
  "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "address": "Đảo Rều, Bãi Cháy, Hạ Long, Hạ Long, Việt Nam",
  "city": "Hạ Long",
  "city_id": 10779,
  "area": "Hạ Long",
  "country": "Việt Nam",
  "latitude": 20.941213607788086,
  "longitude": 107.02555084228516,
  "nearby_places": [
    {
      "name": "Bến tàu du lịch Bãi Cháy",
      "distance_km": 0.82
    }
  ]
}
```

## 15. Hotel Text Chunks

Input:

```http
GET /api/hotels/1015998/text-chunks?include_embedding=false
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output vì bạn chưa insert bảng `text_chunks`:

```json
{
  "hotel_id": 1015998,
  "text_chunks": []
}
```

## 16. Similar Hotels

Input:

```http
GET /api/hotels/1015998/similar?limit=5
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "reference_hotel": {
    "id": 1015998,
    "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
    "city": "Hạ Long",
    "accommodation_type": "Resort",
    "min_room_price": 5000000.0
  },
  "similar_hotels": []
}
```

Nếu trong 520 khách sạn có resort khác cùng `city`, `accommodation_type`, và khoảng giá tương đương, `similar_hotels` sẽ là mảng có phần tử.

## 17. Global Rooms

Input:

```http
GET /api/rooms?hotel_id=1015998&city=Hạ%20Long&min_occupancy=2&price_max=5000000&sort_by=price:asc&page=1&limit=20
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "room_type_id": 7558808,
      "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
      "price": 5000000.0,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 18. Room Detail

Input:

```http
GET /api/rooms/1
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "id": 1,
  "hotel_id": 1015998,
  "room_type_id": 7558808,
  "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
  "price": 5000000.0,
  "room_size": "38 m²",
  "max_occupancy": 3,
  "bed_type": "1 giường lớn",
  "room_view": "Hướng Vườn",
  "review_score": 9.353,
  "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "hotel_city": "Hạ Long"
}
```

## 19. Global Nearby Places

Input:

```http
GET /api/nearby-places?city=Hạ%20Long&name=Bến%20tàu%20du%20lịch%20Bãi%20Cháy&type=Bến%20Cảng%20và%20Bến%20Đò&distance_max_km=1&page=1&limit=20
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "name": "Bến tàu du lịch Bãi Cháy",
      "type": "Bến Cảng và Bến Đò",
      "distance_km": 0.82,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 20. Place Categories

Input:

```http
GET /api/place-categories
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "data": [
    {
      "id": 1,
      "name": "Bến Cảng và Bến Đò"
    }
  ]
}
```

## 21. Global Activities

Input:

```http
GET /api/activities?hotel_id=1015998&city=Hạ%20Long&title=Diamond%20Era&price_max=1000000&review_score_min=4.5&sort_by=review_score:desc&page=1&limit=20
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "activity_id": 1587993,
      "title": "[MỚI RA MẮT] Du thuyền hạng sang Diamond Era - Vịnh Hạ Long, Hang Sửng Sốt & Đảo Ti Tốp",
      "price_amount": 853886.0,
      "review_score": 4.9,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 22. Activity Detail

Input:

```http
GET /api/activities/1
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "id": 1,
  "hotel_id": 1015998,
  "activity_id": 1587993,
  "title": "[MỚI RA MẮT] Du thuyền hạng sang Diamond Era - Vịnh Hạ Long, Hang Sửng Sốt & Đảo Ti Tốp",
  "price_amount": 853886.0,
  "review_score": 4.9,
  "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "hotel_city": "Hạ Long"
}
```

## 23. Amenity Categories

Input:

```http
GET /api/amenity-categories
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "data": [
    {
      "id": 1,
      "name": "Tiện nghi phổ biến"
    }
  ]
}
```

## 24. Amenities

Input:

```http
GET /api/amenities?name=Bàn%20tiếp%20tân%2024%20giờ&category=Tiện%20nghi%20phổ%20biến&page=1&limit=20
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "name": "Bàn tiếp tân 24 giờ",
      "category": "Tiện nghi phổ biến",
      "category_id": 1,
      "category_name": "Tiện nghi phổ biến"
    }
  ]
}
```

## 25. Global Hotel Suitability

Input:

```http
GET /api/hotel-suitability?hotel_id=1015998&tag=Cặp%20đôi&page=1&limit=20
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "hotel_id": 1015998,
      "suitable_for_tag": "Cặp đôi",
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 26. Global Reviews

Input:

```http
GET /api/reviews?hotel_id=1015998&rating_min=10&reviewer_country=Hàn%20Quốc&page=1&limit=20
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "total": 1,
  "page": 1,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "reviewer_name": "Nak",
      "reviewer_country": "Hàn Quốc",
      "rating": 10.0,
      "title": "Vịnh Hạ Long hòn đảo xinh đẹp",
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 27. Review Detail

Input:

```http
GET /api/reviews/1
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "id": 1,
  "hotel_id": 1015998,
  "reviewer_name": "Nak",
  "reviewer_country": "Hàn Quốc",
  "rating": 10.0,
  "title": "Vịnh Hạ Long hòn đảo xinh đẹp",
  "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
  "hotel_city": "Hạ Long"
}
```

## 28. Review Grades

Input:

```http
GET /api/review-grades?hotel_id=1015998&grade_name=Sự%20thoải%20mái%20và%20chất%20lượng%20phòng
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "data": [
    {
      "hotel_id": 1015998,
      "grade_name": "Sự thoải mái và chất lượng phòng",
      "grade_score": 9.4,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 29. Review Aspects

Input:

```http
GET /api/review-aspects?hotel_id=1015998&aspect_name=Dịch%20vụ
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "data": [
    {
      "hotel_id": 1015998,
      "aspect_name": "Dịch vụ",
      "mentioned": 146,
      "positive_pct": 74.0,
      "hotel_name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
      "hotel_city": "Hạ Long"
    }
  ]
}
```

## 30. Global Text Chunks

Input:

```http
GET /api/text-chunks?hotel_id=1015998&chunk_type=hotel_overview&include_embedding=false&page=1&limit=20
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output vì bạn chưa insert bảng `text_chunks`:

```json
{
  "total": 0,
  "page": 1,
  "limit": 20,
  "total_pages": 0,
  "data": []
}
```

## 31. Hotel Combo

Input:

```http
GET /api/hotels/1015998/combo?nights=2&guests=2&include_activities=true
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "hotel": {
    "id": 1015998,
    "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)"
  },
  "room": {
    "id": 1,
    "hotel_id": 1015998,
    "room_type_id": 7558808,
    "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
    "price": 5000000.0,
    "max_occupancy": 3
  },
  "nights": 2,
  "guests": 2,
  "activities": [
    {
      "id": 1,
      "hotel_id": 1015998,
      "activity_id": 1587993,
      "price_amount": 853886.0,
      "review_score": 4.9
    }
  ],
  "room_total": 10000000.0,
  "activities_total": 1707772.0,
  "estimated_total": 11707772.0
}
```

## 32. Combo Suggest

Input:

```http
GET /api/hotels/combo-suggest?city=Hạ%20Long&budget_total=12000000&guests=2&nights=2&suitable_for=Cặp%20đôi&limit=5
X-API-Key: <API_SECRET_KEY>
```

Expected status: `200`

Expected output:

```json
{
  "data": [
    {
      "hotel": {
        "id": 1015998,
        "name": "Vinpearl Resort & Spa Hạ Long (Vinpearl Resort & Spa Ha Long)",
        "city": "Hạ Long",
        "room_id": 1,
        "room_name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
        "room_price": 5000000.0,
        "max_occupancy": 3,
        "room_view": "Hướng Vườn",
        "bed_type": "1 giường lớn"
      },
      "room": {
        "id": 1,
        "name": "Phòng Deluxe Có Giường Cỡ King (deluxe king)",
        "price": 5000000.0,
        "max_occupancy": 3,
        "room_view": "Hướng Vườn",
        "bed_type": "1 giường lớn"
      },
      "activities": [
        {
          "activity_id": 1587993,
          "price_amount": 853886.0
        }
      ],
      "room_total": 10000000.0,
      "activities_total": 1707772.0,
      "estimated_total": 11707772.0,
      "remaining_budget": 292228.0
    }
  ]
}
```

## Negative Tests

### 33. Missing API Key

Input:

```http
GET /api/hotels
```

Expected status: `401`

Expected output:

```json
{
  "detail": "Invalid or missing API Key. Provide it via 'X-API-Key' header."
}
```

### 34. Hotel Not Found

Input:

```http
GET /api/hotels/999999999
X-API-Key: <API_SECRET_KEY>
```

Expected status: `404`

Expected output:

```json
{
  "detail": "Không tìm thấy khách sạn."
}
```

### 35. Invalid Compare IDs

Input:

```http
GET /api/hotels/compare?ids=abc,xyz
X-API-Key: <API_SECRET_KEY>
```

Expected status: `400`

Expected output:

```json
{
  "detail": "ids phải chứa ít nhất một số nguyên."
}
```

