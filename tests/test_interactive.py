import cli2
from unittest import mock


def test_default_choices_y():
    with mock.patch("builtins.input", return_value="y"):
        result = cli2.choice("Test question")
        assert result == "y"


def test_default_choices_n():
    with mock.patch("builtins.input", return_value="n"):
        result = cli2.choice("Test question")
        assert result == "n"


def test_custom_choices():
    with mock.patch("builtins.input", return_value="b"):
        result = cli2.choice("Test question", choices=["a", "b", "c"])
        assert result == "b"


def test_default_value_provided():
    with mock.patch("builtins.input", return_value=""):
        result = cli2.choice("Test question", choices=["a", "b", "c"], default="b")
        assert result == "b"


def test_default_value_not_provided():
    with mock.patch("builtins.input", return_value=""):
        result = cli2.choice("Test question", choices=["a", "b", "c"])
        assert result is None  # because the while loop breaks without return.


def test_case_insensitive_input():
    with mock.patch("builtins.input", return_value="A"):
        result = cli2.choice("Test question", choices=["a", "b", "c"])
        assert result == "a"


def test_invalid_input():
    with mock.patch("builtins.input", side_effect=["d", "a"]):
        result = cli2.choice("Test question", choices=["a", "b", "c"])
        assert result == "a"


def test_empty_choices_defaults_to_yn():
    with mock.patch("builtins.input", return_value="y"):
        result = cli2.choice("Test question", choices=[])
        assert result == "y"
