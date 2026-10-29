from .extraction import extract_pages
from .chunking import chunk_text
from .embeddings import embed_text
from .models import Chunk


def process_document(document):
    document.file.open()
    try:
        pages = extract_pages(document.file)
    finally:
        document.file.close()

    order = 0
    for page_number, text in pages:
        for piece in chunk_text(text):
            vector = embed_text(piece)
            Chunk.objects.create(
                document=document,
                text=piece,
                embedding=vector,
                order=order,
                page_number=page_number,
            )
            order += 1

    if order == 0:
        raise ValueError("No readable text was found in this file.")
