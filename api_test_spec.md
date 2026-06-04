# Tài Liệu Đặc Tả Test Cases API (API Test Specification)

Tài liệu này định nghĩa danh sách tham số cần điền (Request Parameters) và cấu trúc dữ liệu trả về mong muốn (Expected Output) của tất cả 16 endpoint trong hệ thống OTA Travel Assistant API. Các ví dụ được xây dựng dựa trên dữ liệu thực tế đã import từ thư mục `processed/` (ví dụ: khách sạn Melia Vinpearl Riverfront Đà Nẵng - ID `4947690`).

---

## 🔑 Cấu Hình Header Chung
Tất cả các endpoint (trừ `/health`) yêu cầu truyền thông tin xác thực sau qua Header:
- **Header Key**: `X-API-Key`
- **Header Value**: `<token_của_bạn>` (Ví dụ ở local: `ota_sk_7f3d9b2e1a4c8f6e5d3a`)

---

## 📋 Danh Sách Test Cases Cho 16 Endpoints

### 1. GET /health
Kiểm tra trạng thái hoạt động của hệ thống. Không yêu cầu API Key.

* **Tham số cần điền**: Không có.
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "status": "OK",
    "version": "2.0.0",
    "message": "OTA Travel Assistant API đang hoạt động bình thường."
  }
  ```

---

### 2. GET /api/hotels
Tìm kiếm và lọc danh sách khách sạn.

* **Tham số cần điền**:
  * `city` (Query, Optional): `Đà Nẵng`
  * `accommodation_type` (Query, Optional): `Khách sạn`
  * `price_min` (Query, Optional): `1000000`
  * `price_max` (Query, Optional): `3000000`
  * `review_score_min` (Query, Optional): `8.0`
  * `star_rating` (Query, Optional): `5`
  * `is_luxury` (Query, Optional): `false`
  * `amenities` (Query, Optional): `Hồ bơi,Spa` (Phân tách bằng dấu phẩy)
  * `suitable_for` (Query, Optional): `Cặp đôi,Gia đình có trẻ nhỏ`
  * `nearby_place_name` (Query, Optional): `Sân bay Đà Nẵng`
  * `distance_max_km` (Query, Optional): `5.0`
  * `sort_by` (Query, Optional): `distance:asc` (Các giá trị khác: `review_score:desc`, `price:asc`, `price:desc`)
  * `page` (Query, Optional): `1` (Mặc định: `1`)
  * `limit` (Query, Optional): `20` (Mặc định: `20`)
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "total": 1,
    "page": 1,
    "limit": 20,
    "data": [
      {
        "id": 4947690,
        "name": "Melia Vinpearl Riverfront Đà Nẵng",
        "accommodation_type": "Khách sạn",
        "star_rating": 5.0,
        "is_luxury": false,
        "review_score": 8.9,
        "review_count": 10921,
        "address": "341 Đ. Trần Hưng Đạo, An Hải Bắc, Sơn Trà, Đà Nẵng",
        "city": "Đà Nẵng",
        "latitude": 16.0708026885986,
        "longitude": 108.229141235352,
        "description": "Khám phá Melia Vinpearl Riverfront Đà Nẵng...",
        "amenities": ["Bàn tiếp tân [24 giờ]", "Hồ bơi", "Spa"],
        "suitable_for": ["Khách đi công tác", "Cặp đôi"],
        "policyNotes": [],
        "useful_info": {
          "Nhận phòng từ": "14:00",
          "Trả phòng đến": "12:00"
        },
        "images": [
          "https://pix8.agoda.net/hotelImages/4947690/..."
        ],
        "rooms": {
          "min_price": 1425768.0
        },
        "nearby_places": [
          {
            "name": "Sân bay Đà Nẵng",
            "type": "Transit",
            "distance_km": 3.5
          }
        ]
      }
    ]
  }
  ```

---

