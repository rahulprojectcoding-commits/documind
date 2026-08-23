from .extraction import extract_text
from .chunking import chunk_text
from .embeddings import embed_text
from .models import Chunk


def process_document(document):
    document.file.open()
    text = extract_text(document.file)
    document.file.close()

    pieces = chunk_text(text)

    for i, piece in enumerate(pieces):
        vector = embed_text(piece)
        Chunk.objects.create(
            document=document,
            text=piece,
            embedding=vector,
            order=i,
        )