from unittest.mock import patch
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from qa.models import Document


class UploadViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alice", password="testpass123")
        self.client.login(username="alice", password="testpass123")

    def test_redirects_anonymous_users_to_login(self):
        self.client.logout()
        response = self.client.get(reverse("upload"))
        self.assertRedirects(response, f"/login/?next={reverse('upload')}")

    @patch("qa.views.process_document_task.delay")
    def test_upload_creates_document_owned_by_user(self, mock_delay):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_file = SimpleUploadedFile("test.txt", b"some content")

        response = self.client.post(reverse("upload"), {"document": fake_file})

        document = Document.objects.get()
        self.assertEqual(document.owner, self.user)
        mock_delay.assert_called_once_with(document.id)
        self.assertRedirects(response, reverse("ask", args=[document.id]))

class AskViewTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(username="alice", password="testpass123")
        self.bob = User.objects.create_user(username="bob", password="testpass123")
        self.document = Document.objects.create(
            file="documents/example.pdf", owner=self.alice, status="ready"
        )

    @patch("qa.views.answer_question")
    @patch("qa.views.get_relevant_chunks")
    def test_owner_gets_an_answer(self, mock_get_chunks, mock_answer):
        mock_get_chunks.return_value = []
        mock_answer.return_value = "The company was founded in 2015."

        self.client.login(username="alice", password="testpass123")
        response = self.client.post(
            reverse("ask", args=[self.document.id]),
            {"question": "When was it founded?"},
        )

        self.assertContains(response, "The company was founded in 2015.")

    def test_other_user_gets_404(self):
        self.client.login(username="bob", password="testpass123")
        response = self.client.get(reverse("ask", args=[self.document.id]))
        self.assertEqual(response.status_code, 404)

    def test_unprocessed_document_hides_form(self):
        processing_doc = Document.objects.create(
            file="documents/example2.pdf", owner=self.alice, status="processing"
        )
        self.client.login(username="alice", password="testpass123")
        response = self.client.get(reverse("ask", args=[processing_doc.id]))
        self.assertContains(response, "still processing")