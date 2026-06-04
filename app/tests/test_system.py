def test_health_success(client):
    """Test 1: Health check endpoint returns 200 OK."""
    response = client.get("/health")
    assert response.status_code == 200

def test_health_method_not_allowed(client):
    """Test 2: POST /health returns 405 Method Not Allowed."""
    response = client.post("/health")
    assert response.status_code == 405

def test_health_no_auth_needed(client):
    """Test 3: Calling /health without X-API-Key does NOT return 401."""
    response = client.get("/health")
    assert response.status_code != 401

def test_health_response_structure(client):
    """Test 4: Response has status, version, and message."""
    response = client.get("/health")
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "message" in data
    assert data["status"] == "OK"

def test_health_extra_query_params(client):
    """Test 5: Extra query parameters are ignored and request still succeeds."""
    response = client.get("/health?dummy=value&another=123")
    assert response.status_code == 200
    assert response.json()["status"] == "OK"
