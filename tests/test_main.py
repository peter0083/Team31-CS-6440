"""
Sample tests for FastAPI application
"""
from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


def test_placeholder():
    """Test root endpoint"""
    print("unit test placeholder")
    assert True
