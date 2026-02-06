"""
Compliance test for TDD Chapter 11 rules.
Demonstrates: Mocking external APIs (Network isolation) vs WSGI-like structure.
"""

from typing import Any
from unittest.mock import MagicMock

# --- Domains ---


class ExternalClient:
    def __init__(self, requester: Any) -> None:
        """Dependency Injection for the HTTP requester."""
        self.requester = requester

    def fetch_user(self, user_id: int) -> dict[str, Any]:
        """Fetches user data from external API."""
        response = self.requester.get(f"https://api.example.com/users/{user_id}")
        result: dict[str, Any] = response.json()
        return result


# --- Tests ---


def test_external_api_mocking() -> None:
    """
    Demonstrates Rule 2.11: Mock ALL external requests.

    We don't use 'requests-mock' library to avoid adding a dependency
    just for this specific compliance test, but we demonstrate the
    PRINCIPLE using unittest.mock which is standard.
    """
    # Arrange
    mock_requester = MagicMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 1, "name": "Alice"}
    mock_requester.get.return_value = mock_response

    client = ExternalClient(mock_requester)

    # Act
    data = client.fetch_user(1)

    # Assert
    assert data["name"] == "Alice"
    mock_requester.get.assert_called_with("https://api.example.com/users/1")
