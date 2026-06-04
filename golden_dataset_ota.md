# Golden Dataset — Hệ thống OTA Du lịch

> **Cấu trúc mỗi bản ghi:**
> - 🙋 **Câu hỏi người dùng** — ngôn ngữ tự nhiên như người thật gõ vào chatbot/search bar.
> - 💬 **Phản hồi người dùng mong muốn** — nội dung hiển thị thân thiện, dễ đọc.
> - 📦 **Phản hồi API Backend** — các trường dữ liệu cần trả về từ database để tổng hợp câu trả lời.

---

## Mục lục Nghiệp vụ

| # | Nghiệp vụ | Số câu hỏi |
|---|-----------|-----------|
| 1 | [Tìm kiếm & Lọc Khách sạn](#1-tìm-kiếm--lọc-khách-sạn) | 6 |
| 2 | [Chi tiết Khách sạn](#2-chi-tiết-khách-sạn) | 5 |
| 3 | [Thông tin & Lựa chọn Phòng](#3-thông-tin--lựa-chọn-phòng) | 5 |
| 4 | [Địa điểm Lân cận](#4-địa-điểm-lân-cận) | 4 |
| 5 | [Hoạt động Giải trí](#5-hoạt-động-giải-trí) | 4 |
| 6 | [Gói Combo Khách sạn + Vui chơi](#6-gói-combo-khách-sạn--vui-chơi) | 3 |
| 7 | [So sánh & Gợi ý Cá nhân hóa](#7-so-sánh--gợi-ý-cá-nhân-hóa) | 5 |

---

## 1. Tìm kiếm & Lọc Khách sạn

---

### Q1-01 — Tìm khách sạn theo thành phố

🙋 **Câu hỏi người dùng:**
> "Cho tôi xem danh sách khách sạn ở Đà Nẵng"

💬 **Phản hồi người dùng mong muốn:**
```
Tìm thấy 24 khách sạn tại Đà Nẵng.

1. ★★★★★  Fusion Maia Resort Đà Nẵng
   Loại: Resort  |  Điểm đánh giá: 9.2/10 (1.840 đánh giá)
   Địa chỉ: Võ Nguyên Giáp, Quận Ngũ Hành Sơn
   [Xem chi tiết]

2. ★★★★☆  Marriott Resort & Spa Đà Nẵng
   Loại: Resort  |  Điểm đánh giá: 8.9/10 (2.103 đánh giá)
   Địa chỉ: 07 Trường Sa, Quận Ngũ Hành Sơn
   [Xem chi tiết]
   ...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": { "city": "Đà Nẵng", "page": 1, "limit": 20 },
  "response": {
    "total": 24,
    "page": 1,
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "accommodation_type": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "review_count": "integer",
        "address": "text",
        "city": "varchar",
        "images": ["text — ảnh đại diện [0]"],
        "latitude": "double",
        "longitude": "double"
      }
    ]
  }
}
```

---

### Q1-02 — Lọc theo loại hình lưu trú

🙋 **Câu hỏi người dùng:**
> "Tôi muốn tìm Homestay ở Hội An, giá khoảng 500k–1 triệu một đêm"

💬 **Phản hồi người dùng mong muốn:**
```
Tìm thấy 8 Homestay tại Hội An trong khoảng giá 500.000 – 1.000.000 VND/đêm.

1. Hội An Chic Homestay
   Điểm đánh giá: 8.7 | Giá từ: 650.000 VND/đêm
   Phù hợp: Cặp đôi, Du khách solo
   [Xem chi tiết]
   ...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Hội An",
    "accommodation_type": "Homestay",
    "price_min": 500000,
    "price_max": 1000000
  },
  "response": {
    "total": 8,
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "accommodation_type": "varchar",
        "review_score": "numeric",
        "review_count": "integer",
        "address": "text",
        "suitable_for": ["text[]"],
        "images": ["text — ảnh đại diện [0]"],
        "rooms": {
          "min_price": "numeric — giá phòng rẻ nhất trong khách sạn"
        }
      }
    ]
  }
}
```

---

### Q1-03 — Lọc theo điểm đánh giá cao

🙋 **Câu hỏi người dùng:**
> "Khách sạn nào được đánh giá trên 9 điểm ở Nha Trang?"

💬 **Phản hồi người dùng mong muốn:**
```
5 khách sạn đánh giá xuất sắc (≥ 9.0) tại Nha Trang:

★ Amiana Resort & Villas Nha Trang — 9.4/10 (876 đánh giá)
★ Six Senses Ninh Van Bay — 9.3/10 (543 đánh giá)
★ Mia Resort Nha Trang — 9.1/10 (1.201 đánh giá)
...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Nha Trang",
    "review_score_min": 9.0,
    "sort_by": "review_score:desc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "review_count": "integer",
        "accommodation_type": "varchar",
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

### Q1-04 — Tìm khách sạn hạng sang (Luxury)

🙋 **Câu hỏi người dùng:**
> "Tìm resort 5 sao hạng sang ở Phú Quốc cho tôi"

💬 **Phản hồi người dùng mong muốn:**
```
12 Resort 5 sao hạng sang tại Phú Quốc:

🏆 JW Marriott Phu Quoc Emerald Bay
   Điểm: 9.5/10 | Giá từ: 6.200.000 VND/đêm
   Tiện ích nổi bật: Bể bơi vô cực, Spa cao cấp, Bãi biển riêng
   [Xem chi tiết]
   ...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Phú Quốc",
    "accommodation_type": "Resort",
    "star_rating": 5,
    "is_luxury": true,
    "sort_by": "review_score:desc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "is_luxury": "boolean",
        "star_rating": "numeric",
        "review_score": "numeric",
        "amenities": ["text[] — top 5 tiện ích"],
        "images": ["text — ảnh đại diện [0]"],
        "rooms": {
          "min_price": "numeric"
        }
      }
    ]
  }
}
```

---

### Q1-05 — Lọc theo tiện ích cụ thể

🙋 **Câu hỏi người dùng:**
> "Khách sạn ở Đà Lạt có hồ bơi và cho phép mang thú cưng không?"

💬 **Phản hồi người dùng mong muốn:**
```
Tìm thấy 3 khách sạn tại Đà Lạt có hồ bơi và cho phép thú cưng:

1. Dalat Edensee Lake Resort & Spa
   Điểm: 8.8 | Loại: Resort
   ✓ Hồ bơi ngoài trời  ✓ Cho phép thú cưng (phụ phí)
   [Xem chi tiết]
   ...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Đà Lạt",
    "amenities": ["Hồ bơi", "Cho phép thú cưng"]
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "accommodation_type": "varchar",
        "review_score": "numeric",
        "amenities": ["text[] — toàn bộ danh sách tiện ích"],
        "policyNotes": ["text[] — chính sách thú cưng, phụ phí"],
        "useful_info": "jsonb — chi tiết phí dịch vụ",
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

### Q1-06 — Tìm khách sạn phù hợp đối tượng

🙋 **Câu hỏi người dùng:**
> "Khách sạn nào ở Sầm Sơn phù hợp cho gia đình có trẻ nhỏ?"

💬 **Phản hồi người dùng mong muốn:**
```
10 khách sạn tại Sầm Sơn lý tưởng cho gia đình có trẻ nhỏ:

1. FLC Grand Hotel Sầm Sơn
   Điểm: 8.6 | ★★★★★
   Phù hợp: Gia đình có trẻ nhỏ, Nhóm bạn
   Tiện ích cho trẻ: Hồ bơi trẻ em, Khu vui chơi trong nhà
   [Xem chi tiết]
   ...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Sầm Sơn",
    "suitable_for": "Gia đình có trẻ nhỏ",
    "sort_by": "review_score:desc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "suitable_for": ["text[]"],
        "amenities": ["text[] — lọc các tiện ích liên quan trẻ em"],
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

## 2. Chi tiết Khách sạn

---

### Q2-01 — Xem thông tin tổng quan khách sạn

🙋 **Câu hỏi người dùng:**
> "Cho tôi biết thêm về khách sạn Vinpearl Resort & Spa Nha Trang Bay"

💬 **Phản hồi người dùng mong muốn:**
```
🏨 Vinpearl Resort & Spa Nha Trang Bay
⭐⭐⭐⭐⭐ | Điểm: 9.0/10 (3.421 đánh giá) | Resort Hạng sang

📍 Đảo Hòn Tre, Vĩnh Nguyên, Nha Trang, Khánh Hòa

📝 Mô tả:
Vinpearl Resort & Spa Nha Trang Bay tọa lạc trên đảo Hòn Tre thơ mộng, 
mang đến trải nghiệm nghỉ dưỡng đẳng cấp với bãi biển riêng dài 700m...

🛎 Tiện ích nổi bật:
✓ Bãi biển riêng  ✓ Hồ bơi vô cực  ✓ Spa & Wellness
✓ Nhà hàng cao cấp  ✓ Khu vui chơi trẻ em  ✓ Cáp treo

📌 Phù hợp cho: Cặp đôi, Gia đình, Khách công tác
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}",
  "path_params": { "id": "integer" },
  "response": {
    "id": "integer",
    "name": "varchar",
    "accommodation_type": "varchar",
    "star_rating": "numeric",
    "is_luxury": "boolean",
    "review_score": "numeric",
    "review_count": "integer",
    "address": "text",
    "city": "varchar",
    "latitude": "double",
    "longitude": "double",
    "description": "text",
    "amenities": ["text[]"],
    "suitable_for": ["text[]"],
    "useful_info": "jsonb",
    "policyNotes": ["text[]"],
    "images": ["text[]"],
    "reviews_detail": "jsonb",
    "source_url": "text"
  }
}
```

---

### Q2-02 — Xem hình ảnh khách sạn

🙋 **Câu hỏi người dùng:**
> "Cho tôi xem ảnh của khách sạn này"

💬 **Phản hồi người dùng mong muốn:**
```
📸 Bộ sưu tập ảnh — Vinpearl Resort & Spa Nha Trang Bay
[32 ảnh]

[Ảnh 1: Toàn cảnh resort từ trên cao]
[Ảnh 2: Hồ bơi vô cực hướng biển]
[Ảnh 3: Phòng Suite với view biển]
...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/images",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "hotel_name": "varchar",
    "images": ["text[] — toàn bộ URL ảnh khách sạn"]
  }
}
```

---

### Q2-03 — Xem chính sách & lưu ý đặc biệt

🙋 **Câu hỏi người dùng:**
> "Chính sách nhận phòng và các khoản phụ thu của khách sạn này là gì?"

💬 **Phản hồi người dùng mong muốn:**
```
📋 Chính sách & Lưu ý — Vinpearl Resort & Spa Nha Trang Bay

