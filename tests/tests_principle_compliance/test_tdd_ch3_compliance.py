"""
Compliance test for TDD Chapter 3 rules.
Demonstrates: I/O Decoupling (Dependency Injection) and avoiding direct I/O.
"""
from typing import Callable, List
import pytest


# --- Domain Logic ---


class TodoApp:
    def __init__(
        self,
        input_func: Callable[[], str],
        output_func: Callable[[str], None]
    ):
        """Injectable I/O for testability (TDD Ch. 3)."""
        self.input_func = input_func
        self.output_func = output_func
        self.todos: List[str] = []

    def run_one_step(self) -> bool:
        """Runs one iteration of the REPL."""
        command = self.input_func()
        if command == "quit":
            return False
        
        if command.startswith("add "):
            item = command[4:]
            self.todos.append(item)
            self.output_func(f"Added: {item}")
        
        return True


# --- Tests ---


def test_io_decoupling() -> None:
    """Demonstrates testing interactive logic without real stdin/stdout."""
    # Arrange
    # Simulated User Input (Scripted)
    user_inputs = ["add Buy Milk", "quit"]
    input_iterator = iter(user_inputs)
    
    # Simulated User Output (Capture)
    captured_output: List[str] = []

    def mock_input() -> str:
        return next(input_iterator)

    def mock_output(msg: str) -> None:
        captured_output.append(msg)

    # Act
    app = TodoApp(input_func=mock_input, output_func=mock_output)
    
    # Run loop strictly controlled
    while app.run_one_step():
        pass

    # Assert
    assert app.todos == ["Buy Milk"]
    assert captured_output == ["Added: Buy Milk"]
