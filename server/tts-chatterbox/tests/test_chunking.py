from app.chunking import split_text


def test_short_text_is_unchanged() -> None:
    assert split_text("Hello there.", 100) == ["Hello there."]


def test_long_text_is_split_without_losing_words() -> None:
    original = "One short sentence. Another sentence with several words. Final sentence."
    chunks = split_text(original, 32)

    assert len(chunks) > 1
    assert " ".join(chunks) == original
    assert all(len(chunk) <= 32 for chunk in chunks)