🕐 Nhận phòng: 14:00 | Trả phòng: 12:00
💳 Phí dịch vụ: 5% trên tổng hóa đơn
🧒 Trẻ em dưới 6 tuổi: Miễn phí (không kèm bữa ăn)
🐾 Thú cưng: Không được phép

⚠️ Lưu ý đặc biệt:
• Yêu cầu đặt cọc thẻ tín dụng khi nhận phòng
• Resort thu phí cáp treo theo chiều
• Booking sớm trước 30 ngày được giảm 15%
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/policies",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "policyNotes": ["text[]"],
    "useful_info": "jsonb — check_in_time, check_out_time, service_fee, child_policy, pet_policy, deposit_required"
  }
}
```

---

### Q2-04 — Xem điểm đánh giá chi tiết

🙋 **Câu hỏi người dùng:**
> "Khách hàng đánh giá khách sạn này như thế nào? Điểm mạnh yếu là gì?"

💬 **Phản hồi người dùng mong muốn:**
```
⭐ Đánh giá chi tiết — Vinpearl Resort & Spa Nha Trang Bay
Tổng điểm: 9.0/10 từ 3.421 đánh giá

Vị trí:         ████████░░  8.5
Sạch sẽ:        █████████░  9.2
Dịch vụ:        █████████░  9.1
Tiện nghi:       ████████░░  8.8
Giá trị:         ███████░░░  7.9

