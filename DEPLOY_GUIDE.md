# Hướng Dẫn Triển Khai Cơ Sở Dữ Liệu & Backend API

Tài liệu này hướng dẫn bạn từng bước thiết lập cơ sở dữ liệu trên **Supabase**, chạy script import dữ liệu từ máy của bạn, và deploy mã nguồn Express backend lên **Render** chạy thực tế trên Internet.

---

## BƯỚC 1: Cấu hình Cơ sở dữ liệu trên Supabase

1. **Tạo Project mới:**
   - Truy cập trang quản trị [Supabase Dashboard](https://supabase.com/dashboard).
   - Đăng nhập và nhấn **New Project**.
   - Điền các thông tin: **Name** (tên dự án), **Database Password** (mật khẩu này rất quan trọng, bạn hãy lưu lại để cấu hình), chọn Region (ví dụ: *Singapore* để tối ưu tốc độ kết nối về Việt Nam) và chọn gói **Free Tier**.
   - Nhấn **Create new project** và đợi khoảng 1-2 phút cho dự án khởi tạo xong.

2. **Khởi tạo các bảng dữ liệu (Table Schema):**
   - Ở thanh điều hướng bên trái, nhấp vào biểu tượng **SQL Editor** (hình thẻ mã nguồn `SQL`).
   - Nhấp **New query** để tạo trang soạn thảo SQL mới.
   - Mở file [schema.sql](file:///d:/supabase_ota_travel/schema.sql) trong máy của bạn, copy toàn bộ nội dung và dán vào SQL Editor của Supabase.
   - Nhấn nút **Run** ở góc dưới bên phải. Đảm bảo thông báo trả về hiển thị `"Success. No rows returned."` cho thấy 4 bảng (`hotels`, `rooms`, `nearby_places`, `activities`) và các index đã được tạo thành công.

3. **Lấy chuỗi kết nối (Connection String):**
   - Ở thanh điều hướng bên trái Supabase, nhấn vào biểu tượng **Project Settings** (hình bánh răng ở góc dưới cùng).
   - Nhấp vào mục **Database** trong menu cài đặt.
   - Cuộn xuống phần **Connection string**, chọn tab **URI** (hoặc **Session**).
   - Copy chuỗi kết nối có định dạng:
     `postgresql://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-ID].supabase.co:5432/postgres`
   - Thay thế phần `[YOUR-PASSWORD]` bằng mật khẩu database bạn đã đặt ở bước tạo dự án.

---

## BƯỚC 2: Cấu hình file .env và Import dữ liệu

1. **Cấu hình file môi trường cục bộ:**
   - Mở file [.env](file:///d:/supabase_ota_travel/.env) trong dự án của bạn.
   - Dán chuỗi kết nối vừa copy (đã thay mật khẩu) vào biến `DATABASE_URL`.
     Ví dụ:
     ```env
     PORT=5000
     DATABASE_URL=postgresql://postgres:MatKhauCuaBan123@db.abcxyz.supabase.co:5432/postgres
     ```

2. **Chạy script tải dữ liệu:**
   - Mở terminal tại thư mục dự án `d:\supabase_ota_travel`.
   - Thực hiện lệnh sau để khởi chạy script import:
     ```powershell
     npm run import
     ```
   - Script sẽ đọc lần lượt 26 file JSON trong thư mục `processed/`, bóc tách thông tin, ánh xạ sang các cột và chèn vào database Supabase.
   - Chờ script chạy và kiểm tra nhật ký log. Khi màn hình xuất hiện thông báo:
     `Quá trình import hoàn tất thành công!`
     tức là toàn bộ dữ liệu đã được nạp thành công vào database Supabase trực tuyến của bạn. Bạn có thể kiểm tra dữ liệu bằng tính năng **Table Editor** trên Supabase dashboard.

---

## BƯỚC 3: Chạy thử nghiệm cục bộ (Local Testing)

1. **Khởi động Local Server:**
   - Trong terminal, chạy lệnh:
     ```powershell
     npm run dev
     ```
   - Server sẽ chạy trên cổng 5000: `http://localhost:5000`.

2. **Kiểm tra API bằng trình duyệt hoặc Postman:**
   - Truy cập `http://localhost:5000/health` để kiểm tra trạng thái server.
   - Thử nghiệm tìm kiếm khách sạn ở Đà Nẵng:
     `http://localhost:5000/api/hotels?city=Đà%20Nẵng`
   - Kiểm tra API lấy chi tiết một khách sạn (ví dụ ID: 1994212):
     `http://localhost:5000/api/hotels/1994212`

---

## BƯỚC 4: Deploy Backend lên Render

Để deploy lên Render, dự án của bạn cần được đẩy lên GitHub.

1. **Push code lên GitHub:**
   - Hãy chắc chắn rằng bạn đã commit các file mới tạo (ngoại trừ `.env` đã bị `.gitignore` chặn).
   - Mở terminal và thực hiện:
     ```powershell
     git add .
     git commit -m "feat: setup backend server and import script"
     git push origin main
     ```

2. **Tạo Web Service trên Render:**
   - Đăng nhập vào trang quản trị [Render Dashboard](https://dashboard.render.com).
   - Nhấp vào nút **New +** ở góc trên cùng bên phải và chọn **Web Service**.
   - Chọn **Connect a repository** và liên kết tài khoản GitHub của bạn, sau đó chọn kho lưu trữ `supabase_ota_travel` vừa push lên.

3. **Cấu hình Web Service:**
   - **Name:** Đặt tên cho dự án (ví dụ: `supabase-ota-travel-backend`).
   - **Region:** Chọn khu vực gần Việt Nam (ví dụ: *Singapore* hoặc *Oregon*).
   - **Branch:** `main` (hoặc nhánh chứa code của bạn).
   - **Runtime:** `Node` (Render tự động phát hiện).
   - **Build Command:** `npm install`
   - **Start Command:** `npm start`
   - **Instance Type:** Chọn gói **Free** (Miễn phí).

4. **Thiết lập Biến môi trường trên Render:**
   - Nhấp vào tab **Environment** (hoặc nút **Advanced**) trong cấu hình Render.
   - Nhấn **Add Environment Variable** để thêm biến sau:
     * **Key:** `DATABASE_URL`
     * **Value:** Dán chuỗi kết nối PostgreSQL Supabase giống như trong file `.env` cục bộ của bạn.
   - Nhấn **Save changes** hoặc **Create Web Service** ở cuối trang.

5. **Hoàn tất deploy:**
   - Render sẽ tự động build và start server. Bạn có thể theo dõi trực tiếp nhật ký build trong trang chi tiết dịch vụ.
   - Khi trạng thái chuyển sang màu xanh lá **"Live"**, Render sẽ cấp cho bạn một đường dẫn công khai (ví dụ: `https://supabase-ota-travel-backend.onrender.com`).
   - Bạn có thể thử nghiệm gọi API từ máy của bạn qua URL trực tuyến này, ví dụ:
     `https://supabase-ota-travel-backend.onrender.com/health`
     `https://supabase-ota-travel-backend.onrender.com/api/hotels?city=Đà%20Nẵng`
