from django.test import TestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from qa.forms import DocumentUploadForm, QuestionForm


class DocumentUploadFormTests(TestCase):
    def test_valid_with_file(self):
        fake_file = SimpleUploadedFile("test.txt", b"some file content")
        form = DocumentUploadForm(files={"document": fake_file})
        self.assertTrue(form.is_valid())

    def test_invalid_without_file(self):
        form = DocumentUploadForm(files={})
        self.assertFalse(form.is_valid())


class QuestionFormTests(TestCase):
    def test_valid_with_question(self):
        form = QuestionForm(data={"question": "What year was it founded?"})
        self.assertTrue(form.is_valid())

    def test_invalid_with_empty_question(self):
        form = QuestionForm(data={"question": ""})
        self.assertFalse(form.is_valid())