🏷 Tags phổ biến từ khách hàng:
#bãi biển riêng  #nhân viên thân thiện  #hồ bơi đẹp
#phòng rộng rãi  #view biển tuyệt vời
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/reviews",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "review_score": "numeric",
    "review_count": "integer",
    "reviews_detail": "jsonb — grades: { location, cleanliness, service, facilities, value }, tags: [text[]]"
  }
}
```

---

### Q2-05 — Tra cứu vị trí & bản đồ

🙋 **Câu hỏi người dùng:**
> "Khách sạn Amanoi ở đâu, cách trung tâm Phan Rang bao xa?"

💬 **Phản hồi người dùng mong muốn:**
```
📍 Vị trí — Amanoi Resort
Địa chỉ: Vĩnh Hy, Ninh Hải, Ninh Thuận

📏 Khoảng cách:
• Trung tâm Phan Rang: 45 km (~ 55 phút lái xe)
• Sân bay Cam Ranh: 100 km
• Vườn quốc gia Núi Chúa: 2 km

🗺 [Xem bản đồ]
Tọa độ: 11.6982° N, 109.2219° E
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/location",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "name": "varchar",
    "address": "text",
    "city": "varchar",
    "latitude": "double",
    "longitude": "double",
    "nearby_places": [
      {
        "name": "varchar",
        "type": "varchar",
        "distance_km": "numeric"
      }
    ]
  }
}
```

---

## 3. Thông tin & Lựa chọn Phòng

---

### Q3-01 — Xem danh sách loại phòng

🙋 **Câu hỏi người dùng:**
> "Khách sạn này có những loại phòng nào?"

💬 **Phản hồi người dùng mong muốn:**
```
🛏 Các loại phòng — Vinpearl Resort & Spa Nha Trang Bay

1. Deluxe Garden View
   Diện tích: 38 m²  |  2 người  |  Giường đôi King
   Giá từ: 2.800.000 VND/đêm  |  Điểm: 8.9
   [Xem chi tiết]

2. Premier Ocean View
   Diện tích: 48 m²  |  2 người  |  Giường đôi King
   Giá từ: 4.200.000 VND/đêm  |  Điểm: 9.2
   [Xem chi tiết]

3. Family Suite
   Diện tích: 72 m²  |  4 người  |  2 giường đôi
   Giá từ: 6.500.000 VND/đêm  |  Điểm: 9.0
   [Xem chi tiết]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/rooms",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "rooms": [
      {
        "id": "integer",
        "room_type_id": "bigint",
        "name": "varchar",
        "price": "numeric",
        "room_size": "varchar",
        "max_occupancy": "integer",
        "bed_type": "varchar",
        "room_view": "varchar",
        "review_score": "numeric",
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

### Q3-02 — Tìm phòng theo số người

🙋 **Câu hỏi người dùng:**
> "Tôi đi 4 người, có phòng nào phù hợp không?"

💬 **Phản hồi người dùng mong muốn:**
```
Tìm thấy 3 loại phòng phù hợp cho 4 người:

1. Family Suite — tối đa 4 người
   72 m²  |  2 giường đôi  |  6.500.000 VND/đêm

2. Connecting Rooms (2 phòng liền kề) — tối đa 4 người
   2 × 38 m²  |  2 giường đôi King  |  5.600.000 VND/đêm

3. Villa 2 Phòng ngủ — tối đa 4 người
   120 m²  |  2 giường King  |  12.000.000 VND/đêm
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/rooms",
  "path_params": { "id": "integer" },
  "query_params": { "min_occupancy": 4 },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "max_occupancy": "integer",
        "room_size": "varchar",
        "bed_type": "varchar",
        "price": "numeric",
        "room_amenities": ["text[]"],
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

### Q3-03 — Tìm phòng view biển

🙋 **Câu hỏi người dùng:**
> "Có phòng view biển không, giá khoảng bao nhiêu?"

💬 **Phản hồi người dùng mong muốn:**
```
🌊 Phòng hướng biển tại Vinpearl Resort Nha Trang Bay:

1. Premier Ocean View
   48 m²  |  Giường King  |  Tầm nhìn trực tiếp ra biển
   Giá: 4.200.000 VND/đêm  ★ 9.2/10

2. Ocean Front Suite
   65 m²  |  Giường King + sofa  |  Ban công view biển rộng
   Giá: 7.800.000 VND/đêm  ★ 9.4/10
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/rooms",
  "path_params": { "id": "integer" },
  "query_params": { "room_view": "Hướng Biển" },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "room_view": "varchar",
        "room_size": "varchar",
        "bed_type": "varchar",
        "price": "numeric",
        "review_score": "numeric",
        "room_amenities": ["text[]"],
        "images": ["text[]"]
      }
    ]
  }
}
```

---

### Q3-04 — Xem chi tiết một loại phòng

🙋 **Câu hỏi người dùng:**
> "Cho tôi xem chi tiết phòng Premier Ocean View"

💬 **Phản hồi người dùng mong muốn:**
```
🛏 Premier Ocean View — Vinpearl Resort Nha Trang Bay
★ 9.2/10

