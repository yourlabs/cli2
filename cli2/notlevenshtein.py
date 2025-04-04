"""
Like levenshtein with difflib.

.. code-block:: python

        source_word = "apple"
        word_list = ["apply", "aple", "banana", "orange", "applet"]

        closest = cli2.closest(source_word, word_list)
        print(f"The closest word to '{source_word}' is: {closest}")
"""

import difflib


def closest(source_token, token_list):
    """
    Finds the token in token_list with the shortest distance to source_token.

    :param source_token: The source token (string).
    :param token_list: A list of tokens (strings).
    :return: The token with the shortest distance, or None if token_list is
             empty.
    """

    if not token_list:
        return None

    closest_token = None
    shortest_distance = float("inf")  # Initialize with infinity

    for token in token_list:
        matcher = difflib.SequenceMatcher(None, source_token, token)
        distance = (
            1 - matcher.ratio()
        )  # Calculate a distance metric (1 - similarity ratio)

        if distance < shortest_distance:
            shortest_distance = distance
            closest_token = token

    return closest_token
