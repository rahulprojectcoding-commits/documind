from django.test import TestCase
from qa.chunking import chunk_text


class ChunkTextTests(TestCase):
    def test_short_text_returns_single_chunk(self):
        text = "This is a short sentence."
        chunks = chunk_text(text)
        self.assertEqual(len(chunks), 1)

    def test_long_text_splits_into_multiple_chunks(self):
        text = " ".join(["word"] * 2000)
        chunks = chunk_text(text)
        self.assertGreater(len(chunks), 1)

    def test_chunks_overlap(self):
        text = " ".join([f"word{i}" for i in range(2000)])
        chunks = chunk_text(text)

        first_chunk_words = chunks[0].split()
        second_chunk_words = chunks[1].split()

        overlap = set(first_chunk_words[-100:]) & set(second_chunk_words[:100])
        self.assertTrue(len(overlap) > 0)