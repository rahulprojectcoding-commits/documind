from google import genai
from google.genai import types
from django.conf import settings

_client = None


def _get_client():
    global _client
    if _client is None:
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client


def answer_question(document_text, question):
    prompt = f"--- DOCUMENT START ---\n{document_text}\n--- DOCUMENT END ---\n\nQuestion: {question}"

    response = _get_client().models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction="Answer using ONLY the document text provided. If the answer isn't there, say so."
        ),
    )
    return response.text