📐 Diện tích: 48 m²   |  👥 Tối đa 2 người
🛏 Giường: King size (1.8m × 2m)   |  🌊 View: Hướng biển trực diện

✨ Tiện nghi phòng:
✓ Điều hòa   ✓ Minibar   ✓ Smart TV 55"
✓ Phòng tắm với bồn tắm   ✓ Bàn làm việc   ✓ Két sắt
✓ Dép & áo choàng tắm   ✓ Máy pha cà phê

💰 Giá: từ 4.200.000 VND / đêm
📸 [12 ảnh phòng]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/rooms/{id}",
  "path_params": { "id": "integer" },
  "response": {
    "id": "integer",
    "hotel_id": "integer",
    "room_type_id": "bigint",
    "name": "varchar",
    "price": "numeric",
    "room_size": "varchar",
    "max_occupancy": "integer",
    "bed_type": "varchar",
    "room_view": "varchar",
    "room_amenities": ["text[]"],
    "review_score": "numeric",
    "images": ["text[]"]
  }
}
```

---

### Q3-05 — Tìm phòng giá rẻ nhất

🙋 **Câu hỏi người dùng:**
> "Phòng rẻ nhất ở khách sạn này là bao nhiêu?"

💬 **Phản hồi người dùng mong muốn:**
```
💡 Giá phòng thấp nhất tại Vinpearl Resort Nha Trang Bay:

Standard Garden View
Giá chỉ từ: 2.100.000 VND / đêm
(Áp dụng cho đặt trước 14 ngày, không hoàn hủy)
32 m²  |  2 người  |  Giường đôi
[Đặt ngay]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/rooms",
  "path_params": { "id": "integer" },
  "query_params": { "sort_by": "price:asc", "limit": 1 },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "price": "numeric",
        "room_size": "varchar",
        "max_occupancy": "integer",
        "bed_type": "varchar",
        "room_amenities": ["text[]"],
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

## 4. Địa điểm Lân cận

---

### Q4-01 — Xem tất cả địa điểm gần khách sạn

🙋 **Câu hỏi người dùng:**
> "Xung quanh khách sạn Vinpearl có những gì vui chơi?"

💬 **Phản hồi người dùng mong muốn:**
```
📍 Địa điểm nổi bật gần Vinpearl Resort Nha Trang Bay:

🎡 Khu vui chơi:
  • VinWonders Nha Trang — 0.3 km (đi cáp treo)
  • Vinpearl Aquarium — 0.5 km

🏖 Bãi biển:
  • Bãi biển riêng của resort — ngay tại chỗ
  • Bãi Dài Cam Ranh — 35 km

🏛 Văn hóa / Di tích:
  • Tháp Bà Ponagar — 8 km
  • Viện Hải dương học Nha Trang — 6 km
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/nearby-places",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "nearby_places": [
      {
        "id": "integer",
        "name": "varchar",
        "type": "varchar",
        "distance_km": "numeric"
      }
    ]
  }
}
```

---

### Q4-02 — Lọc địa điểm theo loại

🙋 **Câu hỏi người dùng:**
> "Gần đây có bãi biển hoặc điểm tắm biển nào không?"

💬 **Phản hồi người dùng mong muốn:**
```
🏖 Bãi biển gần Vinpearl Resort Nha Trang Bay:

1. Bãi biển riêng của resort — 0 km (Ngay tại chỗ)
2. Bãi Trũ — 2.1 km (10 phút đi thuyền)
3. Bãi Đá Chồng — 4.5 km
4. Bãi Dài — 18 km (30 phút lái xe)
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/nearby-places",
  "path_params": { "id": "integer" },
  "query_params": { "type": "Bãi biển" },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "type": "varchar",
        "distance_km": "numeric"
      }
    ]
  }
}
```

---

### Q4-03 — Tìm khách sạn gần địa điểm cụ thể

🙋 **Câu hỏi người dùng:**
> "Tôi muốn đi VinWonders Nha Trang, khách sạn nào ở gần nhất?"

