# Hướng Dẫn Triển Khai Backend FastAPI & Database Supabase

Tài liệu này hướng dẫn bạn từng bước thiết lập cơ sở dữ liệu trên **Supabase**, chạy script import dữ liệu, và deploy mã nguồn **FastAPI** (Python) lên **Render** chạy trực tuyến công khai.

---

## BƯỚC 1: Cấu hình Cơ sở dữ liệu trên Supabase

1. **Khởi tạo các bảng dữ liệu (Table Schema):**
   - Truy cập vào **SQL Editor** trên [Supabase Dashboard](https://supabase.com/dashboard) dự án của bạn.
   - Nhấp **New query** để tạo trang soạn thảo SQL mới.
   - Mở file [schema.sql](file:///d:/supabase_ota_travel/schema.sql), copy toàn bộ nội dung và dán vào SQL Editor của Supabase.
   - Nhấn nút **Run**. Đảm bảo các bảng (`hotels`, `rooms`, `nearby_places`, `activities`) và các index được tạo thành công.

---

## BƯỚC 2: Cài đặt và Import dữ liệu ở Local

1. **Cài đặt thư viện (nếu chưa thực hiện):**
   - Đảm bảo bạn đang ở môi trường Miniconda. Mở terminal tại thư mục dự án và chạy:
     ```powershell
     pip install -r requirements.txt
     ```

2. **Chạy script tải dữ liệu lên Supabase:**
   - Tôi đã tự động cấu hình chuỗi kết nối thực tế của dự án của bạn vào file `.env`. Bạn chỉ cần khởi chạy lệnh sau để import:
     ```powershell
     python import_data.py
     ```
   - Script sẽ đọc lần lượt 26 file JSON trong thư mục `processed/` và đẩy trực tiếp lên cơ sở dữ liệu Supabase của bạn.
   - Đợi script hiển thị thông báo:
     `Quá trình import dữ liệu hoàn tất thành công!`

---

## BƯỚC 3: Chạy thử nghiệm cục bộ (Local Testing)

1. **Khởi động server FastAPI bằng Uvicorn:**
   - Trong terminal, chạy lệnh:
     ```powershell
     uvicorn main:app --reload --port 5000
     ```
   - Server sẽ chạy tại địa chỉ: `http://localhost:5000`.

2. **Kiểm tra API tự động bằng Swagger UI:**
   - FastAPI tự động tạo tài liệu và giao diện test API tại: `http://localhost:5000/docs`.
   - Bạn có thể truy cập đường dẫn này trên trình duyệt và trực tiếp nhấn **Try it out** để test toàn bộ 15 API.

---

## BƯỚC 4: Deploy lên Render

Để deploy lên Render, dự án của bạn cần được đẩy lên GitHub.

1. **Push code lên GitHub:**
   - Commit các file mới tạo (FastAPI và Python files):
     ```powershell
     git add .
     git commit -m "feat: migrate backend to Python FastAPI"
     git push origin main
     ```

2. **Tạo Web Service trên Render:**
   - Truy cập [Render Dashboard](https://dashboard.render.com).
   - Chọn **New +** -> **Web Service**.
   - Liên kết với GitHub và chọn kho lưu trữ dự án này.

3. **Cấu hình Web Service:**
   - **Name:** Đặt tên cho backend (ví dụ: `supabase-ota-travel-fastapi`).
   - **Region:** Chọn khu vực gần Việt Nam (ví dụ: *Singapore*).
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Chọn gói **Free** (Miễn phí).

4. **Thiết lập Biến môi trường trên Render:**
   - Nhấp vào tab **Environment** trong cấu hình Render.
   - Thêm biến sau:
     * **Key:** `DATABASE_URL`
     * **Value:** Dán chuỗi kết nối thực tế trong file `.env` của bạn:
       `postgresql://postgres:o0PVbJXG1vzp8Z5T@db.icpmdjghxsstmlzxoefv.supabase.co:5432/postgres`
   - Nhấn **Save changes** để Render tiến hành build và deploy.

5. **Nghiệm thu trực tuyến:**
   - Khi trạng thái chuyển sang **"Live"**, bạn sẽ có đường dẫn công khai (ví dụ: `https://supabase-ota-travel-fastapi.onrender.com`).
   - Tài liệu Swagger UI trực tuyến cũng sẽ khả dụng tại: `https://[your-app].onrender.com/docs`.
