require('dotenv').config();
const fs = require('fs');
const path = require('path');
const { Client } = require('pg');

// Khởi tạo Client kết nối đến Supabase PostgreSQL
const client = new Client({
  connectionString: process.env.DATABASE_URL,
});

async function run() {
  if (!process.env.DATABASE_URL || process.env.DATABASE_URL.includes('YOUR_PROJECT_ID_HERE')) {
    console.error('Lỗi: Bạn chưa cấu hình đúng DATABASE_URL trong file .env');
    process.exit(1);
  }

  try {
    await client.connect();
    console.log('Đã kết nối thành công đến Supabase database!');

    const processedDir = path.join(__dirname, 'processed');
    if (!fs.existsSync(processedDir)) {
      console.error(`Không tìm thấy thư mục processed tại: ${processedDir}`);
      process.exit(1);
    }

    const files = fs.readdirSync(processedDir).filter(f => f.endsWith('.json'));
    console.log(`Tìm thấy ${files.length} file dữ liệu JSON trong thư mục processed.`);

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      const filePath = path.join(processedDir, file);
      const rawData = fs.readFileSync(filePath, 'utf8');
      
      let data;
      try {
        data = JSON.parse(rawData);
      } catch (err) {
        console.error(`Lỗi parse JSON file ${file}:`, err.message);
        continue;
      }

      const hotelId = data.hotel_id;
      if (!hotelId) {
        console.warn(`File ${file} không chứa hotel_id. Bỏ qua.`);
        continue;
      }

      console.log(`[${i + 1}/${files.length}] Đang import khách sạn: ${data.name} (ID: ${hotelId})...`);

      // Bắt đầu Transaction cho mỗi khách sạn để đảm bảo tính toàn vẹn dữ liệu
      await client.query('BEGIN');

      try {
        // 1. Chuẩn bị dữ liệu cho bảng hotels
        const name = data.name || 'Không rõ tên';
        const accommodationType = data.accommodation_type || null;
        const starRating = data.star_rating !== undefined && data.star_rating !== null ? parseFloat(data.star_rating) : null;
        const isLuxury = data.is_luxury === true || data.is_luxury === 'true';
        const reviewScore = data.review_score !== undefined && data.review_score !== null ? parseFloat(data.review_score) : null;
        const reviewCount = data.review_count !== undefined && data.review_count !== null ? parseInt(data.review_count, 10) : 0;
        const address = data.address || null;
        const city = data.city || data.province || null;
        const latitude = data.latitude !== undefined && data.latitude !== null ? parseFloat(data.latitude) : null;
        const longitude = data.longitude !== undefined && data.longitude !== null ? parseFloat(data.longitude) : null;
        const description = data.description || null;
        const amenities = Array.isArray(data.amenities) ? data.amenities : [];
        const usefulInfo = data.useful_info || null;

        // policyNotes
        let policyNotes = null;
        if (data.secondary && data.secondary.hotel_policy && Array.isArray(data.secondary.hotel_policy.policyNotes)) {
          policyNotes = data.secondary.hotel_policy.policyNotes;
        }

        const suitableFor = Array.isArray(data.suitable_for) ? data.suitable_for : [];

        // reviews_detail - lưu mảng reviews của khách hàng theo feedback của bạn
        let reviewsDetail = null;
        if (data.reviews_detail && Array.isArray(data.reviews_detail.reviews)) {
          reviewsDetail = JSON.stringify(data.reviews_detail.reviews);
        }

        // images
        let images = [];
        if (Array.isArray(data.image_urls)) {
          images = data.image_urls;
        } else if (Array.isArray(data.images)) {
          images = data.images.map(img => img.url).filter(Boolean);
        }

        const sourceUrl = data.source_url || null;

        // 2. Chèn hoặc cập nhật bảng hotels
        const hotelQuery = `
          INSERT INTO hotels (
            id, name, accommodation_type, star_rating, is_luxury, review_score, review_count, 
            address, city, latitude, longitude, description, amenities, useful_info, 
            policyNotes, suitable_for, reviews_detail, images, source_url
          ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19
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
        `;

        await client.query(hotelQuery, [
          hotelId, name, accommodationType, starRating, isLuxury, reviewScore, reviewCount,
          address, city, latitude, longitude, description, amenities, usefulInfo,
          policyNotes, suitableFor, reviewsDetail, images, sourceUrl
        ]);

        // Xóa sạch phòng, địa danh, hoạt động cũ của khách sạn này trước khi import mới (đảm bảo tính idempotent)
        await client.query('DELETE FROM rooms WHERE hotel_id = $1', [hotelId]);
        await client.query('DELETE FROM nearby_places WHERE hotel_id = $1', [hotelId]);
        await client.query('DELETE FROM activities WHERE hotel_id = $1', [hotelId]);

        // 3. Chuẩn bị và chèn bảng rooms
        let roomsList = [];
        if (Array.isArray(data.rooms)) {
          roomsList = data.rooms;
        } else if (data.room_grid && Array.isArray(data.room_grid.rooms)) {
          roomsList = data.room_grid.rooms;
        }

        for (const room of roomsList) {
          const roomTypeId = room.room_type_id ? BigInt(room.room_type_id) : null;
          const roomName = room.name || 'Không rõ tên phòng';
          const price = room.price_per_night !== undefined && room.price_per_night !== null ? parseFloat(room.price_per_night) : null;
          
          let roomSize = null;
          if (room.room_size) {
            roomSize = String(room.room_size);
          } else if (room.size_sqm !== undefined && room.size_sqm !== null) {
            roomSize = `${room.size_sqm} m²`;
          }

          const maxOccupancy = room.max_occupancy !== undefined && room.max_occupancy !== null ? parseInt(room.max_occupancy, 10) : 2;
          const bedType = room.bed_type || null;
          const roomView = room.room_view || null;
          const roomAmenities = Array.isArray(room.room_amenities) ? room.room_amenities : [];
          const roomImages = Array.isArray(room.images) ? room.images : [];
          const roomReviewScore = room.review_score !== undefined && room.review_score !== null ? parseFloat(room.review_score) : null;

          const roomQuery = `
            INSERT INTO rooms (
              hotel_id, room_type_id, name, price, room_size, max_occupancy, 
              bed_type, room_view, room_amenities, images, review_score
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
          `;

          await client.query(roomQuery, [
            hotelId, roomTypeId, roomName, price, roomSize, maxOccupancy,
            bedType, roomView, roomAmenities, roomImages, roomReviewScore
          ]);
        }

        // 4. Chuẩn bị và chèn bảng nearby_places
        if (Array.isArray(data.nearby_places)) {
          for (const place of data.nearby_places) {
            const placeName = place.name;
            if (!placeName) continue;
            const placeType = place.type || null;
            const distanceKm = place.distance_km !== undefined && place.distance_km !== null ? parseFloat(place.distance_km) : null;

            const placeQuery = `
              INSERT INTO nearby_places (hotel_id, name, type, distance_km)
              VALUES ($1, $2, $3, $4)
            `;
            await client.query(placeQuery, [hotelId, placeName, placeType, distanceKm]);
          }
        }

        // 5. Chuẩn bị và chèn bảng activities
        if (Array.isArray(data.activities)) {
          for (const act of data.activities) {
            const actTitle = act.title;
            if (!actTitle) continue;
            const actDescription = act.description || null;
            const actReviewScore = act.review_score !== undefined && act.review_score !== null ? parseFloat(act.review_score) : null;
            
            let priceAmount = 0.00;
            if (act.price) {
              if (act.price.currency && typeof act.price.currency === 'number') {
                priceAmount = act.price.currency;
              } else if (act.price.display && act.price.display.perBook && act.price.display.perBook.total && act.price.display.perBook.total.allInclusive && act.price.display.perBook.total.allInclusive.chargeTotal) {
                priceAmount = parseFloat(act.price.display.perBook.total.allInclusive.chargeTotal);
              }
            }

            const actQuery = `
              INSERT INTO activities (hotel_id, title, description, price_amount, review_score)
              VALUES ($1, $2, $3, $4, $5)
            `;
            await client.query(actQuery, [hotelId, actTitle, actDescription, priceAmount, actReviewScore]);
          }
        }

        await client.query('COMMIT');
      } catch (err) {
        await client.query('ROLLBACK');
        console.error(`Lỗi khi lưu dữ liệu khách sạn ID ${hotelId}:`, err.message);
      }
    }

    console.log('Quá trình import hoàn tất thành công!');
  } catch (err) {
    console.error('Lỗi kết nối cơ sở dữ liệu hoặc lỗi thực thi hệ thống:', err.message);
  } finally {
    await client.end();
  }
}

run();