💬 **Phản hồi người dùng mong muốn:**
```
🏨 Khách sạn gần VinWonders Nha Trang nhất:

1. Vinpearl Resort & Spa Nha Trang Bay — 0.3 km
   ★★★★★ | 9.0/10 | Giá từ 2.100.000 VND/đêm

2. Novotel Nha Trang — 3.5 km
   ★★★★ | 8.4/10 | Giá từ 1.800.000 VND/đêm
   ...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "nearby_place_name": "VinWonders Nha Trang",
    "sort_by": "distance:asc",
    "city": "Nha Trang"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "nearby_places": [
          {
            "name": "varchar",
            "distance_km": "numeric — khoảng cách tới địa điểm tìm kiếm"
          }
        ],
        "rooms": {
          "min_price": "numeric"
        },
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

### Q4-04 — Tìm địa điểm trong bán kính nhất định

🙋 **Câu hỏi người dùng:**
> "Trong vòng 5km quanh khách sạn có những điểm tham quan nào?"

💬 **Phản hồi người dùng mong muốn:**
```
🗺 Trong bán kính 5 km quanh Vinpearl Resort (8 địa điểm):

📍 Dưới 1 km:
  • VinWonders Nha Trang (Khu vui chơi) — 0.3 km
  • Bãi biển Hòn Tre (Bãi biển) — 0.1 km

📍 1 – 3 km:
  • Vinpearl Golf Club (Sân golf) — 1.2 km

📍 3 – 5 km:
  • Tháp Bà Ponagar (Di tích) — 4.8 km
  • Viện Hải dương học (Bảo tàng) — 4.2 km
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/nearby-places",
  "path_params": { "id": "integer" },
  "query_params": { "distance_max_km": 5 },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "type": "varchar",
        "distance_km": "numeric"
      }
    ]
  }
}
```

---

## 5. Hoạt động Giải trí

---

### Q5-01 — Xem hoạt động của khách sạn

🙋 **Câu hỏi người dùng:**
> "Khách sạn này có những hoạt động vui chơi gì?"

💬 **Phản hồi người dùng mong muốn:**
```
🎉 Hoạt động & Vé vui chơi tại Vinpearl Resort Nha Trang Bay:

1. Vé tham quan VinWonders Nha Trang
   Công viên giải trí đẳng cấp quốc tế trên đảo Hòn Tre
   💰 450.000 VND/người  |  ★ 9.1/10
   [Mua vé]

2. Tour lặn ngắm san hô
   Trải nghiệm thế giới đại dương tuyệt đẹp tại Hòn Mun
   💰 850.000 VND/người  |  ★ 8.8/10
   [Đặt tour]

3. Dịch vụ Spa Vinpearl Premium
   Massage & chăm sóc sức khỏe toàn diện
   💰 1.200.000 VND/buổi  |  ★ 9.3/10
   [Đặt lịch]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/activities",
  "path_params": { "id": "integer" },
  "response": {
    "hotel_id": "integer",
    "activities": [
      {
        "id": "integer",
        "title": "varchar",
        "description": "text",
        "price_amount": "numeric",
        "review_score": "numeric"
      }
    ]
  }
}
```

---

### Q5-02 — Tìm hoạt động theo giá

🙋 **Câu hỏi người dùng:**
> "Có hoạt động nào dưới 500k không?"

💬 **Phản hồi người dùng mong muốn:**
```
💚 Hoạt động dưới 500.000 VND tại Vinpearl Resort:

1. Vé vào cổng VinWonders — 450.000 VND  ★ 9.1
2. Thuê xe đạp dạo đảo — 120.000 VND  ★ 8.5
3. Yoga buổi sáng trên bãi biển — 200.000 VND  ★ 9.0
4. Vé tham quan Thủy cung Vinpearl — 300.000 VND  ★ 8.7
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/activities",
  "path_params": { "id": "integer" },
  "query_params": { "price_max": 500000, "sort_by": "price:asc" },
  "response": {
    "data": [
      {
        "id": "integer",
        "title": "varchar",
        "description": "text",
        "price_amount": "numeric",
        "review_score": "numeric"
      }
    ]
  }
}
```

---

### Q5-03 — Tìm hoạt động đánh giá cao nhất

🙋 **Câu hỏi người dùng:**
> "Hoạt động được đánh giá cao nhất tại đây là gì?"

💬 **Phản hồi người dùng mong muốn:**
```
🏆 Top 3 hoạt động được yêu thích nhất:

🥇 Dịch vụ Spa Vinpearl Premium
   ★ 9.3/10 — "Trải nghiệm thư giãn tuyệt vời, nhân viên chuyên nghiệp"
   1.200.000 VND/buổi

🥈 Tour lặn ngắm san hô Hòn Mun
   ★ 8.8/10 — "San hô rất đẹp, hướng dẫn viên nhiệt tình"
   850.000 VND/người

🥉 Vé VinWonders Nha Trang
   ★ 9.1/10 — "Khu vui chơi hoành tráng, phù hợp mọi lứa tuổi"
   450.000 VND/người
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/activities",
  "path_params": { "id": "integer" },
  "query_params": { "sort_by": "review_score:desc", "limit": 3 },
  "response": {
    "data": [
      {
        "id": "integer",
        "title": "varchar",
        "description": "text",
        "price_amount": "numeric",
        "review_score": "numeric"
      }
    ]
  }
}
```

---

### Q5-04 — Tìm hoạt động trên toàn hệ thống theo thành phố

🙋 **Câu hỏi người dùng:**
> "Có những trải nghiệm vui chơi độc đáo nào ở Phú Quốc?"

💬 **Phản hồi người dùng mong muốn:**
```
🌴 Top hoạt động đặc sắc tại Phú Quốc:

