import re


def normalize_description(text):
    if not text:
        return set()

    text = text.lower()

    # Remove punctuation
    text = re.sub(r"[^\w\s]", "", text)

    # Split into individual words
    return set(text.split())


def jaccard_similarity(text_a, text_b):
    words_a = normalize_description(text_a)
    words_b = normalize_description(text_b)

    # No meaningful text to compare
    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b

    return len(intersection) / len(union)