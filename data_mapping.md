# Đặc Tả Ánh Xạ Dữ Liệu (JSON to PostgreSQL Data Mapping)

Tài liệu này chi tiết hóa cách ánh xạ các trường dữ liệu từ tệp tin JSON trong thư mục `processed/` sang các cột tương ứng trong 4 bảng của cơ sở dữ liệu quan hệ PostgreSQL.

---

## 1. Bảng `hotels` (Thông tin Khách sạn)

| Cột trong DB | Kiểu dữ liệu | Trường dữ liệu trong JSON | Logic xử lý / Fallback | ví dụ giá trị |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `INTEGER` (PK) | `$.hotel_id` | Lấy trực tiếp làm khóa chính. | `1994212` |
| `name` | `VARCHAR(255)` | `$.name` | Lấy trực tiếp. Báo lỗi nếu thiếu. | `"Vinpearl Hoi An Villas"` |
| `accommodation_type`| `VARCHAR(100)` | `$.accommodation_type` | Lấy trực tiếp. | `"Resort"` |
| `star_rating` | `NUMERIC(3,1)` | `$.star_rating` | Ép kiểu số thực (float). | `5.0` |
| `is_luxury` | `BOOLEAN` | `$.is_luxury` | Mặc định: `false`. | `false` |
| `review_score` | `NUMERIC(3,1)` | `$.review_score` | Ép kiểu số thực (float). | `7.8` |
| `review_count` | `INTEGER` | `$.review_count` | Ép kiểu số nguyên. Mặc định `0`. | `15` |
| `address` | `TEXT` | `$.address` | Lấy trực tiếp. | `"Cửa Đại, Hội An, Việt Nam"` |
| `city` | `VARCHAR(100)` | `$.city` hoặc `$.province` | Ưu tiên `city`. Nếu không có, sử dụng `province`. | `"Hội An"` |
| `latitude` | `DOUBLE PRECISION`| `$.latitude` | Ép kiểu số thực. | `15.88068675994873` |
| `longitude` | `DOUBLE PRECISION`| `$.longitude` | Ép kiểu số thực. | `108.38843536376953` |
| `description` | `TEXT` | `$.description` | Lấy trực tiếp. | `"Vinpearl Hoi An Villas..."` |
| `amenities` | `TEXT[]` | `$.amenities` | Chuyển mảng string của JSON thành mảng PG. | `['Bể bơi', 'Spa', 'Quán bar']` |
| `useful_info` | `JSONB` | `$.useful_info` | Lưu trữ nguyên đối tượng JSON bổ sung. | `{"Nhận phòng từ": "14:00", ...}` |
| `policyNotes` | `TEXT[]` | `$.secondary.hotel_policy.policyNotes` | Lấy mảng từ cấu trúc lồng nhau trong `secondary`. | `['Không cung cấp giường phụ...']` |
| `suitable_for` | `TEXT[]` | `$.suitable_for` | Chuyển mảng đối tượng phù hợp. | `['Cặp đôi', 'Gia đình']` |
| `reviews_detail` | `JSONB` | `$.reviews_detail.reviews` | Lưu trữ toàn bộ mảng chứa các đánh giá (reviews) của khách hàng. | `[{"rating": 4.0, "text": "...", "reviewer_name": "NGUYỄN", ...}]` |
| `images` | `TEXT[]` | `$.image_urls` hoặc `$.images` | Ưu tiên dùng mảng `image_urls` (mảng string). Nếu không có, trích xuất `url` từ mảng đối tượng `images`. | `['https://pix8.agoda.net/...']` |
| `source_url` | `TEXT` | `$.source_url` | Đường dẫn trang nguồn Agoda. | `"https://www.agoda.com/..."` |

---

## 2. Bảng `rooms` (Thông tin Phòng)

Dữ liệu phòng được duyệt từ mảng `$.rooms` ở root JSON. Nếu không tồn tại hoặc rỗng, sẽ sử dụng mảng dự phòng `$.room_grid.rooms`.

