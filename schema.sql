-- Xóa bảng nếu đã tồn tại để thiết lập lại (theo thứ tự ngược của quan hệ khóa ngoại)
DROP TABLE IF EXISTS activities CASCADE;
DROP TABLE IF EXISTS nearby_places CASCADE;
DROP TABLE IF EXISTS rooms CASCADE;
DROP TABLE IF EXISTS hotels CASCADE;

-- 1. Bảng hotels (Thông tin Khách sạn)
CREATE TABLE hotels (
    id INTEGER PRIMARY KEY, -- hotel_id từ JSON
    name VARCHAR(255) NOT NULL,
    accommodation_type VARCHAR(100),
    star_rating NUMERIC(3,1),
    is_luxury BOOLEAN DEFAULT FALSE,
    review_score NUMERIC(3,1),
    review_count INTEGER DEFAULT 0,
    address TEXT,
    city VARCHAR(100),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    description TEXT,
    amenities TEXT[], -- Mảng các tiện ích chung
    useful_info JSONB, -- Thông tin thêm (giờ checkin, checkout, v.v.)
    policyNotes TEXT[], -- Chính sách khách sạn
    suitable_for TEXT[], -- Đối tượng phù hợp
    reviews_detail JSONB, -- Lưu trữ mảng reviews từ JSON
    images TEXT[], -- Mảng URL các hình ảnh của khách sạn
    source_url TEXT
);

-- 2. Bảng rooms (Thông tin Phòng)
CREATE TABLE rooms (
    id SERIAL PRIMARY KEY,
    hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
    room_type_id BIGINT,
    name VARCHAR(255) NOT NULL,
    price NUMERIC(15,2),
    room_size VARCHAR(50),
    max_occupancy INTEGER,
    bed_type VARCHAR(255),
    room_view VARCHAR(100),
    room_amenities TEXT[],
    images TEXT[],
    review_score NUMERIC(3,1)
);

-- 3. Bảng nearby_places (Địa điểm Lân cận)
CREATE TABLE nearby_places (
    id SERIAL PRIMARY KEY,
    hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(100),
    distance_km NUMERIC(6,2)
);

-- 4. Bảng activities (Hoạt động Giải trí / Điểm vui chơi)
CREATE TABLE activities (
    id SERIAL PRIMARY KEY,
    hotel_id INTEGER REFERENCES hotels(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    price_amount NUMERIC(15,2),
    review_score NUMERIC(3,1)
);

-- Tạo các chỉ mục (Index) để tối ưu hóa tìm kiếm và lọc dữ liệu
CREATE INDEX idx_hotels_city ON hotels(city);
CREATE INDEX idx_hotels_accommodation_type ON hotels(accommodation_type);
CREATE INDEX idx_hotels_star_rating ON hotels(star_rating);
CREATE INDEX idx_hotels_review_score ON hotels(review_score);
CREATE INDEX idx_hotels_is_luxury ON hotels(is_luxury);

CREATE INDEX idx_rooms_hotel_id ON rooms(hotel_id);
CREATE INDEX idx_rooms_price ON rooms(price);
CREATE INDEX idx_rooms_max_occupancy ON rooms(max_occupancy);

CREATE INDEX idx_nearby_places_hotel_id ON nearby_places(hotel_id);
CREATE INDEX idx_nearby_places_name ON nearby_places(name);

CREATE INDEX idx_activities_hotel_id ON activities(hotel_id);
CREATE INDEX idx_activities_price_amount ON activities(price_amount);
CREATE INDEX idx_activities_review_score ON activities(review_score);
