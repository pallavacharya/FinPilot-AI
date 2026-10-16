from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from app.auth_utils import require_permission
from modules.documents import index_document, ask

router = APIRouter()


class AskRequest(BaseModel):
    question: str


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), user=Depends(require_permission("documents:read"))):
    content = await file.read()
    return index_document(file.filename, content)


@router.post("/ask")
def ask_question(payload: AskRequest, user=Depends(require_permission("documents:read"))):
    return ask(payload.question)
