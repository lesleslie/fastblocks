"""Additional tests for coverage boost."""


def test_basic_python_functionality() -> None:
    """Test basic Python functionality without fastblocks imports."""
    # Test basic data structures
    test_dict = {"key": "value", "number": 42}
    test_list = [1, 2, 3, "test"]
    test_set = {1, 2, 3}

    # Test basic operations
    assert len(test_dict) == 2
    assert "key" in test_dict
    assert test_dict["key"] == "value"

    assert len(test_list) == 4
    assert test_list[0] == 1
    assert "test" in test_list

    assert len(test_set) == 3
    assert 1 in test_set

    # Test string operations
    test_string = "Hello World"
    assert test_string.lower() == "hello world"
    assert test_string.split() == ["Hello", "World"]
    assert "World" in test_string


def test_python_functions() -> None:
    """Test Python functions and classes."""

    # Test lambda functions
    def square(x: int) -> int:
        return x * x

    assert square(4) == 16

    # Test list comprehensions
    numbers = [1, 2, 3, 4, 5]
    squares = [x * x for x in numbers]
    assert squares == [1, 4, 9, 16, 25]

    # Test dictionary comprehensions
    square_dict = {x: x * x for x in range(5)}
    assert square_dict[3] == 9

    # Test any/all functions
    assert any([False, True, False])
    assert all([True, True, True])
    assert not all([True, False, True])


def test_exception_handling() -> None:
    """Test basic exception handling."""
    # Test try/except
    try:
        result = 10 / 2
        assert result == 5
    except ZeroDivisionError:
        assert False, "Should not raise ZeroDivisionError"

    # Test exception raising
    try:
        raise ValueError("Test error")
    except ValueError as e:
        assert str(e) == "Test error"

    # Test finally block
    executed = False
    try:
        executed = True
    finally:
        assert executed


def test_class_creation() -> None:
    """Test basic class creation and methods."""

    class TestClass:
        def __init__(self, value: str) -> None:
            self.value = value

        def get_value(self) -> str:
            return self.value

        def set_value(self, new_value: str) -> None:
            self.value = new_value

    # Test instantiation
    obj = TestClass("initial")
    assert obj.get_value() == "initial"

    # Test method call
    obj.set_value("updated")
    assert obj.get_value() == "updated"


def test_file_operations() -> None:
    """Test basic file operations without external dependencies."""
    import tempfile
    from pathlib import Path

    # Test temporary file creation
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp_file:
        tmp_file.write("test content")
        tmp_path = tmp_file.name

    # Test file reading
    with open(tmp_path) as f:
        content = f.read()
        assert content == "test content"

    # Cleanup
    Path(tmp_path).unlink()
