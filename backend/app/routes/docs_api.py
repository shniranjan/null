"""
Built-in Documentation API.

GET /api/docs               — list available docs
GET /api/docs/{name}        — get doc content as HTML/markdown
"""

import os
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/docs", tags=["docs"])

DOCS_DIR = Path(__file__).resolve().parent.parent.parent.parent / "docs"

# Map of doc files to display names
DOC_INDEX = {
    "quickstart":    {"title": "Quick Start Guide",   "file": "quickstart.md"},
    "architecture":  {"title": "Architecture Overview", "file": "architecture.md"},
    "api-reference": {"title": "API Reference",         "file": "api-reference.md"},
    "contributing":  {"title": "Contributing Guide",    "file": "contributing.md"},
}


@router.get("")
async def list_docs():
    return {
        "docs": [
            {"id": k, "title": v["title"]} for k, v in DOC_INDEX.items()
        ]
    }


@router.get("/{doc_id}")
async def get_doc(doc_id: str):
    if doc_id not in DOC_INDEX:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found")

    file_path = DOCS_DIR / DOC_INDEX[doc_id]["file"]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Document file not found on disk")

    content = file_path.read_text()
    return {
        "id": doc_id,
        "title": DOC_INDEX[doc_id]["title"],
        "content": content,
    }
