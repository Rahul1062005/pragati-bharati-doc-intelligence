import logging
from app.core.database import SessionLocal
from app.services.question_service import question_service

logger = logging.getLogger(__name__)

async def process_document_task(document_id: str):
    """
    Background worker task for processing uploaded documents asynchronously.
    """
    logger.info(f"Starting background processing for document: {document_id}")
    db = SessionLocal()
    try:
        await question_service.process_document_pipeline(db, document_id)
        logger.info(f"Finished processing for document: {document_id}")
    except Exception as e:
        logger.error(f"Error in background task for document {document_id}: {e}", exc_info=True)
    finally:
        db.close()
