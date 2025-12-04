"""
Pytest configuration for codegen tests.
"""

import pytest


@pytest.fixture
def sample_data():
    """Sample JSON data for testing."""
    return {
        "user_id": 123,
        "name": "John Doe",
        "email": "john@example.com",
        "active": True,
        "score": 98.5,
    }


@pytest.fixture
def nested_data():
    """Sample nested JSON data."""
    return {
        "user": {
            "id": 1,
            "profile": {
                "name": "John",
                "age": 30,
            },
        }
    }


@pytest.fixture
def array_data():
    """Sample array JSON data."""
    return {
        "users": [
            {"id": 1, "name": "John"},
            {"id": 2, "name": "Jane"},
        ],
        "tags": ["python", "go", "rust"],
        "scores": [95, 87, 92],
    }
