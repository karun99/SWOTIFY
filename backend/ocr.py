"""Baidu OCR — unlimited document parsing + general OCR for Swotify.

Adapted from the Collabuild OCR module. Works on in-memory bytes so
uploaded documents (PDF, PPTX, DOCX, images) can be parsed directly.

Free tiers (verified 2026):
  • Unlimited-OCR (document parsing): 200 pages/personal, 1000 pages/enterprise
  • Accurate OCR (images): 1000 calls/month/personal

Auth: OAuth2 client_credentials → access_token.
Set BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY env vars to enable.
Without keys, all methods raise OCRNotConfigured — the app falls back to
client-side extraction (pdf.js / pptx.js) and text uploads.
"""

import base64
import logging
import os
import time
import threading

import requests

log = logging.getLogger("swotify.ocr")

MAX_FILE_SIZE = 100 * 1024 * 1024  # Baidu 100 MB limit

MIME_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".txt": "text/plain; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".webp": "image/webp",
}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".webp"}
DOCUMENT_EXTS = {
    ".pdf", ".doc", ".docx", ".ppt", ".pptx",
    ".xls", ".xlsx", ".txt", ".md",
}

BAIDU_ERRORS = {
    110: "Access token invalid or expired",
    111: "Invalid API key or secret",
    112: "Request rate limit exceeded",
    216: "File too large (max 100MB)",
    217: "Unsupported file format",
    401: "Insufficient quota",
    403: "Permission denied",
    502: "Service temporarily unavailable",
    503: "Task processing failed",
}


class OCRNotConfigured(RuntimeError):
    """Raised when Baidu keys are missing."""


