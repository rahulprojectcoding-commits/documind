from celery import shared_task
import logging
from .models import Document
from .ingestion import process_document as _process_document

logger = logging.getLogger(__name__)


@shared_task
def process_document_task(document_id):
    document = Document.objects.filter(id=document_id).first()
    if document is None:
        return

    try:
        document.chunks.all().delete()
        _process_document(document)
        document.status = "ready"
        document.processing_error = ""
    except ValueError as exc:
        document.status = "failed"
        document.processing_error = str(exc)[:500]
        document.chunks.all().delete()
    except Exception:
        logger.exception("Document processing failed for document %s", document_id)
        document.status = "failed"
        document.processing_error = (
            "Processing failed unexpectedly. Retry the document; if it fails again, "
            "check the server logs."
        )
        document.chunks.all().delete()
    document.save(update_fields=["status", "processing_error"])
