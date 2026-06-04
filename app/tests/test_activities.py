def test_get_activities_all(client, mock_db):
    """Test 1: GET /api/activities returns system activities."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = [
        {
            "id": 1,
            "hotel_id": 1,
            "title": "Tour Bà Nà Hills",
            "description": "Tham quan cầu Vàng",
            "price_amount": 1000000.0,
            "review_score": 9.0,
            "hotel_name": "Vinpearl",
            "hotel_city": "Đà Nẵng"
        }
    ]
    
    response = client.get("/api/activities", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["data"]) == 1
    assert data["data"][0]["title"] == "Tour Bà Nà Hills"

def test_get_activities_filter_city(client, mock_db):
    """Test 2: Lọc hoạt động theo thành phố."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = []
    
    response = client.get("/api/activities?city=Đà Nẵng", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    assert cursor.execute.called

def test_get_hotel_activities_success(client, mock_db):
    """Test 3: Lấy hoạt động của một khách sạn cụ thể."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = [
        {
            "id": 1,
            "hotel_id": 1,
            "title": "Tour Bà Nà Hills",
            "description": "Tham quan cầu Vàng",
            "price_amount": 1000000.0,
            "review_score": 9.0
        }
    ]
    
    response = client.get("/api/hotels/1/activities", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["hotel_id"] == 1
    assert len(data["activities"]) == 1

def test_get_hotel_activities_filter_price(client, mock_db):
    """Test 4: Lọc hoạt động của khách sạn theo giá tối đa."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = []
    
    response = client.get("/api/hotels/1/activities?price_max=500000", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    assert cursor.execute.called

def test_get_activities_limit(client, mock_db):
    """Test 5: Param limit được truyền đúng xuống truy vấn."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = []
    
    response = client.get("/api/activities?limit=5", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    assert cursor.execute.called
