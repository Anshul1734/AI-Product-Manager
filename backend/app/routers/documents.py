"""
Uploaded-document endpoints.

    GET    /documents?workspace_id=...           list a workspace's documents
    POST   /documents        (multipart)          upload one file
    DELETE /documents/{doc_id}?workspace_id=...   remove one

Uploaded documents ground both `/generate` runs and `/knowledge/search` when
those requests carry the same `workspace_id`.
"""
from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile

from ..core.config.settings import settings
from ..rag.parsers import SUPPORTED_EXTENSIONS
from ..rag.uploads import UploadError, get_uploaded_documents
from ..schemas.requests import WORKSPACE_ID_PATTERN

router = APIRouter(prefix="/documents", tags=["documents"])


def _limits() -> Dict[str, Any]:
    return {
        "max_bytes": settings.UPLOAD_MAX_BYTES,
        "max_documents": settings.UPLOAD_MAX_DOCUMENTS,
        "supported_extensions": list(SUPPORTED_EXTENSIONS),
    }


def _raise(exc: UploadError) -> None:
    raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("")
async def list_documents(
    workspace_id: str = Query(..., pattern=WORKSPACE_ID_PATTERN),
) -> Dict[str, Any]:
    """List a workspace's documents, or explain why uploads are unavailable.

    Answers 200 even when uploads are not configured, so the UI can show the
    reason instead of a generic error.
    """
    reason = settings.uploads_unavailable_reason()
    if reason:
        return {"success": True, "data": {"enabled": False, "reason": reason, "documents": [], **_limits()}}

    try:
        documents = await get_uploaded_documents().list(workspace_id)
    except UploadError as exc:
        _raise(exc)
    return {"success": True, "data": {"enabled": True, "reason": None, "documents": documents, **_limits()}}


@router.post("")
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str = Form(..., pattern=WORKSPACE_ID_PATTERN),
) -> Dict[str, Any]:
    """Parse, chunk, embed and store one document."""
    # Read one byte past the cap, so an oversized file is rejected without
    # buffering all of it.
    data = await file.read(settings.UPLOAD_MAX_BYTES + 1)
    try:
        document = await get_uploaded_documents().add(workspace_id, file.filename or "document", data)
    except UploadError as exc:
        _raise(exc)

    message = (
        f"'{document['filename']}' was already uploaded"
        if document.get("duplicate")
        else f"Indexed '{document['filename']}' as {document['chunk_count']} passages"
    )
    return {"success": True, "message": message, "data": {"document": document}}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    workspace_id: str = Query(..., pattern=WORKSPACE_ID_PATTERN),
) -> Dict[str, Any]:
    try:
        await get_uploaded_documents().remove(workspace_id, doc_id)
    except UploadError as exc:
        _raise(exc)
    return {"success": True, "message": "Document deleted", "data": {"doc_id": doc_id}}
