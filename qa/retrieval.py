from pgvector.django import CosineDistance
from .embeddings import embed_text
from .models import Chunk, Document


def get_relevant_chunks(document_or_documents, question, top_k=5):
    question_vector = embed_text(question)

    chunks = Chunk.objects.all()
    if isinstance(document_or_documents, Document):
        chunks = chunks.filter(document=document_or_documents)
    else:
        chunks = chunks.filter(document__in=document_or_documents)

    return chunks.annotate(
        distance=CosineDistance("embedding", question_vector)
    ).select_related("document").order_by("distance")[:top_k]
