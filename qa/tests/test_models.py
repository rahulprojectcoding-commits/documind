from django.test import TestCase
from django.contrib.auth.models import User
from qa.models import Document, Chunk


class DocumentModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_document_str_returns_filename(self):
        document = Document.objects.create(file="documents/example.pdf", owner=self.user)
        self.assertEqual(str(document), "documents/example.pdf")

    def test_document_defaults_to_processing_status(self):
        document = Document.objects.create(file="documents/example.pdf", owner=self.user)
        self.assertEqual(document.status, "processing")

    def test_chunk_ordering(self):
        document = Document.objects.create(file="documents/example.pdf", owner=self.user)
        Chunk.objects.create(document=document, text="second", embedding=[0.0] * 768, order=1)
        Chunk.objects.create(document=document, text="first", embedding=[0.0] * 768, order=0)

        ordered_texts = list(document.chunks.values_list("text", flat=True))
        self.assertEqual(ordered_texts, ["first", "second"])