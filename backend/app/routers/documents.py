import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from app.auth_utils import require_permission
from modules.documents import ask, delete_document, index_document

router = APIRouter()
log = logging.getLogger("finpilot.documents")

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


class AskRequest(BaseModel):
    question: str


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), user=Depends(require_permission("documents:read"))):
    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (maximum 10 MB).")
    try:
        # indexing is CPU-heavy: run it off the event loop so other requests are not blocked
        return await run_in_threadpool(index_document, file.filename or "", content)
    except ValueError as e:  # not a PDF, empty file, no extractable text
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{filename:path}")
async def remove_document(filename: str, user=Depends(require_permission("documents:read"))):
    try:
        return await run_in_threadpool(delete_document, filename)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



@router.post("/ask")
def ask_question(payload: AskRequest, user=Depends(require_permission("documents:read"))):
    try:
        return ask(payload.question)
    except RuntimeError as e:  # e.g. GEMINI_API_KEY / GEMINI_MODEL not configured
        raise HTTPException(status_code=503, detail=str(e))
    except Exception:
        log.exception("Document Q&A failed")
        raise HTTPException(status_code=502, detail="The answer service is unavailable right now. Please try again.")


@router.get("/list")
def list_documents(user=Depends(require_permission("documents:read"))):
    """Documents currently in the index (one row per file)."""
    # TODO(Pallav): expose a public list_documents() in modules/documents and call that instead of this private helper.
    from modules.documents import _get_collection

    collection = _get_collection()
    if collection.count() == 0:
        return {"documents": []}
    files: dict = {}
    for meta in collection.get(include=["metadatas"])["metadatas"]:
        entry = files.setdefault(meta["filename"], {"chunks": 0, "pages": set()})
        entry["chunks"] += 1
        entry["pages"].add(meta["page"])
    return {
        "documents": [
            {"filename": name, "chunks": e["chunks"], "pages": len(e["pages"])}
            for name, e in sorted(files.items())
        ]
    }


@router.get("/eval-summary")
def eval_summary(user=Depends(require_permission("documents:read"))):
    """Score from Pallav's retrieval evaluation (tests/retrieval_eval_results.json)."""
    path = Path(__file__).resolve().parents[2] / "tests" / "retrieval_eval_results.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="No evaluation results found.")
    results = json.loads(path.read_text(encoding="utf-8"))
    passed = sum(1 for r in results if r.get("pass"))
    total = len(results)
    return {
        "passed": passed,
        "total": total,
        "pct": round(passed / total * 100, 1) if total else 0.0,
        "documents_in_eval": len({s for r in results for s in r.get("expected_sources", [])}),
        "measures": "which source file is retrieved for each question, not whether the final answer is correct",
    }
