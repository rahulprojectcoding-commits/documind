from .llm import answer_question
from .models import AnswerRecord
from .retrieval import get_relevant_chunks


def answer_for_documents(*, owner, question, documents, document=None, collection=None):
    chunks = list(get_relevant_chunks(documents, question))
    sources = []
    prompt_sources = []

    for index, chunk in enumerate(chunks, start=1):
        label = f"S{index}"
        title = chunk.document.title
        page_number = chunk.page_number
        source = {
            "label": label,
            "document_id": chunk.document_id,
            "document_title": title,
            "page_number": page_number,
            "chunk_order": chunk.order,
            "text": chunk.text,
        }
        sources.append(source)
        location = f", page {page_number}" if page_number else f", section {chunk.order + 1}"
        prompt_sources.append(
            f"[{label}] {title}{location}\n"
            f"<source_text>\n{chunk.text}\n</source_text>"
        )

    answer = answer_question("\n\n".join(prompt_sources), question)
    record = AnswerRecord.objects.create(
        owner=owner,
        document=document,
        collection=collection,
        question=question,
        answer=answer,
        sources=sources,
    )
    return answer, sources, record
