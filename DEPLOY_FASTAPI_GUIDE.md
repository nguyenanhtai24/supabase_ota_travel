# Hướng dẫn Deploy — OTA Travel FastAPI Backend

## Tổng quan

| Mục | Công nghệ |
|-----|-----------|
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL trên Supabase |
| Hosting | Render (Web Service) |
| Xác thực | API Key (header `X-API-Key`) |

---

## Bước 1 — Chuẩn bị Supabase

### 1.1 Tạo Project
1. Đăng ký / đăng nhập tại [supabase.com](https://supabase.com)
2. Nhấn **New Project** → đặt tên, chọn region gần nhất (Singapore)
3. Lưu lại **Database Password** (chỉ hiển thị một lần)

### 1.2 Tạo Schema (Tables)
1. Vào **SQL Editor** trong Supabase Dashboard
2. Copy toàn bộ nội dung file `schema.sql` → dán vào SQL Editor → nhấn **Run**
3. Kiểm tra: 4 bảng `hotels`, `rooms`, `nearby_places`, `activities` được tạo thành công

### 1.3 Lấy Connection String
1. Vào **Settings → Database → Connection string**
2. Chọn tab **URI**
3. Copy chuỗi có dạng:
   ```
   postgresql://postgres:[YOUR_PASSWORD]@db.[PROJECT_ID].supabase.co:5432/postgres
   ```
4. Thay `[YOUR_PASSWORD]` bằng password đã lưu ở bước 1.1

---

## Bước 2 — Import dữ liệu

### 2.1 Thiết lập môi trường local
```bash
# Tạo file .env từ mẫu
copy .env.example .env

# Điền DATABASE_URL và API_SECRET_KEY vào .env
# DATABASE_URL=postgresql://postgres:...
# API_SECRET_KEY=your-secret-token-here
```

### 2.2 Cài thư viện
```bash
pip install -r requirements.txt
```

### 2.3 Chạy import
```bash
python import_data.py
```

Script sẽ đọc 26 file JSON trong thư mục `processed/` và import vào Supabase.
Sau khi chạy xong, kiểm tra dữ liệu trên Supabase → **Table Editor**.

---

## Bước 3 — Deploy lên Render

### 3.1 Tạo Web Service
1. Đăng nhập [render.com](https://render.com) → **New → Web Service**
2. Kết nối GitHub repo `supabase_ota_travel`
3. Cấu hình:

| Trường | Giá trị |
|--------|---------|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `python -m uvicorn main:app --host 0.0.0.0 --port $PORT` |
| **Root Directory** | *(để trống)* |

### 3.2 Thiết lập Environment Variables
Vào tab **Environment** → thêm 2 biến:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | Connection string từ Supabase (bước 1.3) |
| `API_SECRET_KEY` | Token bí mật của bạn (tự đặt, ví dụ: `ota_sk_abc123xyz`) |

### 3.3 Deploy
- Nhấn **Deploy** → chờ build xong (~2–3 phút)
- Log thành công sẽ hiển thị:
  ```
  INFO:     Uvicorn running on http://0.0.0.0:XXXX
  Database Connection Pool đã được khởi tạo thành công!
  ```

---

## Bước 4 — Kiểm tra API

### 4.1 Health Check (không cần token)
```bash
curl https://your-app.onrender.com/health
```
Kết quả mong đợi:
```json
{"status": "OK", "version": "2.0.0", "message": "..."}
```

### 4.2 Gọi API với token
```bash
# Tìm khách sạn tại Đà Nẵng
curl -H "X-API-Key: your-secret-token" \
     "https://your-app.onrender.com/api/hotels?city=Đà Nẵng"

# Lọc theo địa danh lân cận + khoảng cách
curl -H "X-API-Key: your-secret-token" \
     "https://your-app.onrender.com/api/hotels?city=Đà Nẵng&nearby_place_name=Sân bay Đà Nẵng&distance_max_km=5&sort_by=distance:asc"

# Chi tiết khách sạn
curl -H "X-API-Key: your-secret-token" \
     "https://your-app.onrender.com/api/hotels/1"

# Danh sách phòng, sắp xếp theo giá tăng dần
curl -H "X-API-Key: your-secret-token" \
     "https://your-app.onrender.com/api/hotels/1/rooms?sort_by=price:asc"
```

### 4.3 Swagger UI (tương tác trực tiếp)
Mở trình duyệt: `https://your-app.onrender.com/docs`

Nhấn **Authorize** → nhập API Key → test tất cả 15 endpoints.

---

## Danh sách 15 Endpoints

| # | Endpoint | Mô tả |
|---|----------|-------|
| 1 | `GET /api/hotels` | Tìm kiếm & lọc danh sách khách sạn |
| 2 | `GET /api/hotels/{id}` | Chi tiết đầy đủ một khách sạn |
| 3 | `GET /api/hotels/{id}/images` | Toàn bộ ảnh khách sạn |
| 4 | `GET /api/hotels/{id}/policies` | Chính sách nhận/trả phòng |
| 5 | `GET /api/hotels/{id}/reviews` | Điểm đánh giá chi tiết |
| 6 | `GET /api/hotels/{id}/location` | Tọa độ & địa điểm lân cận |
| 7 | `GET /api/hotels/{id}/rooms` | Danh sách loại phòng |
| 8 | `GET /api/rooms/{id}` | Chi tiết một loại phòng |
| 9 | `GET /api/hotels/{id}/nearby-places` | Địa điểm nổi bật gần khách sạn |
| 10 | `GET /api/hotels/{id}/activities` | Hoạt động vui chơi của khách sạn |
| 11 | `GET /api/activities` | Tìm hoạt động toàn hệ thống |
| 12 | `GET /api/hotels/{id}/combo` | Gợi ý gói combo |
| 13 | `GET /api/hotels/combo-suggest` | Gợi ý combo theo ngân sách |
| 14 | `GET /api/hotels/compare` | So sánh nhiều khách sạn |
| 15 | `GET /api/hotels/{id}/similar` | Khách sạn tương tự rẻ hơn |

---

## Lưu ý quan trọng

> **Bảo mật:** Không bao giờ commit file `.env` lên Git. File này đã được thêm vào `.gitignore`.

> **API Key:** Nếu `API_SECRET_KEY` chưa được cấu hình trên server, API sẽ cho phép tất cả request (dev mode). Luôn đặt key trên Render trước khi ra production.

> **Render Free Tier:** Server sẽ sleep sau 15 phút không có request. Request đầu tiên sau khi sleep sẽ mất ~30 giây để khởi động lại (cold start).