### 3. GET /api/hotels/{id}
Lấy thông tin chi tiết đầy đủ của một khách sạn cụ thể.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690` (Kiểu số nguyên)
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "id": 4947690,
    "name": "Melia Vinpearl Riverfront Đà Nẵng",
    "accommodation_type": "Khách sạn",
    "star_rating": 5.0,
    "is_luxury": false,
    "review_score": 8.9,
    "review_count": 10921,
    "address": "341 Đ. Trần Hưng Đạo...",
    "city": "Đà Nẵng",
    "latitude": 16.0708026885986,
    "longitude": 108.229141235352,
    "description": "Khám phá Melia Vinpearl Riverfront Đà Nẵng...",
    "amenities": ["Bàn tiếp tân [24 giờ]", "Hồ bơi"],
    "suitable_for": ["Cặp đôi", "Khách đi công tác"],
    "useful_info": {
      "Nhận phòng từ": "14:00",
      "Trả phòng đến": "12:00"
    },
    "policyNotes": [],
    "images": [
      "https://pix8.agoda.net/hotelImages/4947690/..."
    ],
    "reviews_detail": [
      {
        "date": "05 tháng 5 2024",
        "text": "Địa điểm tuyệt vời, ngay bên sông...",
        "rating": 10.0,
        "reviewer_name": "Thắm"
      }
    ],
    "source_url": "https://www.agoda.com/..."
  }
  ```

---

### 4. GET /api/hotels/{id}/images
Lấy tất cả hình ảnh của một khách sạn.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "hotel_id": 4947690,
    "hotel_name": "Melia Vinpearl Riverfront Đà Nẵng",
    "images": [
      "https://pix8.agoda.net/hotelImages/4947690/0/bfb51fa3976c865ea22b803dd1b7ca78.jpeg",
      "https://pix8.agoda.net/hotelImages/4947690/0/..."
    ]
  }
  ```

---

### 5. GET /api/hotels/{id}/policies
Lấy chính sách của khách sạn.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "hotel_id": 4947690,
    "policyNotes": [],
    "useful_info": {
      "Nhận phòng từ": "14:00",
      "Trả phòng đến": "12:00",
      "Số lượng phòng": "864",
      "Phí đưa đón sân bay": "350000 VND"
    }
  }
  ```

---

### 6. GET /api/hotels/{id}/reviews
Lấy phân tích đánh giá chi tiết (điểm số từng tiêu chí và các tag đặc trưng).

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "hotel_id": 4947690,
    "review_score": 8.9,
    "review_count": 10921,
    "reviews_detail": {
      "grades": {
        "location": 9.0,
        "cleanliness": 9.4,
        "service": 9.2,
        "facilities": 8.7,
        "value": 9.1
      },
      "tags": [
        "nhân viên thân thiện",
        "vị trí đẹp",
        "phòng sạch sẽ",
        "view tốt",
        "đáng đồng tiền"
      ]
    }
  }
  ```

---

### 7. GET /api/hotels/{id}/location
Lấy tọa độ bản đồ và danh sách đầy đủ địa danh lân cận của khách sạn.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "hotel_id": 4947690,
    "name": "Melia Vinpearl Riverfront Đà Nẵng",
    "address": "341 Đ. Trần Hưng Đạo...",
    "city": "Đà Nẵng",
    "latitude": 16.0708026885986,
    "longitude": 108.229141235352,
    "nearby_places": [
      {
        "id": 12,
        "hotel_id": 4947690,
        "name": "Sân bay Quốc tế Đà Nẵng (DAD)",
        "type": "Sân bay",
        "distance_km": 5.1
      }
    ]
  }
  ```

---