class BaiduOCR:
    TOKEN_URL = "https://aip.baidubce.com/oauth/2.0/token"
    GENERAL_ACCURATE_URL = "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic"
    UNLIMITED_SUBMIT_URL = "https://aip.baidubce.com/rest/2.0/brain/online/v2/unlimited-ocr-parser/task"
    UNLIMITED_QUERY_URL = "https://aip.baidubce.com/rest/2.0/brain/online/v2/unlimited-ocr-parser/task/query"

    def __init__(self, api_key: str = "", secret_key: str = "",
                 timeout: int = 120, poll_interval: int = 5, max_polls: int = 60):
        self.api_key = api_key or os.getenv("BAIDU_OCR_API_KEY", "")
        self.secret_key = secret_key or os.getenv("BAIDU_OCR_SECRET_KEY", "")
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.max_polls = max_polls
        self._token = ""
        self._token_expires = 0.0
        self._token_lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.secret_key)

    def status(self) -> dict:
        return {
            "configured": self.configured,
            "mode": "unlimited-document-parser" if self.configured else "disabled (client-side extraction)",
            "limits": {
                "documents": "200 pages/personal, 1000 pages/enterprise",
                "images": "1000 calls/month/personal",
            },
        }

    # ── Token ─────────────────────────────────────────────────
    def _get_token(self) -> str:
        with self._token_lock:
            now = time.time()
            if self._token and now < self._token_expires - 60:
                return self._token
            if not self.configured:
                raise OCRNotConfigured(
                    "Baidu OCR not configured. Set BAIDU_OCR_API_KEY / BAIDU_OCR_SECRET_KEY."
                )
            r = requests.get(self.TOKEN_URL, params={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.secret_key,
            }, timeout=30)
            r.raise_for_status()
            data = r.json()
            if "access_token" not in data:
                raise RuntimeError(f"Baidu token request failed: {data}")
            self._token = data["access_token"]
            self._token_expires = now + data.get("expires_in", 2592000)
            return self._token

    def _auth_url(self, base: str) -> str:
        return f"{base}?access_token={self._get_token()}"

    # ── General OCR for images (sync) ────────────────────────
    def ocr_image(self, image_data: bytes) -> list[str]:
        if not image_data:
            return []
        b64 = base64.b64encode(image_data).decode()
        r = requests.post(
            self._auth_url(self.GENERAL_ACCURATE_URL),
            data={"image": b64},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        if "error_code" in data and data["error_code"] != 0:
            raise RuntimeError(f"Baidu OCR error {data['error_code']}: {data.get('error_msg', '')}")
        return [w.get("words", "") for w in data.get("words_result", [])]

    # ── Unlimited-OCR document parsing (async) ───────────────
    def parse_document_bytes(self, data: bytes, filename: str) -> str:
        """Parse PDF/DOCX/PPTX/image bytes → Markdown text via Unlimited-OCR."""
        if not filename:
            raise ValueError("filename required")
        ext = os.path.splitext(filename)[1].lower()
        if ext not in MIME_TYPES:
            raise ValueError(f"Unsupported file type: {ext or 'unknown'}")
        if len(data) > MAX_FILE_SIZE:
            raise ValueError("File too large (max 100MB)")

        content_type = MIME_TYPES[ext]
        r = requests.post(
            self._auth_url(self.UNLIMITED_SUBMIT_URL),
            files={"file": (filename, data, content_type)},
            timeout=self.timeout,
        )
        resp = r.json()
        if "error_code" in resp and resp.get("error_code", 0) != 0:
            code = resp.get("error_code")
            readable = BAIDU_ERRORS.get(code, "")
            raise RuntimeError(f"Baidu submit error {code}: {resp.get('error_msg', '')} ({readable})")
        task_id = resp.get("result", {}).get("task_id", "")
        if not task_id:
            raise RuntimeError(f"Baidu submit: no task_id in {resp}")
        log.info("[ocr] submitted %s → task_id=%s", filename, task_id)
        return self._poll_task(task_id)

    def _poll_task(self, task_id: str) -> str:
        for _ in range(self.max_polls):
            time.sleep(self.poll_interval)
            r = requests.post(
                self._auth_url(self.UNLIMITED_QUERY_URL),
                data={"task_id": task_id},
                timeout=self.timeout,
            )
            r.raise_for_status()
            data = r.json()
            result = data.get("result", {}) or {}
            status = result.get("status", "")
            if status in ("success", "done"):
                md_url = result.get("markdown_url", "") or result.get("parse_result_url", "")
                if md_url:
                    md = requests.get(md_url, timeout=self.timeout)
                    md.raise_for_status()
                    return md.text
                return ""
            if status in ("error", "failed"):
                raise RuntimeError(f"Baidu parsing failed: {data.get('error_msg', status)}")
        raise RuntimeError("Baidu parsing timed out")


def classify_file(filename: str) -> str:
    """Return 'image' | 'document' | 'other' based on extension."""
    ext = os.path.splitext(filename)[1].lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in DOCUMENT_EXTS:
        return "document"
    return "other"


def magic_matches(filename: str, data: bytes) -> bool:
    """Verify the leading bytes match the claimed extension.

    Uploads are never served back as executable content, but this prevents
    disguised payloads (e.g. HTML files renamed to .pdf) from being stored
    as an entity's "documents" for later phishing/misinformation.
    """
    ext = os.path.splitext(filename)[1].lower()
    head = data[:8]
    if ext in (".jpg", ".jpeg"):
        return head[:3] == b"\xff\xd8\xff"
    if ext == ".png":
        return head[:8] == b"\x89PNG\r\n\x1a\n"
    if ext == ".gif":
        return head[:6] in (b"GIF87a", b"GIF89a")
    if ext == ".bmp":
        return head[:2] == b"BM"
    if ext == ".webp":
        return head[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if ext == ".pdf":
        return head[:5] == b"%PDF-"
    if ext in (".docx", ".pptx", ".xlsx"):
        return head[:4] == b"PK\x03\x04"
    if ext in (".doc", ".ppt", ".xls"):
        return head[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    if ext in (".txt", ".md"):
        return True
    return True


def extract_with_ocr(ocr: BaiduOCR, data: bytes, filename: str) -> tuple[str, str]:
    """Best-effort OCR extraction. Returns (text, source).

    source is 'baidu-ocr-image' or 'baidu-unlimited'. Raises OCRNotConfigured
    if keys missing, RuntimeError on API failure.
    """
    kind = classify_file(filename)
    if kind == "image":
        return "\n".join(ocr.ocr_image(data)), "baidu-ocr-image"
    return ocr.parse_document_bytes(data, filename), "baidu-unlimited"
