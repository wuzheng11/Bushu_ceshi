from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..deps import get_current_user, get_owned_conversation_or_404
from ..models import Attachment, User
from ..schemas import AttachmentOut
from ..services.file_service import conversation_directory, resolve_inside, safe_filename


router = APIRouter(tags=["attachment"])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
TEXT_SUFFIXES = {".txt", ".md", ".csv", ".json", ".sql", ".log", ".xml", ".yaml", ".yml"}


def _attachment_dict(attachment: Attachment) -> dict:
    return {
        "attachment_id": attachment.id,
        "conversation_id": attachment.conversation_id,
        "message_id": attachment.message_id,
        "file_name": attachment.file_name,
        "file_path": attachment.file_path,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "parse_status": attachment.parse_status,
        "created_at": attachment.created_at,
    }


@router.post("/api/attachment/upload", response_model=AttachmentOut)
async def upload_attachment(
    conversation_id: int = Form(...),
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    get_owned_conversation_or_404(db, conversation_id, user)
    original_name = safe_filename(file.filename or "upload.bin")
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="附件不能超过20MB")

    directory = conversation_directory(settings.uploads_dir, user.id, conversation_id)
    target = (directory / original_name).resolve()
    if target.parent != directory:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法文件名")
    if target.exists():
        target = (directory / f"{target.stem}_{Path(file.filename or 'file').stem[:8]}{target.suffix}").resolve()
    target.write_bytes(content)

    suffix = target.suffix.lower()
    parse_status = "pending"
    if suffix in TEXT_SUFFIXES:
        try:
            content.decode("utf-8")
            parse_status = "parsed"
        except UnicodeDecodeError:
            content.decode("gb18030", errors="ignore")
            parse_status = "parsed"
    else:
        parse_status = "stored"

    attachment = Attachment(
        conversation_id=conversation_id,
        file_name=original_name,
        file_path=str(target),
        file_type=file.content_type or mimetypes.guess_type(original_name)[0] or "application/octet-stream",
        file_size=len(content),
        parse_status=parse_status,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return _attachment_dict(attachment)


@router.get("/api/attachment/ls", response_model=list[AttachmentOut])
def list_attachments(
    conversation_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    get_owned_conversation_or_404(db, conversation_id, user)
    attachments = db.scalars(
        select(Attachment)
        .where(Attachment.conversation_id == conversation_id)
        .order_by(Attachment.created_at.desc())
    ).all()
    return [_attachment_dict(item) for item in attachments]


@router.post("/api/attachment/delete")
def delete_attachment(
    attachment_id: int = Form(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    attachment = db.get(Attachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="附件不存在")
    get_owned_conversation_or_404(db, attachment.conversation_id, user)
    try:
        target = resolve_inside(settings.uploads_dir, attachment.file_path)
        target.unlink(missing_ok=True)
    except ValueError:
        pass
    db.delete(attachment)
    db.commit()
    return {"status": "deleted", "attachment_id": attachment_id}


@router.get("/api/attachment/get")
def download_attachment(
    attachment_id: int = Query(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> FileResponse:
    attachment = db.get(Attachment, attachment_id)
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="附件不存在")
    get_owned_conversation_or_404(db, attachment.conversation_id, user)
    try:
        path = resolve_inside(settings.uploads_dir, attachment.file_path)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="附件路径非法") from exc
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="附件文件不存在")
    return FileResponse(path, filename=attachment.file_name, media_type=attachment.file_type)
