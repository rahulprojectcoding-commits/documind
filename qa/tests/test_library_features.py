from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from qa.models import AnswerFeedback, AnswerRecord, Chunk, Collection, Document


class LibraryFeatureTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="reader",
            password="testpass123",
            email="reader@example.com",
        )
        self.client.login(username="reader", password="testpass123")

    @patch("qa.services.answer_question", return_value="The policy is 30 days [S1].")
    @patch("qa.services.get_relevant_chunks")
    def test_collection_answer_persists_page_citation(self, get_chunks, _answer):
        collection = Collection.objects.create(owner=self.user, name="Policies")
        document = Document.objects.create(
            owner=self.user,
            collection=collection,
            file="documents/policy.pdf",
            status="ready",
        )
        chunk = Chunk.objects.create(
            document=document,
            text="The return period is 30 days.",
            embedding=[0.0] * 768,
            order=0,
            page_number=4,
        )
        second_document = Document.objects.create(
            owner=self.user,
            collection=collection,
            file="documents/appendix.pdf",
            status="ready",
        )
        second_chunk = Chunk.objects.create(
            document=second_document,
            text="The policy applies to all purchases.",
            embedding=[0.0] * 768,
            order=2,
            page_number=9,
        )
        get_chunks.return_value = [chunk, second_chunk]

        response = self.client.post(
            reverse("collection_ask", args=[collection.id]),
            {"question": "What is the return period?"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "[S1]")
        self.assertContains(response, "[S2]")
        self.assertContains(response, "page 4")
        self.assertContains(response, "page 9")
        record = AnswerRecord.objects.get(owner=self.user)
        self.assertEqual(record.sources[0]["page_number"], 4)
        self.assertEqual(record.sources[1]["document_title"], "appendix.pdf")
        self.assertEqual(record.collection, collection)

    def test_library_search_and_name_sort(self):
        Document.objects.create(
            owner=self.user,
            file="documents/zulu.txt",
            display_name="Zulu notes",
        )
        Document.objects.create(
            owner=self.user,
            file="documents/alpha.txt",
            display_name="Alpha notes",
        )

        response = self.client.get(reverse("upload"), {"q": "notes", "sort": "name"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [document.title for document in response.context["documents"]],
            ["Alpha notes", "Zulu notes"],
        )

    def test_collection_is_private_to_its_owner(self):
        other = User.objects.create_user(username="other", password="testpass123")
        collection = Collection.objects.create(owner=other, name="Private")
        response = self.client.get(reverse("collection_ask", args=[collection.id]))
        self.assertEqual(response.status_code, 404)

    @patch("qa.views.process_document_task.delay")
    def test_failed_document_can_be_retried(self, delay):
        document = Document.objects.create(
            owner=self.user,
            file="documents/retry.txt",
            status="failed",
            processing_error="The file could not be read.",
        )

        response = self.client.post(reverse("retry_document", args=[document.id]))

        self.assertRedirects(response, reverse("upload"))
        document.refresh_from_db()
        self.assertEqual(document.status, "processing")
        self.assertEqual(document.processing_error, "")
        delay.assert_called_once_with(document.id)

    def test_upload_rejects_unsupported_file_extension(self):
        upload = SimpleUploadedFile("malware.exe", b"not a supported document")
        response = self.client.post(reverse("upload"), {"document": upload})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Upload a PDF or TXT file.")
        self.assertFalse(Document.objects.filter(owner=self.user).exists())

    def test_feedback_is_saved_for_answer_owner(self):
        record = AnswerRecord.objects.create(
            owner=self.user,
            question="What is the return period?",
            answer="30 days.",
        )

        response = self.client.post(
            reverse("answer_feedback", args=[record.id]),
            {"rating": "helpful"},
        )

        self.assertRedirects(response, reverse("history"))
        feedback = AnswerFeedback.objects.get(answer=record, owner=self.user)
        self.assertEqual(feedback.rating, "helpful")
