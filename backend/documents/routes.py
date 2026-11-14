import asyncio
import logging
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from auth.dependencies import get_current_user
from auth.models import User
from database import get_db
from documents.chunker import chunk_pages
from documents.models import Document, DocumentChunk
from documents.parser import SUPPORTED, parse_document
from documents.schemas import DocumentResponse, UploadResponse
from rag.errors import AWSServiceError
from rag.services import get_services

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/docs", tags=["documents"])
MAX_BYTES = 10 * 1024 * 1024


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UploadResponse:
    filename = os.path.basename(file.filename or "upload")
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED:
        raise HTTPException(400, "Unsupported file type. Use PDF, DOCX, or PPTX.")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(413, "File exceeds the 10MB limit.")
    if not data:
        raise HTTPException(400, "File is empty.")

    try:
        pages = await asyncio.to_thread(parse_document, data, ext)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Could not parse document: {exc}") from exc
    chunks = chunk_pages(pages)
    if not chunks:
        raise HTTPException(400, "No extractable text found in document.")

    svc = get_services()
    try:
        vectors_values = await svc.embeddings.embed_batch([c for _, c in chunks])
    except AWSServiceError as exc:
        raise HTTPException(exc.status_code, exc.message) from exc

    doc = Document(user_id=user.id, filename=filename, file_type=ext, chunk_count=len(chunks))
    db.add(doc)
    db.flush()
    db.add_all(
        DocumentChunk(doc_id=doc.id, user_id=user.id, chunk_index=i, page_number=page, text=text)
        for i, (page, text) in enumerate(chunks)
    )
    vectors = [
        {
            "id": f"{doc.id}_{i}",
            "values": vec,
            "metadata": {
                "doc_id": str(doc.id),
                "filename": filename,
                "page_number": page,
                "chunk_index": i,
                "user_id": user.id,
                "text": text,
            },
        }
        for i, ((page, text), vec) in enumerate(zip(chunks, vectors_values))
    ]
    try:
        await svc.store.upsert(vectors)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception("Pinecone upsert failed")
        raise HTTPException(502, f"Vector store error: {exc}") from exc
    db.commit()
    db.refresh(doc)
    svc.retriever.invalidate(user.id)
    return UploadResponse(
        document=DocumentResponse.model_validate(doc),
        message=f"Indexed {len(chunks)} chunks.",
    )


@router.get("/list", response_model=list[DocumentResponse])
async def list_docs(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Document]:
    return list(db.scalars(select(Document).where(Document.user_id == user.id).order_by(Document.id.desc())).all())


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doc(doc_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    doc = db.get(Document, doc_id)
    if doc is None or doc.user_id != user.id:
        raise HTTPException(404, "Document not found")
    svc = get_services()
    try:
        await svc.store.delete_by_doc(str(doc_id))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Pinecone delete failed: %s", exc)
    db.execute(delete(DocumentChunk).where(DocumentChunk.doc_id == doc_id))
    db.delete(doc)
    db.commit()
    svc.retriever.invalidate(user.id)
