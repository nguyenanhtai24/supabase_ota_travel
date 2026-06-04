def test_combo_suggest_success(client, mock_db):
    """Test 1: Gợi ý combo thành công khi trong ngân sách."""
    cursor = mock_db["cursor"]
    cursor.fetchall.side_effect = [
        [{"id": 1, "name": "Hotel Test", "star_rating": 4, "review_score": 8.5, "suitable_for": ["Family"], "city": "Đà Nẵng"}], # hotels_list
        [{"id": 10, "title": "Tour 1", "description": "Desc", "price_amount": 100000.0, "review_score": 8.0}] # activities
    ]
    cursor.fetchone.return_value = {"id": 100, "name": "Standard Room", "price": 500000.0, "max_occupancy": 2}
    
    response = client.get("/api/hotels/combo-suggest?city=Đà Nẵng&budget_total=2000000", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["hotel"]["name"] == "Hotel Test"
    assert data["total_cost"] == 700000.0  # 500000 + 100000*2

def test_combo_suggest_budget_too_low(client, mock_db):
    """Test 2: Trả về 404 nếu ngân sách quá thấp không đủ thuê phòng."""
    cursor = mock_db["cursor"]
    cursor.fetchall.return_value = [{"id": 1, "name": "Hotel Test", "star_rating": 4, "review_score": 8.5, "suitable_for": ["Family"], "city": "Đà Nẵng"}]
    cursor.fetchone.return_value = {"id": 100, "name": "Standard Room", "price": 500000.0, "max_occupancy": 2}
    
    response = client.get("/api/hotels/combo-suggest?city=Đà Nẵng&budget_total=100000", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Không tìm thấy combo nào phù hợp ngân sách của bạn."

def test_hotel_combo_details(client, mock_db):
    """Test 3: Lấy gợi ý combo cho một khách sạn cụ thể."""
    cursor = mock_db["cursor"]
    cursor.fetchone.side_effect = [
        {"id": 1, "name": "Hotel Test", "star_rating": 4, "review_score": 8.5}, # hotel
        {"name": "Standard Room", "price": 500000.0, "room_view": "Garden"} # room
    ]
    cursor.fetchall.return_value = [
        {"id": 10, "title": "Tour 1", "price_amount": 100000.0, "review_score": 8.0}
    ]
    
    response = client.get("/api/hotels/1/combo", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 200
    data = response.json()
    assert data["hotel"]["name"] == "Hotel Test"
    assert len(data["activities"]) == 1
    assert data["estimated_total"] == 1200000.0  # (500000 * 2 nights) + 100000 * 2 guests

def test_hotel_combo_not_found(client, mock_db):
    """Test 4: Trả về 404 nếu khách sạn không tồn tại."""
    cursor = mock_db["cursor"]
    cursor.fetchone.return_value = None
    
    response = client.get("/api/hotels/999/combo", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 404

def test_hotel_combo_no_rooms(client, mock_db):
    """Test 5: Trả về 404 nếu khách sạn chưa được thiết lập dữ liệu phòng."""
    cursor = mock_db["cursor"]
    cursor.fetchone.side_effect = [
        {"id": 1, "name": "Hotel Test", "star_rating": 4, "review_score": 8.5}, # hotel
        None # room
    ]
    
    response = client.get("/api/hotels/1/combo", headers={"X-API-Key": "ota_sk_test_token"})
    assert response.status_code == 404
    assert response.json()["detail"] == "Khách sạn này chưa có dữ liệu phòng."
