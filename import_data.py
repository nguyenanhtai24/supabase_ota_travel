import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def run_import():
    if not DATABASE_URL or "YOUR_PASSWORD_HERE" in DATABASE_URL:
        print("Lỗi: DATABASE_URL chưa được cấu hình đúng trong file .env")
        return

    processed_dir = os.path.join(os.path.dirname(__file__), "processed")
    if not os.path.exists(processed_dir):
        print(f"Lỗi: Không tìm thấy thư mục processed tại {processed_dir}")
        return

    files = [f for f in os.listdir(processed_dir) if f.endswith(".json")]
    print(f"Tìm thấy {len(files)} file dữ liệu JSON trong thư mục processed.")

    try:
        # Kết nối tới cơ sở dữ liệu Supabase
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
        conn.autocommit = False  # Sử dụng manual transaction control
        cur = conn.cursor()
        print("Kết nối thành công đến Supabase database!")

        for idx, file in enumerate(files):
            file_path = os.path.join(processed_dir, file)
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                except Exception as e:
                    print(f"Lỗi đọc JSON từ file {file}: {e}")
                    continue

            hotel_id = data.get("hotel_id")
            if not hotel_id:
                print(f"File {file} không chứa hotel_id. Bỏ qua.")
                continue

            print(f"[{idx + 1}/{len(files)}] Đang import khách sạn: {data.get('name')} (ID: {hotel_id})...")

            try:
                # 1. Bóc tách dữ liệu hotels
                name = data.get("name", "Không rõ tên")
                accommodation_type = data.get("accommodation_type")
                star_rating = float(data["star_rating"]) if data.get("star_rating") is not None else None
                is_luxury = data.get("is_luxury") is True
                review_score = float(data["review_score"]) if data.get("review_score") is not None else None
                review_count = int(data["review_count"]) if data.get("review_count") is not None else 0
                address = data.get("address")
                city = data.get("city") or data.get("province") or None
                latitude = float(data["latitude"]) if data.get("latitude") is not None else None
                longitude = float(data["longitude"]) if data.get("longitude") is not None else None
                description = data.get("description")
                amenities = data.get("amenities", [])
                
                useful_info = None
                if data.get("useful_info"):
                    useful_info = json.dumps(data["useful_info"])

                # policyNotes từ secondary.hotel_policy.policyNotes
                policy_notes = None
                secondary = data.get("secondary", {})
                if secondary:
                    hotel_policy = secondary.get("hotel_policy", {})
                    if hotel_policy and isinstance(hotel_policy.get("policyNotes"), list):
                        policy_notes = hotel_policy["policyNotes"]

                suitable_for = data.get("suitable_for", [])

                # reviews_detail - lưu mảng reviews từ JSON
                reviews_detail = None
                reviews_detail_obj = data.get("reviews_detail", {})
                if reviews_detail_obj and isinstance(reviews_detail_obj.get("reviews"), list):
                    reviews_detail = json.dumps(reviews_detail_obj["reviews"])

                # images
                images = []
                if isinstance(data.get("image_urls"), list):
                    images = data["image_urls"]
                elif isinstance(data.get("images"), list):
                    images = [img.get("url") for img in data["images"] if img.get("url")]

                source_url = data.get("source_url")

                # 2. Chèn dữ liệu khách sạn (ON CONFLICT DO UPDATE để có tính chất idempotent)
                hotel_query = """
                    INSERT INTO hotels (
                        id, name, accommodation_type, star_rating, is_luxury, review_score, review_count, 
                        address, city, latitude, longitude, description, amenities, useful_info, 
                        policyNotes, suitable_for, reviews_detail, images, source_url
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    ) ON CONFLICT (id) DO UPDATE SET
                        name = EXCLUDED.name,
                        accommodation_type = EXCLUDED.accommodation_type,
                        star_rating = EXCLUDED.star_rating,
                        is_luxury = EXCLUDED.is_luxury,
                        review_score = EXCLUDED.review_score,
                        review_count = EXCLUDED.review_count,
                        address = EXCLUDED.address,
                        city = EXCLUDED.city,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        description = EXCLUDED.description,
                        amenities = EXCLUDED.amenities,
                        useful_info = EXCLUDED.useful_info,
                        policyNotes = EXCLUDED.policyNotes,
                        suitable_for = EXCLUDED.suitable_for,
                        reviews_detail = EXCLUDED.reviews_detail,
                        images = EXCLUDED.images,
                        source_url = EXCLUDED.source_url;
                """
                cur.execute(hotel_query, (
                    hotel_id, name, accommodation_type, star_rating, is_luxury, review_score, review_count,
                    address, city, latitude, longitude, description, amenities, useful_info,
                    policy_notes, suitable_for, reviews_detail, images, source_url
                ))

                # Xóa sạch các phòng, địa danh, hoạt động cũ liên kết với khách sạn này để tránh trùng lặp
                cur.execute("DELETE FROM rooms WHERE hotel_id = %s", (hotel_id,))
                cur.execute("DELETE FROM nearby_places WHERE hotel_id = %s", (hotel_id,))
                cur.execute("DELETE FROM activities WHERE hotel_id = %s", (hotel_id,))

                # 3. Chuẩn bị và chèn bảng rooms
                rooms_list = []
                if isinstance(data.get("rooms"), list):
                    rooms_list = data["rooms"]
                elif data.get("room_grid") and isinstance(data["room_grid"].get("rooms"), list):
                    rooms_list = data["room_grid"]["rooms"]

                for room in rooms_list:
                    room_type_id = int(room["room_type_id"]) if room.get("room_type_id") is not None else None
                    room_name = room.get("name", "Không rõ tên phòng")
                    price = float(room["price_per_night"]) if room.get("price_per_night") is not None else None
                    
                    room_size = None
                    if room.get("room_size"):
                        room_size = str(room["room_size"])
                    elif room.get("size_sqm") is not None:
                        room_size = f"{room['size_sqm']} m²"

                    max_occupancy = int(room["max_occupancy"]) if room.get("max_occupancy") is not None else 2
                    bed_type = room.get("bed_type")
                    room_view = room.get("room_view")
                    room_amenities = room.get("room_amenities", [])
                    room_images = room.get("images", [])
                    room_review_score = float(room["review_score"]) if room.get("review_score") is not None else None

                    room_query = """
                        INSERT INTO rooms (
                            hotel_id, room_type_id, name, price, room_size, max_occupancy, 
                            bed_type, room_view, room_amenities, images, review_score
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    cur.execute(room_query, (
                        hotel_id, room_type_id, room_name, price, room_size, max_occupancy,
                        bed_type, room_view, room_amenities, room_images, room_review_score
                    ))

                # 4. Chuẩn bị và chèn bảng nearby_places
                if isinstance(data.get("nearby_places"), list):
                    for place in data["nearby_places"]:
                        place_name = place.get("name")
                        if not place_name:
                            continue
                        place_type = place.get("type")
                        distance_km = float(place["distance_km"]) if place.get("distance_km") is not None else None

                        place_query = """
                            INSERT INTO nearby_places (hotel_id, name, type, distance_km)
                            VALUES (%s, %s, %s, %s)
                        """
                        cur.execute(place_query, (hotel_id, place_name, place_type, distance_km))

                # 5. Chuẩn bị và chèn bảng activities
                if isinstance(data.get("activities"), list):
                    for act in data["activities"]:
                        act_title = act.get("title")
                        if not act_title:
                            continue
                        act_description = act.get("description")
                        act_review_score = float(act["review_score"]) if act.get("review_score") is not None else None

                        price_amount = 0.00;
                        price_obj = act.get("price")
                        if price_obj:
                            if isinstance(price_obj.get("currency"), (int, float)):
                                price_amount = float(price_obj["currency"])
                            elif price_obj.get("display"):
                                try:
                                    per_book = price_obj["display"].get("perBook", {})
                                    total = per_book.get("total", {})
                                    all_inclusive = total.get("allInclusive", {})
                                    charge_total = all_inclusive.get("chargeTotal")
                                    if charge_total is not None:
                                        price_amount = float(charge_total)
                                except Exception:
                                    pass

                        act_query = """
                            INSERT INTO activities (hotel_id, title, description, price_amount, review_score)
                            VALUES (%s, %s, %s, %s, %s)
                        """
                        cur.execute(act_query, (hotel_id, act_title, act_description, price_amount, act_review_score))

                conn.commit()
            except Exception as e:
                conn.rollback()
                print(f"Lỗi chèn dữ liệu khách sạn ID {hotel_id}: {e}")

        print("Quá trình import dữ liệu hoàn tất thành công!")
        cur.close()
        conn.close()

    except Exception as e:
        print(f"Lỗi hệ thống hoặc lỗi kết nối: {e}")

if __name__ == "__main__":
    run_import()