1. Safari Vinpearl Phú Quốc — từ 600.000 VND  ★ 9.2
2. Lặn biển khám phá san hô Nam đảo — từ 750.000 VND  ★ 8.9
3. Cáp treo Hòn Thơm (dài nhất thế giới) — từ 400.000 VND  ★ 8.7
4. Tour câu mực đêm — từ 300.000 VND  ★ 8.5
5. Sunworld Hòn Thơm Nature Park — từ 500.000 VND  ★ 8.8
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/activities",
  "query_params": {
    "city": "Phú Quốc",
    "sort_by": "review_score:desc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "hotel_id": "integer",
        "title": "varchar",
        "description": "text",
        "price_amount": "numeric",
        "review_score": "numeric",
        "hotel": {
          "name": "varchar",
          "city": "varchar"
        }
      }
    ]
  }
}
```

---

## 6. Gói Combo Khách sạn + Vui chơi

---

### Q6-01 — Gợi ý combo nghỉ dưỡng + vui chơi

🙋 **Câu hỏi người dùng:**
> "Tư vấn cho tôi gói combo 3 ngày 2 đêm ở Nha Trang bao gồm cả vé vui chơi"

💬 **Phản hồi người dùng mong muốn:**
```
🎁 Gợi ý Combo 3N2Đ Nha Trang — Dành cho 2 người

🏨 Khách sạn đề xuất:
   Vinpearl Resort & Spa Nha Trang Bay ★★★★★
   2 đêm × 4.200.000 VND = 8.400.000 VND

🎉 Hoạt động kèm theo:
   ✓ Vé VinWonders (2 người): 900.000 VND
   ✓ Tour lặn san hô (2 người): 1.700.000 VND
   ✓ Buổi Spa cho 2 người: 2.400.000 VND

💰 Tổng ước tính: 13.400.000 VND / 2 người
   (~ 6.700.000 VND / người)
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/combo",
  "path_params": { "id": "integer" },
  "query_params": {
    "nights": 3,
    "guests": 2,
    "include_activities": true
  },
  "response": {
    "hotel": {
      "id": "integer",
      "name": "varchar",
      "star_rating": "numeric",
      "review_score": "numeric",
      "recommended_room": {
        "name": "varchar",
        "price": "numeric",
        "room_view": "varchar"
      }
    },
    "activities": [
      {
        "id": "integer",
        "title": "varchar",
        "price_amount": "numeric",
        "review_score": "numeric"
      }
    ],
    "estimated_total": "numeric — tổng ước tính (phòng × đêm + activities × guests)"
  }
}
```

---

### Q6-02 — Tìm combo theo ngân sách

🙋 **Câu hỏi người dùng:**
> "Ngân sách 5 triệu cho 2 người đi Đà Lạt 2 ngày bao gồm cả vé vui chơi, có được không?"

💬 **Phản hồi người dùng mong muốn:**
```
✅ Hoàn toàn khả thi! Gợi ý trong ngân sách 5.000.000 VND / 2 người:

🏨 Dalat Wonder Resort
   1 đêm: 1.800.000 VND (phòng Deluxe, 2 người)

🎉 Hoạt động:
   ✓ Vé Thung lũng Tình Yêu (2 người): 360.000 VND
   ✓ Cáp treo Robin Hill (2 người): 280.000 VND
   ✓ Tour tham quan vườn hoa (2 người): 200.000 VND

💰 Tổng: 2.640.000 VND — Tiết kiệm được 2.360.000 VND!
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/combo-suggest",
  "query_params": {
    "city": "Đà Lạt",
    "budget_total": 5000000,
    "guests": 2,
    "nights": 2
  },
  "response": {
    "hotel": {
      "id": "integer",
      "name": "varchar",
      "review_score": "numeric",
      "recommended_room": {
        "name": "varchar",
        "price": "numeric"
      }
    },
    "activities": [
      {
        "id": "integer",
        "title": "varchar",
        "price_amount": "numeric"
      }
    ],
    "total_cost": "numeric",
    "remaining_budget": "numeric"
  }
}
```

---

### Q6-03 — Combo gia đình

🙋 **Câu hỏi người dùng:**
> "Gợi ý gói gia đình 4 người (2 người lớn + 2 trẻ em) đi Phú Quốc 3N2Đ"

💬 **Phản hồi người dùng mong muốn:**
```
👨‍👩‍👧‍👦 Gói Gia đình 3N2Đ Phú Quốc — 4 người

🏨 Premier Village Phú Quốc Resort ★★★★★ (9.1/10)
   Family Suite, tối đa 4 người: 2 đêm × 8.500.000 VND = 17.000.000 VND
   Phù hợp: Gia đình có trẻ nhỏ ✓

🎉 Hoạt động gia đình:
   ✓ Vinpearl Safari (4 người): 2.400.000 VND
   ✓ Cáp treo Hòn Thơm (4 người): 1.600.000 VND
   ✓ Bữa tối BBQ hải sản (4 người): 1.200.000 VND

