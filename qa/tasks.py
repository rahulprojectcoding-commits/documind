from celery import shared_task
from .models import Document
from .ingestion import process_document as _process_document


@shared_task
def process_document_task(document_id):
    document = Document.objects.get(id=document_id)
    try:
        _process_document(document)
        document.status = "ready"
    except Exception:
        document.status = "failed"
    document.save()