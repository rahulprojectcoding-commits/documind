from pgvector.django import CosineDistance
from .embeddings import embed_text
from .models import Chunk


def get_relevant_chunks(document, question, top_k=5):
    question_vector = embed_text(question)

    return (
        Chunk.objects
        .filter(document=document)
        .annotate(distance=CosineDistance("embedding", question_vector))
        .order_by("distance")[:top_k]
    )