💰 Tổng ước tính: 22.200.000 VND
   (~ 5.550.000 VND / người)
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/combo-suggest",
  "query_params": {
    "city": "Phú Quốc",
    "guests": 4,
    "nights": 3,
    "suitable_for": "Gia đình có trẻ nhỏ",
    "min_occupancy": 4
  },
  "response": {
    "hotel": {
      "id": "integer",
      "name": "varchar",
      "star_rating": "numeric",
      "review_score": "numeric",
      "suitable_for": ["text[]"],
      "recommended_room": {
        "name": "varchar",
        "max_occupancy": "integer",
        "price": "numeric"
      }
    },
    "activities": [
      {
        "id": "integer",
        "title": "varchar",
        "description": "text",
        "price_amount": "numeric",
        "review_score": "numeric"
      }
    ],
    "total_cost": "numeric"
  }
}
```

---

## 7. So sánh & Gợi ý Cá nhân hóa

---

### Q7-01 — So sánh 2 khách sạn

🙋 **Câu hỏi người dùng:**
> "So sánh Fusion Maia và Four Seasons Đà Nẵng giúp tôi chọn"

💬 **Phản hồi người dùng mong muốn:**
```
⚖️ So sánh chi tiết — Fusion Maia vs Four Seasons Đà Nẵng

                      Fusion Maia          Four Seasons
──────────────────────────────────────────────────────
Xếp hạng sao          ★★★★★                ★★★★★
Điểm đánh giá         9.4/10               9.6/10
Giá phòng từ          5.200.000 VND        8.500.000 VND
Loại hình             Resort               Resort
Hạng sang             ✓                    ✓
Bãi biển riêng        ✓                    ✓
Spa                   ✓ (Bữa sáng + Spa)   ✓
Điểm vị trí           9.1                  9.4
Điểm sạch sẽ          9.5                  9.7

