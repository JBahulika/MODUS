"""Simple uploaded document store for prototype research context."""

from __future__ import annotations

import re
import uuid
from pathlib import Path
from typing import Any

from app.config import get_settings


def _docs_dir() -> Path:
    path = get_settings().data_path / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_upload(filename: str, content: bytes, content_type: str = "") -> dict[str, Any]:
    doc_id = str(uuid.uuid4())
    safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", filename)[:80] or "upload.txt"
    path = _docs_dir() / f"{doc_id}_{safe_name}"
    path.write_bytes(content)
    text = extract_text(path, content_type=content_type, original_name=filename)
    meta = {
        "id": doc_id,
        "filename": filename,
        "path": str(path),
        "chars": len(text),
        "preview": text[:400],
    }
    meta_path = _docs_dir() / f"{doc_id}.meta.txt"
    meta_path.write_text(text[:20000], encoding="utf-8")
    return meta


def get_document_text(doc_id: str) -> str:
    meta_path = _docs_dir() / f"{doc_id}.meta.txt"
    if meta_path.exists():
        return meta_path.read_text(encoding="utf-8")
    return ""


def get_documents_text(doc_ids: list[str]) -> str:
    chunks: list[str] = []
    for doc_id in doc_ids:
        text = get_document_text(doc_id).strip()
        if text:
            chunks.append(f"[Document {doc_id[:8]}]\n{text[:6000]}")
    return "\n\n".join(chunks)


def extract_text(path: Path, content_type: str = "", original_name: str = "") -> str:
    name = (original_name or path.name).lower()
    if name.endswith(".txt") or name.endswith(".md") or "text/" in content_type:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return ""
    if name.endswith(".pdf") or "pdf" in content_type:
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            parts = []
            for page in reader.pages[:20]:
                parts.append(page.extract_text() or "")
            return "\n".join(parts)
        except Exception:
            return ""
    if name.endswith(".docx"):
        try:
            import zipfile
            from xml.etree import ElementTree

            with zipfile.ZipFile(path) as zf:
                xml = zf.read("word/document.xml")
            root = ElementTree.fromstring(xml)
            texts = [
                node.text
                for node in root.iter()
                if node.text and node.tag.endswith("}t")
            ]
            return " ".join(texts)
        except Exception:
            return ""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