| Cột trong DB | Kiểu dữ liệu | Trường trong Room Object JSON | Logic xử lý / Fallback | ví dụ giá trị |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `SERIAL` (PK) | *Tự sinh* | Khóa chính tự tăng trong DB. | `1` |
| `hotel_id` | `INTEGER` (FK) | `$.hotel_id` | Lấy từ `hotel_id` ở root của file JSON hiện tại. | `1994212` |
| `room_type_id` | `BIGINT` | `room.room_type_id` | ID loại phòng gốc từ Agoda. | `11305152` |
| `name` | `VARCHAR(255)` | `room.name` | Tên loại phòng (bắt buộc). | `"Villa 3 phòng ngủ hướng biển"` |
| `price` | `NUMERIC(15,2)` | `room.price_per_night` | Giá phòng mỗi đêm (VND). Nếu không có, mặc định là `NULL`. | `3820457.00` |
| `room_size` | `VARCHAR(50)` | `room.room_size` hoặc `room.size_sqm` | Trích xuất diện tích. Nếu là số, thêm hậu tố " m²". Ví dụ: `38` -> `"38 m²"`. | `"38 m²"` |
| `max_occupancy` | `INTEGER` | `room.max_occupancy` | Số khách tối đa. Mặc định `2`. | `6` |
| `bed_type` | `VARCHAR(255)` | `room.bed_type` | Mô tả loại giường. | `"1 giường lớn / 2 giường đơn"` |
| `room_view` | `VARCHAR(100)` | `room.room_view` | Hướng phòng (e.g. Hướng biển, Hướng vườn). | `"Hướng Đại dương"` |
| `room_amenities`| `TEXT[]` | `room.room_amenities` | Mảng các tiện ích riêng của phòng. | `['Ban công', 'Bể bơi riêng']` |
| `images` | `TEXT[]` | `room.images` | Mảng URL các hình ảnh của phòng. | `['https://pix8.agoda.net/...']` |
| `review_score` | `NUMERIC(3,1)` | `room.review_score` | Điểm đánh giá riêng của phòng (nếu có). | `8.0` |

---

## 3. Bảng `nearby_places` (Địa điểm Lân cận)

Dữ liệu được duyệt từ mảng `$.nearby_places` ở root JSON.

| Cột trong DB | Kiểu dữ liệu | Trường trong Place Object JSON | Logic xử lý / Fallback | ví dụ giá trị |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `SERIAL` (PK) | *Tự sinh* | Khóa chính tự tăng trong DB. | `1` |
| `hotel_id` | `INTEGER` (FK) | `$.hotel_id` | Lấy từ `hotel_id` ở root của file JSON hiện tại. | `1994212` |
| `name` | `VARCHAR(255)` | `place.name` | Tên địa danh (bắt buộc). | `"Rừng dừa nước"` |
| `type` | `VARCHAR(100)` | `place.type` | Phân loại địa danh (e.g., Công viên, Siêu thị).| `"Địa điểm giải trí"` |
| `distance_km` | `NUMERIC(6,2)` | `place.distance_km` | Khoảng cách thực tế (km), ép kiểu float. | `1.16` |

---

## 4. Bảng `activities` (Hoạt động Giải trí / Điểm vui chơi)

Dữ liệu được duyệt từ mảng `$.activities` ở root JSON.

| Cột trong DB | Kiểu dữ liệu | Trường trong Activity Object JSON | Logic xử lý / Fallback | ví dụ giá trị |
| :--- | :--- | :--- | :--- | :--- |
| `id` | `SERIAL` (PK) | *Tự sinh* | Khóa chính tự tăng trong DB. | `1` |
| `hotel_id` | `INTEGER` (FK) | `$.hotel_id` | Lấy từ `hotel_id` ở root của file JSON hiện tại. | `1994212` |
| `title` | `VARCHAR(255)` | `activity.title` | Tên hoạt động (bắt buộc). | `"Vé vào cổng VinWonders Nam Hội An"`|
| `description` | `TEXT` | `activity.description` | Mô tả chi tiết hoạt động. | `"Khám phá VinWonders Nam Hội An..."` |
| `price_amount` | `NUMERIC(15,2)` | `activity.price.currency` hoặc `activity.price.display.perBook.total.allInclusive.chargeTotal` | Phân tích giá vé (VND). Ưu tiên `price.currency` (chứa giá trị số VND) hoặc lội sâu vào `chargeTotal`. Mặc định `0.00`. | `240949.00` |
| `review_score` | `NUMERIC(3,1)` | `activity.review_score` | Điểm đánh giá hoạt động. | `4.8` |
