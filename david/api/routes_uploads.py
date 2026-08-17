"""Upload endpoints (Section 13, 23)."""
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from david.config.settings import get_settings
from david.database.json_store import JSONStore
from david.security.auth import get_current_user
from david.security.workspace import ensure_owner, scope_user_id
from david.utils.helpers import new_id, now_iso

router = APIRouter(prefix="/api/uploads", tags=["uploads"])
store = JSONStore("uploads")

ALLOWED_EXTENSIONS = {
    ".pdf", ".docx", ".txt", ".csv", ".xlsx", ".xls",
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".mp3", ".wav", ".m4a", ".zip",
}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


@router.post("")
async def upload_file(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    settings = get_settings()

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"File type '{ext}' is not allowed")

    upload_id = new_id("upload")
    stored_name = f"{upload_id}{ext}"
    dest_path = settings.UPLOAD_DIR / stored_name

    size = 0
    with open(dest_path, "wb") as out_file:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_FILE_SIZE_BYTES:
                out_file.close()
                dest_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File exceeds 25MB limit")
            out_file.write(chunk)

    record = {
        "id": upload_id,
        "user_id": user["id"],
        "original_name": file.filename,
        "stored_name": stored_name,
        "content_type": file.content_type,
        "size_bytes": size,
        "created_at": now_iso(),
    }
    store.add(record)
    return record


@router.get("")
async def list_uploads(user: dict = Depends(get_current_user)):
    return store.find(lambda u: u.get("user_id") == user["id"])


@router.get("/{stored_name}")
async def download_upload(stored_name: str, user: dict = Depends(get_current_user)):
    settings = get_settings()
    safe_name = Path(stored_name).name
    matches = store.find(lambda u: u.get("stored_name") == safe_name)
    if not matches:
        raise HTTPException(status_code=404, detail="File not found")

    record = matches[0]
    ensure_owner(record, user, resource_name="upload")

    path = settings.UPLOAD_DIR / safe_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=record.get("original_name") or safe_name)


@router.delete("")
async def delete_upload(stored_name: str, user: dict = Depends(get_current_user)):
    settings = get_settings()
    safe_name = Path(stored_name).name
    matches = store.find(lambda u: u.get("stored_name") == safe_name)
    if not matches:
        raise HTTPException(status_code=404, detail="Upload record not found")

    record = matches[0]
    ensure_owner(record, user, resource_name="upload")

    path = settings.UPLOAD_DIR / safe_name
    if path.exists():
        path.unlink()
    store.delete(record["id"])
    return {"deleted": True}