### 8. GET /api/hotels/{id}/rooms
Lấy danh sách các loại phòng hiện có của khách sạn kèm theo các bộ lọc.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
  * `min_occupancy` (Query, Optional): `2`
  * `room_view` (Query, Optional): `sông`
  * `sort_by` (Query, Optional): `price:asc` (Hoặc `price:desc`)
  * `limit` (Query, Optional): `100` (Mặc định: `100`)
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "hotel_id": 4947690,
    "rooms": [
      {
        "id": 45,
        "hotel_id": 4947690,
        "room_type_id": "494769001",
        "name": "Phòng Deluxe Hướng Sông",
        "price": 1425768.0,
        "room_size": "32 m²",
        "max_occupancy": 2,
        "bed_type": "1 giường King",
        "room_view": "Hướng sông",
        "room_amenities": ["Máy điều hòa", "Wifi miễn phí"],
        "images": [
          "https://pix8.agoda.net/hotelImages/..."
        ],
        "review_score": 9.0
      }
    ]
  }
  ```

---

### 9. GET /api/rooms/{id}
Lấy thông tin chi tiết một phòng cụ thể.

* **Tham số cần điền**:
  * `id` (Path, Required): `45` (ID phòng)
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "id": 45,
    "hotel_id": 4947690,
    "room_type_id": "494769001",
    "name": "Phòng Deluxe Hướng Sông",
    "price": 1425768.0,
    "room_size": "32 m²",
    "max_occupancy": 2,
    "bed_type": "1 giường King",
    "room_view": "Hướng sông",
    "room_amenities": ["Máy điều hòa", "Wifi miễn phí"],
    "images": [
      "https://pix8.agoda.net/hotelImages/...",
      "https://pix8.agoda.net/hotelImages/..."
    ],
    "review_score": 9.0
  }
  ```

---

### 10. GET /api/hotels/{id}/nearby-places
Lấy danh sách các địa điểm lân cận khách sạn.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
  * `type` (Query, Optional): `Sân bay`
  * `distance_max_km` (Query, Optional): `6.0`
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "hotel_id": 4947690,
    "nearby_places": [
      {
        "id": 12,
        "hotel_id": 4947690,
        "name": "Sân bay Quốc tế Đà Nẵng (DAD)",
        "type": "Sân bay",
        "distance_km": 5.1
      }
    ]
  }
  ```

---

### 11. GET /api/hotels/{id}/activities
Lấy danh sách các hoạt động vui chơi liên kết với khách sạn.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
  * `price_max` (Query, Optional): `2000000`
  * `sort_by` (Query, Optional): `price:asc` (Hoặc `review_score:desc`)
  * `limit` (Query, Optional): `3`
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "hotel_id": 4947690,
    "activities": [
      {
        "id": 5,
        "hotel_id": 4947690,
        "title": "Tour Khám phá Ngũ Hành Sơn & Hội An",
        "description": "Tour nửa ngày tham quan danh thắng...",
        "price_amount": 750000.0,
        "review_score": 9.2
      }
    ]
  }
  ```

---

### 12. GET /api/activities
Tìm kiếm các hoạt động giải trí trên toàn hệ thống.

* **Tham số cần điền**:
  * `city` (Query, Optional): `Đà Nẵng`
  * `sort_by` (Query, Optional): `review_score:desc` (Hoặc `price:asc`)
  * `limit` (Query, Optional): `10`
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "data": [
      {
        "id": 5,
        "hotel_id": 4947690,
        "title": "Tour Khám phá Ngũ Hành Sơn & Hội An",
        "description": "Tour nửa ngày tham quan danh thắng...",
        "price_amount": 750000.0,
        "review_score": 9.2,
        "hotel": {
          "name": "Melia Vinpearl Riverfront Đà Nẵng",
          "city": "Đà Nẵng"
        }
      }
    ]
  }
  ```

---

### 13. GET /api/hotels/{id}/combo
Tạo gói combo khách sạn kèm hoạt động ước tính cho khách sạn cụ thể.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
  * `nights` (Query, Optional): `3` (Mặc định: `3`)
  * `guests` (Query, Optional): `2` (Mặc định: `2`)
  * `include_activities` (Query, Optional): `true` (Mặc định: `true`)
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "hotel": {
      "id": 4947690,
      "name": "Melia Vinpearl Riverfront Đà Nẵng",
      "star_rating": 5.0,
      "review_score": 8.9,
      "recommended_room": {
        "name": "Phòng Deluxe Hướng Sông",
        "price": 1425768.0,
        "room_view": "Hướng sông"
      }
    },
    "activities": [
      {
        "id": 5,
        "title": "Tour Khám phá Ngũ Hành Sơn & Hội An",
        "price_amount": 750000.0,
        "review_score": 9.2
      }
    ],
    "estimated_total": 4351536.0
  }
  ```
  *(Cách tính `estimated_total` = [Phòng Deluxe (1,425,768) * 2 đêm] + [Hoạt động (750,000) * 2 khách] = 2,851,536 + 1,500,000 = 4,351,536.0)*

