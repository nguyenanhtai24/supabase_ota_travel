def test_get_hotel_rooms_success(client, mock_db):
    """Test 1: GET /api/hotels/{id}/rooms returns room list successfully."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = [
        {
            "id": 10,
            "hotel_id": 1,
            "room_type_id": 101,
            "name": "Deluxe Room",
            "price": 1200000.0,
            "room_size": "30 m²",
            "max_occupancy": 2,
            "bed_type": "Double",
            "room_view": "City",
            "room_amenities": ["AC", "TV"],
            "images": ["http://image1.jpg"],
            "review_score": 8.0
        }
    ]
    
    response = client.get("/api/hotels/1/rooms", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["hotel_id"] == 1
    assert len(data["rooms"]) == 1
    assert data["rooms"][0]["name"] == "Deluxe Room"
    assert data["rooms"][0]["room_type_id"] == "101"

def test_get_hotel_rooms_not_found(client, mock_db):
    """Test 2: GET /api/hotels/{id}/rooms returns empty list if no rooms exist."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = []
    
    response = client.get("/api/hotels/999/rooms", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["rooms"]) == 0

def test_get_room_by_id_success(client, mock_db):
    """Test 3: GET /api/rooms/{id} returns details for a valid room."""
    cursor = mock_db["cursor"]
    cursor.fetchone.return_value = {
        "id": 10,
        "hotel_id": 1,
        "room_type_id": 101,
        "name": "Deluxe Room",
        "price": 1200000.0,
        "room_size": "30 m²",
        "max_occupancy": 2,
        "bed_type": "Double",
        "room_view": "City",
        "room_amenities": ["AC", "TV"],
        "images": ["http://image1.jpg"],
        "review_score": 8.0
    }
    
    response = client.get("/api/rooms/10", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 10
    assert data["name"] == "Deluxe Room"
    assert data["room_type_id"] == "101"
    assert data["images"] == ["http://image1.jpg"]

def test_get_room_by_id_not_found(client, mock_db):
    """Test 4: GET /api/rooms/{id} returns 404 if room is not found."""
    cursor = mock_db["cursor"]
    cursor.fetchone.return_value = None
    
    response = client.get("/api/rooms/999", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Không tìm thấy phòng."

def test_get_hotel_rooms_filter(client, mock_db):
    """Test 5: GET /api/hotels/{id}/rooms supports filtering parameters."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = []
    
    response = client.get("/api/hotels/1/rooms?min_occupancy=4&room_view=Biển&sort_by=price:asc", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    # verify cursor was executed
    assert cursor.execute.called
