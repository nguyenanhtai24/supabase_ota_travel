def test_get_hotels_without_key(client):
    """Test 1: GET /api/hotels without API Key returns 401."""
    response = client.get("/api/hotels")
    assert response.status_code == 401

def test_get_hotels_invalid_key(client):
    """Test 2: GET /api/hotels with wrong key returns 401."""
    response = client.get("/api/hotels", headers={"X-API-Key": "wrong_token"})
    assert response.status_code == 401

def test_get_hotels_success(client, mock_db):
    """Test 3: GET /api/hotels succeeds and returns correct payload format."""
    cursor = mock_db["cursor"]
    cursor.fetchone.return_value = {"count": 1}
    cursor.fetchall.return_value = [{
        "id": 1,
        "name": "Hotel Test",
        "accommodation_type": "Hotel",
        "star_rating": 4.0,
        "is_luxury": False,
        "review_score": 8.5,
        "review_count": 100,
        "address": "123 Street",
        "city": "Da Nang",
        "latitude": 16.0,
        "longitude": 108.0,
        "description": "A nice test hotel",
        "amenities": ["Wifi"],
        "suitable_for": ["Family"],
        "policynotes": ["No pets"],
        "useful_info": {},
        "images": ["http://image.url"],
        "min_price": 500000.0
    }]
    
    response = client.get("/api/hotels", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["data"]) == 1
    assert data["data"][0]["name"] == "Hotel Test"
    assert data["data"][0]["policyNotes"] == ["No pets"]

def test_get_hotel_by_id_success(client, mock_db):
    """Test 4: GET /api/hotels/{id} returns details for a valid hotel."""
    cursor = mock_db["cursor"]
    cursor.fetchone.return_value = {
        "id": 1,
        "name": "Hotel Test Detail",
        "accommodation_type": "Hotel",
        "star_rating": 4.0,
        "is_luxury": False,
        "review_score": 8.5,
        "review_count": 100,
        "address": "123 Street",
        "city": "Da Nang",
        "latitude": 16.0,
        "longitude": 108.0,
        "description": "A nice test hotel detailed info",
        "amenities": ["Wifi"],
        "suitable_for": ["Family"],
        "policynotes": ["No pets"],
        "useful_info": {},
        "images": ["http://image.url"],
        "reviews_detail": [],
        "source_url": "http://source"
    }
    
    response = client.get("/api/hotels/1", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Hotel Test Detail"
    assert data["policyNotes"] == ["No pets"]

def test_get_hotel_by_id_not_found(client, mock_db):
    """Test 5: GET /api/hotels/{id} returns 404 if hotel is not found."""
    cursor = mock_db["cursor"]
    cursor.fetchone.return_value = None
    
    response = client.get("/api/hotels/999", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Không tìm thấy khách sạn."