---

### 14. GET /api/hotels/combo-suggest
Đề xuất gói combo khách sạn + hoạt động phù hợp với ngân sách tổng.

* **Tham số cần điền**:
  * `city` (Query, Required): `Đà Nẵng`
  * `budget_total` (Query, Required): `5000000` (Kiểu số thực)
  * `guests` (Query, Optional): `2` (Mặc định: `2`)
  * `nights` (Query, Optional): `3` (Mặc định: `2`)
  * `suitable_for` (Query, Optional): `Cặp đôi`
  * `min_occupancy` (Query, Optional): `2`
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "hotel": {
      "id": 4947690,
      "name": "Melia Vinpearl Riverfront Đà Nẵng",
      "star_rating": 5.0,
      "review_score": 8.9,
      "suitable_for": ["Cặp đôi", "Khách đi công tác"],
      "recommended_room": {
        "name": "Phòng Deluxe Hướng Sông",
        "price": 1425768.0,
        "max_occupancy": 2
      }
    },
    "activities": [
      {
        "id": 5,
        "title": "Tour Khám phá Ngũ Hành Sơn & Hội An",
        "description": "Tour nửa ngày tham quan danh thắng...",
        "price_amount": 750000.0,
        "review_score": 9.2
      }
    ],
    "total_cost": 4351536.0,
    "remaining_budget": 648464.0
  }
  ```

---

### 15. GET /api/hotels/compare
So sánh thông tin của nhiều khách sạn song song.

* **Tham số cần điền**:
  * `ids` (Query, Required): `4947690,4593719` (Danh sách các ID cách nhau bằng dấu phẩy)
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "hotels": [
      {
        "id": 4947690,
        "name": "Melia Vinpearl Riverfront Đà Nẵng",
        "star_rating": 5.0,
        "is_luxury": false,
        "review_score": 8.9,
        "review_count": 10921,
        "reviews_detail": {
          "grades": {
            "location": 9.0,
            "cleanliness": 9.4,
            "service": 9.2,
            "facilities": 8.7,
            "value": 9.1
          }
        },
        "amenities": ["Bàn tiếp tân [24 giờ]", "Hồ bơi"],
        "rooms": {
          "min_price": 1425768.0
        },
        "images": [
          "https://pix8.agoda.net/hotelImages/4947690/..."
        ]
      }
    ]
  }
  ```

---

### 16. GET /api/hotels/{id}/similar
Gợi ý các khách sạn tương tự (cùng thành phố, cùng loại) nhưng rẻ hơn ít nhất 10%.

* **Tham số cần điền**:
  * `id` (Path, Required): `4947690`
* **Kết quả trả về mong muốn (Response)**:
  ```json
  {
    "reference_hotel": {
      "id": 4947690,
      "name": "Melia Vinpearl Riverfront Đà Nẵng",
      "review_score": 8.9,
      "amenities": ["Bàn tiếp tân", "Hồ bơi"],
      "rooms": {
        "min_price": 1425768.0
      }
    },
    "similar_hotels": [
      {
        "id": 1994212,
        "name": "Vinpearl Hoi An Villas",
        "star_rating": 4.0,
        "review_score": 8.2,
        "amenities": ["Wifi", "Bể bơi"],
        "rooms": {
          "min_price": 1100000.0
        },
        "price_saving_pct": 23,
        "images": [
          "https://pix8.agoda.net/..."
        ]
      }
    ]
  }
  ```
