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


def closest_path(path, paths):
    """
    Find the closest path from paths.

    LLM may output broken paths, this fixes them.

    :param path: Path to find closest
    :param paths: List of paths to search in.
    """
    parts = path.split('/')
    for number, part in enumerate(parts):
        paths_parts = {
            str(path).split('/')[number]
            for path in paths
        }
        if part not in paths_parts:
            path_part = closest(part, paths_parts)
            if not path_part:
                return None  # not found at all
        else:
            path_part = part

        parts[number] = path_part
        paths = {
            path
            for path in paths
            if str(path).startswith('/'.join(parts[:number + 1]))
        }

    return '/'.join(parts)
