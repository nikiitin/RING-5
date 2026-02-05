"""
Compliance test for TDD Chapter 2 rules.
Demonstrates: Test Doubles (Stub, Spy, Fake) and spec=True usage.
"""
from unittest.mock import create_autospec


# --- Domain Interfaces ---


class NetworkService:
    def send(self, message: str) -> bool:
        """Real implementation (expensive)."""
        raise NotImplementedError("Expensive network call")


class ChatClient:
    def __init__(self, service: NetworkService):
        self.service = service

    def broadcast(self, message: str) -> str:
        if self.service.send(message):
            return "Sent"
        return "Failed"


# --- Tests ---


def test_stub_double() -> None:
    """Demonstrates a Stub (Canned Answer)."""
    # Arrange
    # spec=True prevents calling methods that don't exist on NetworkService
    stub_service = create_autospec(NetworkService, instance=True)
    stub_service.send.return_value = True  # Canned answer

    client = ChatClient(stub_service)

    # Act
    result = client.broadcast("Hello")

    # Assert
    assert result == "Sent"


def test_spy_double() -> None:
    """Demonstrates a Spy (Behavior Tracking)."""
    # Arrange
    spy_service = create_autospec(NetworkService, instance=True)
    spy_service.send.return_value = True
    client = ChatClient(spy_service)

    # Act
    client.broadcast("Hello")

    # Assert behavior (Spying)
    spy_service.send.assert_called_once_with("Hello")


class FakeNetworkService:
    """A Fake implementation (lightweight logic)."""
    def __init__(self) -> None:
        self.messages: list[str] = []

    def send(self, message: str) -> bool:
        self.messages.append(message)
        return True

def test_fake_double() -> None:
    """Demonstrates a Fake (Working implementation)."""
    # Arrange
    fake_service = FakeNetworkService()
    client = ChatClient(fake_service)  # type: ignore [arg-type]

    # Act
    client.broadcast("Hello Fake")

    # Assert state (not behavior)
    assert "Hello Fake" in fake_service.messages
