import pytest
import cli2


def test_find_closest_token_basic():
    source_word = "apple"
    word_list = ["apply", "aple", "banana", "orange", "applet"]
    assert cli2.closest(source_word, word_list) == "applet"


def test_find_closest_token_exact_match():
    source_word = "cat"
    word_list = ["dog", "cat", "bat"]
    assert cli2.closest(source_word, word_list) == "cat"


def test_find_closest_token_multiple_close():
    source_word = "car"
    word_list = ["card", "cart", "care"]
    assert cli2.closest(source_word, word_list) == "card"


def test_find_closest_token_empty_list():
    source_word = "test"
    word_list = []
    assert cli2.closest(source_word, word_list) is None


def test_find_closest_token_no_close_match():
    source_word = "xyz"
    word_list = ["apple", "banana", "orange"]
    # difflib will pick the first if no close matches.
    assert cli2.closest(source_word, word_list) == "apple"


def test_find_closest_token_different_lengths():
    source_word = "longword"
    word_list = ["short", "longer", "longestword"]
    assert cli2.closest(source_word, word_list) == "longestword"


def test_find_closest_token_same_distance_multiple():
  source_word = "test"
  word_list = ["tesa", "tesb", "tesc"]
  # difflib will pick the first if same distances.
  assert cli2.closest(source_word, word_list) == "tesa"
