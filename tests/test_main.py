"""
Sample tests for FastAPI application
"""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_read_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_item():
    """Test create item endpoint"""
    item_data = {
        "name": "Test Item",
        "description": "A test item",
        "price": 10.99,
        "tax": 1.10
    }
    response = client.post("/items/", json=item_data)
    assert response.status_code == 200
    data = response.json()
    assert data["item"]["name"] == "Test Item"
    assert data["message"] == "Item created successfully"
