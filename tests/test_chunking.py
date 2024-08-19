"""
Unit tests for utils.chunking module.
"""

from utils.chunking import chunk_large_text, preindex_process_text


def test_chunk_large_text():
    """
    test chunk_large_text function
    """
    text = (
        "This is a long paragraph. Here is a question? Here is the answer to that question. "
        "Another unrelated sentence. Another question? The answer is this. "
        "A very long sentence that should be split. And another one."
    )
    max_chunk_size = 50

    expected_chunks = [
        "This is a long paragraph.",
        "Here is a question?",
        "Here is the answer to that question.",
        "Another unrelated sentence.",
        "Another question? The answer is this.",
        "A very long sentence that should be split.",
        "And another one.",
    ]

    result = chunk_large_text(text, max_chunk_size)
    assert result == expected_chunks


def test_preindex_process_text():
    """
    test preindex_process_text function
    """
    episode = {
        "title": "Episode 1",
        "author": "Author Name",
        "audio": "path/to/audio/file",
        "description": "This is a description.",
        "segments": [{"start": 0, "end": 10}, {"start": 11, "end": 20}],
        "text": str(
            "This is the first sentence."
            "This is the second sentence."
            "And this is the third sentence."
        ),
    }

    def mock_chunking_function(text, max_chunk_size=50):
        # Use the variables to avoid pylint warnings
        _ = text
        _ = max_chunk_size
        return [
            "This is the first sentence.",
            "This is the second sentence.",
            "And this is the third sentence.",
        ]

    documents = preindex_process_text(
        episode,
        chunking_function=mock_chunking_function,
        max_chunk_size=50,
    )

    expected_documents = [
        {
            "title": "Episode 1",
            "author": "Author Name",
            "text": "This is the first sentence.",
            "chunk_id": 0,
        },
        {
            "title": "Episode 1",
            "author": "Author Name",
            "text": "This is the second sentence.",
            "chunk_id": 1,
        },
        {
            "title": "Episode 1",
            "author": "Author Name",
            "text": "And this is the third sentence.",
            "chunk_id": 2,
        },
    ]

    assert documents == expected_documents