💡 Gợi ý: Nếu ưu tiên giá trị tốt nhất → Fusion Maia
           Nếu ưu tiên trải nghiệm cao cấp → Four Seasons
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/compare",
  "query_params": { "ids": [101, 205] },
  "response": {
    "hotels": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "is_luxury": "boolean",
        "review_score": "numeric",
        "review_count": "integer",
        "reviews_detail": "jsonb — grades chi tiết",
        "amenities": ["text[]"],
        "rooms": { "min_price": "numeric" },
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

### Q7-02 — Gợi ý cho cặp đôi tuần trăng mật

🙋 **Câu hỏi người dùng:**
> "Gợi ý khách sạn lãng mạn cho tuần trăng mật ở Phú Quốc, budget 10 triệu 3 đêm"

💬 **Phản hồi người dùng mong muốn:**
```
💑 Top khách sạn lãng mạn cho tuần trăng mật tại Phú Quốc
   (Ngân sách: ~3.300.000 VND/đêm)

1. ✨ La Veranda Resort Phú Quốc MGallery
   ★★★★★ | 9.2/10 | Giá từ 2.900.000 VND/đêm
   Phù hợp: ❤️ Cặp đôi
   Nổi bật: Kiến trúc thuộc địa Pháp, bãi biển riêng, spa đôi
   [Xem chi tiết]

2. Salinda Premium Beach Resort
   ★★★★★ | 9.1/10 | Giá từ 3.100.000 VND/đêm
   Phù hợp: ❤️ Cặp đôi
   Nổi bật: Hồ bơi riêng, sunset view, bữa tối nến lãng mạn
   [Xem chi tiết]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Phú Quốc",
    "suitable_for": "Cặp đôi",
    "price_max": 3400000,
    "sort_by": "review_score:desc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "suitable_for": ["text[]"],
        "amenities": ["text[]"],
        "description": "text — trích đoạn 200 ký tự đầu",
        "rooms": { "min_price": "numeric" },
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

### Q7-03 — Gợi ý khách sạn gần sân bay

🙋 **Câu hỏi người dùng:**
> "Tôi đến Đà Nẵng muộn, tìm khách sạn gần sân bay nhất để nghỉ"

💬 **Phản hồi người dùng mong muốn:**
```
✈️ Khách sạn gần Sân bay Đà Nẵng (cách dưới 5 km):

1. Novotel Đà Nẵng Premier Han River
   2.1 km từ sân bay  |  ★★★★★  |  8.9/10
   Giá từ: 1.950.000 VND/đêm
   [Đặt ngay]

2. Mercure Đà Nẵng
   1.8 km từ sân bay  |  ★★★★  |  8.6/10
   Giá từ: 1.200.000 VND/đêm
   [Đặt ngay]
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "city": "Đà Nẵng",
    "nearby_place_name": "Sân bay Đà Nẵng",
    "distance_max_km": 5,
    "sort_by": "distance:asc"
  },
  "response": {
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "nearby_places": [
          {
            "name": "varchar",
            "type": "varchar",
            "distance_km": "numeric"
          }
        ],
        "rooms": { "min_price": "numeric" },
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

### Q7-04 — Gợi ý dựa trên tiêu chí tổng hợp

🙋 **Câu hỏi người dùng:**
> "Tìm resort có spa, hồ bơi vô cực, gần biển, điểm trên 9, giá dưới 5 triệu đêm"

💬 **Phản hồi người dùng mong muốn:**
```
🌟 Tìm thấy 4 resort khớp tất cả tiêu chí:

1. Radisson Blu Resort Đà Nẵng
   ★★★★★ | 9.1/10
   ✓ Spa  ✓ Hồ bơi vô cực  ✓ Bãi biển riêng
   Giá từ: 4.200.000 VND/đêm

2. TIA Wellness Resort Đà Nẵng  
   ★★★★★ | 9.3/10
   ✓ Wellness Spa  ✓ Hồ bơi infinity  ✓ Sát biển Mỹ Khê
   Giá từ: 4.800.000 VND/đêm
   ...
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels",
  "query_params": {
    "accommodation_type": "Resort",
    "amenities": ["Spa", "Hồ bơi vô cực", "Bãi biển riêng"],
    "review_score_min": 9.0,
    "price_max": 5000000,
    "sort_by": "review_score:desc"
  },
  "response": {
    "total": 4,
    "data": [
      {
        "id": "integer",
        "name": "varchar",
        "city": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "amenities": ["text[]"],
        "rooms": { "min_price": "numeric" },
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

### Q7-05 — Gợi ý khách sạn tương tự

🙋 **Câu hỏi người dùng:**
> "Có khách sạn nào giống Anantara Hội An nhưng rẻ hơn không?"

💬 **Phản hồi người dùng mong muốn:**
```
💡 Các lựa chọn thay thế cho Anantara Hội An:

Anantara Hội An: ★★★★★ | 9.5/10 | từ 7.200.000 VND/đêm

Lựa chọn tương tự nhưng tiết kiệm hơn:

1. Silk Sense Hội An River Resort
   ★★★★★ | 9.2/10 | từ 3.800.000 VND/đêm (-47%)
   Tương đồng: Bên bờ sông Thu Bồn, kiến trúc truyền thống, spa

2. La Siesta Hội An Resort & Spa
   ★★★★ | 9.0/10 | từ 2.500.000 VND/đêm (-65%)
   Tương đồng: Thiết kế Hội An cổ, spa, hồ bơi, vị trí tốt
```

📦 **Phản hồi API Backend:**
```json
{
  "endpoint": "GET /api/hotels/{id}/similar",
  "path_params": { "id": "integer — ID Anantara Hội An" },
  "query_params": {
    "price_max": "numeric — lấy max_price của khách sạn gốc × 0.8",
    "city": "varchar — cùng thành phố",
    "accommodation_type": "varchar — cùng loại",
    "sort_by": "review_score:desc"
  },
  "response": {
    "reference_hotel": {
      "id": "integer",
      "name": "varchar",
      "review_score": "numeric",
      "amenities": ["text[]"],
      "rooms": { "min_price": "numeric" }
    },
    "similar_hotels": [
      {
        "id": "integer",
        "name": "varchar",
        "star_rating": "numeric",
        "review_score": "numeric",
        "amenities": ["text[]"],
        "rooms": { "min_price": "numeric" },
        "price_saving_pct": "numeric — % tiết kiệm so với khách sạn gốc",
        "images": ["text — ảnh đại diện [0]"]
      }
    ]
  }
}
```

---

## Tổng hợp Danh sách API

| # | Endpoint | Method | Mô tả chức năng | Bảng dữ liệu |
|---|----------|--------|-----------------|-------------|
| 1 | `/api/hotels` | GET | Tìm kiếm & lọc danh sách khách sạn theo thành phố, loại, sao, điểm, tiện ích, đối tượng, khoảng giá | `hotels`, `rooms` |
| 2 | `/api/hotels/{id}` | GET | Lấy toàn bộ thông tin chi tiết một khách sạn | `hotels` |
| 3 | `/api/hotels/{id}/images` | GET | Lấy danh sách toàn bộ ảnh của một khách sạn | `hotels.images` |
| 4 | `/api/hotels/{id}/policies` | GET | Lấy chính sách nhận/trả phòng, phụ phí và ghi chú đặc biệt | `hotels.policyNotes`, `hotels.useful_info` |
| 5 | `/api/hotels/{id}/reviews` | GET | Lấy điểm đánh giá tổng quan và chi tiết theo từng tiêu chí | `hotels.review_score`, `hotels.reviews_detail` |
| 6 | `/api/hotels/{id}/location` | GET | Lấy tọa độ, địa chỉ và danh sách địa điểm lân cận kèm khoảng cách | `hotels`, `nearby_places` |
| 7 | `/api/hotels/{id}/rooms` | GET | Lấy danh sách loại phòng của khách sạn, hỗ trợ lọc theo số người, hướng view, giá | `rooms` |
| 8 | `/api/rooms/{id}` | GET | Lấy chi tiết đầy đủ một loại phòng cụ thể | `rooms` |
| 9 | `/api/hotels/{id}/nearby-places` | GET | Lấy danh sách địa điểm nổi bật gần khách sạn, hỗ trợ lọc theo loại và bán kính | `nearby_places` |
| 10 | `/api/hotels/{id}/activities` | GET | Lấy danh sách hoạt động vui chơi liên kết với khách sạn, hỗ trợ lọc theo giá và điểm | `activities` |
| 11 | `/api/activities` | GET | Tìm kiếm hoạt động giải trí trên toàn hệ thống theo thành phố, giá, điểm | `activities`, `hotels` |
| 12 | `/api/hotels/{id}/combo` | GET | Tạo gói combo khách sạn kèm hoạt động gợi ý, tính tổng chi phí ước tính | `hotels`, `rooms`, `activities` |
| 13 | `/api/hotels/combo-suggest` | GET | Gợi ý combo phù hợp theo ngân sách, số người, số đêm, thành phố | `hotels`, `rooms`, `activities` |
| 14 | `/api/hotels/compare` | GET | So sánh song song nhiều khách sạn theo tất cả tiêu chí | `hotels`, `rooms` |
| 15 | `/api/hotels/{id}/similar` | GET | Gợi ý các khách sạn tương tự nhưng rẻ hơn (cùng thành phố, cùng loại) | `hotels`, `rooms` |

---
