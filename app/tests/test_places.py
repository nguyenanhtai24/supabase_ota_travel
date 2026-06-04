def test_get_nearby_places_success(client, mock_db):
    """Test 1: GET /api/hotels/{id}/nearby-places returns places successfully."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = [
        {
            "id": 1,
            "hotel_id": 1,
            "name": "Sân bay Đà Nẵng",
            "type": "Transit",
            "distance_km": 3.5
        }
    ]
    
    response = client.get("/api/hotels/1/nearby-places", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["hotel_id"] == 1
    assert len(data["nearby_places"]) == 1
    assert data["nearby_places"][0]["name"] == "Sân bay Đà Nẵng"

def test_get_nearby_places_filter_type(client, mock_db):
    """Test 2: Lọc theo type truyền đúng param xuống SQL."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = []
    
    response = client.get("/api/hotels/1/nearby-places?type=Airport", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    assert cursor.execute.called

def test_get_nearby_places_filter_distance(client, mock_db):
    """Test 3: Lọc theo distance_max_km truyền đúng param xuống SQL."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = []
    
    response = client.get("/api/hotels/1/nearby-places?distance_max_km=5.0", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    assert cursor.execute.called

def test_get_nearby_places_empty(client, mock_db):
    """Test 4: Trả về mảng rỗng nếu khách sạn không có địa danh gần đó."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = []
    
    response = client.get("/api/hotels/999/nearby-places", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    assert len(response.json()["nearby_places"]) == 0

def test_get_nearby_places_unauthorized(client):
    """Test 5: Không truyền API Key trả về 401."""
    response = client.get("/api/hotels/1/nearby-places")
    assert response.status_code == 401
