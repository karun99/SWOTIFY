"""Swotify — digital profile intelligence by GuidingKey Technologies.

FastAPI backend: visit tracking (Google-Search-Console style), digital profile
assessment, AI reach-agent audit (web + search + OCR) and SWOT reporting.

Run:
    cd backend
    uvicorn main:app --reload --port 8000
"""

import json
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

import database as db
import questions as qn
from agent import DigitalAuditAgent
from ocr import BaiduOCR, OCRNotConfigured, classify_file, extract_with_ocr, magic_matches
from security import RateLimiter, client_ip, get_admin_token, valid_token
from scoring import build_report

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("swotify")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    log.info("Swotify ready. OCR: %s", ocr.status()["mode"])
    log.info("Admin token: %s", get_admin_token())
    yield


ocr = BaiduOCR()
agent = DigitalAuditAgent(ocr=ocr)

app = FastAPI(title="Swotify", version="1.1.0",
              description="Digital profile intelligence by GuidingKey Technologies",
              lifespan=lifespan)

_PUBLIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "public")
if os.path.isdir(_PUBLIC_DIR):
    app.mount("/tracker", StaticFiles(directory=_PUBLIC_DIR), name="tracker")

_DIST_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
_SERVE_FRONTEND = os.path.isdir(os.path.join(_DIST_DIR, "assets"))

# ---------------------------------------------------------------------------
# Security middleware: admin auth + per-endpoint CORS + security headers
# ---------------------------------------------------------------------------
_PUBLIC_API_PATHS = {"/api/health", "/api/login", "/api/track"}

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; font-src 'self' data:; connect-src 'self'; "
        "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
    ),
}


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    path = request.url.path

    # CORS preflight for the public tracking beacon (third-party embeds).
    if path == "/api/track" and request.method == "OPTIONS":
        return JSONResponse(
            {},
            status_code=200,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Max-Age": "600",
            },
        )

    # Bearer-token auth for everything under /api except the public endpoints.
    if path.startswith("/api/") and path not in _PUBLIC_API_PATHS:
        auth = request.headers.get("authorization", "")
        token = auth[7:].strip() if auth[:7].lower() == "bearer " else ""
        if not valid_token(token):
            return JSONResponse({"detail": "unauthorized"}, status_code=401)

    response = await call_next(request)

    if path == "/api/track":
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    else:
        for key, value in _SECURITY_HEADERS.items():
            response.headers[key] = value

    return response


# Rate limiters (in-memory)
_track_global = RateLimiter(600, 60.0)
_track_per_ip = RateLimiter(120, 60.0)
_track_per_tid = RateLimiter(180, 60.0)
_audit_global = RateLimiter(3, 60.0)
_login_global = RateLimiter(10, 60.0)


# ---------------------------------------------------------------------------
# Public endpoints
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {"status": "ok", "app": "Swotify", "version": "1.1.0"}


@app.post("/api/login")
async def login(payload: dict):
    if not _login_global.allow("login"):
        raise HTTPException(429, "too many login attempts")
    token = (payload.get("token") or "").strip()
    if not token or not valid_token(token):
        raise HTTPException(401, "invalid token")
    return {"ok": True, "app": "Swotify"}


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "Swotify",
        "by": "GuidingKey Technologies",
        "ocr": ocr.status(),
    }


@app.post("/api/entities")
def create_entity(payload: dict):
    if not isinstance(payload, dict):
        raise HTTPException(400, "invalid payload")
    name = (payload.get("name") or "").strip()
    website = (payload.get("website") or "").strip()
    if not name:
        raise HTTPException(400, "name is required")
    if len(name) > 200:
        raise HTTPException(400, "name is too long (max 200 chars)")
    if len(website) > 500:
        raise HTTPException(400, "website is too long (max 500 chars)")
    entity = db.create_entity(name, website)
    return entity


@app.get("/api/entities")
def entities():
    out = []
    for e in db.list_entities():
        last = db.latest_assessment(e["id"])
        live = db.live_visits(e["id"], minutes=10)
        out.append({
            **e,
            "total_visits": _count_all(e["id"]),
            "live_now": len(live),
            "has_report": last is not None,
            "last_score": _parse_json(last, "scores").get("overall") if last else None,
        })
    return out


def _parse_json(row: dict | None, field: str) -> dict:
    if not row:
        return {}
    try:
        val = json.loads(row.get(field) or "{}")
        return val if isinstance(val, dict) else {}
    except (ValueError, TypeError):
        return {}


def _count_all(entity_id: int) -> int:
    import datetime as dt
    from datetime import timezone
    end = dt.datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    start = "2000-01-01T00:00:00Z"
    return len(db.visits_in_range(entity_id, start, end))


@app.get("/api/entities/{entity_id}")
def get_entity(entity_id: int):
    e = db.get_entity(entity_id)
    if not e:
        raise HTTPException(404, "entity not found")
    return e


# ---------------------------------------------------------------------------
# Visit tracking (the embeddable beacon endpoint)
# ---------------------------------------------------------------------------
@app.post("/api/track")
async def track(request: Request):
    if not _track_global.allow("global"):
        raise HTTPException(429, "too many requests")
    if not _track_per_ip.allow(client_ip(request)):
        raise HTTPException(429, "too many requests")
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(400, "invalid payload")

    tid = str(payload.get("tid") or payload.get("tracking_id") or "")[:64]
    if not tid:
        raise HTTPException(400, "tracking_id (tid) required")
    if not _track_per_tid.allow(tid):
        raise HTTPException(429, "too many requests")

    entity = db.get_entity_by_tracking_id(tid)

    from user_agents_parse import parse_device, parse_browser
    ua = _text(payload.get("ua"), "")
    visit = {
        "tracking_id": tid,
        "entity_id": entity["id"] if entity else None,
        "path": _text(payload.get("path"), "/")[:2000],
        "title": _text(payload.get("title"))[:300],
        "referrer": _text(payload.get("ref"))[:500],
        "user_agent": ua[:500],
        "device": parse_device(ua),
        "browser": parse_browser(ua),
        "lang": _text(payload.get("lang"))[:20],
        "width": _to_int(payload.get("sw")),
        "height": _to_int(payload.get("sh")),
        "visitor_id": _text(payload.get("vid"))[:64],
        "ts": _text(payload.get("ts")) or db.now_iso(),
        "duration_s": _to_float(payload.get("d")),
    }
    visit_id = db.record_visit(visit)
    return {"ok": True, "visit_id": visit_id, "entity": entity["id"] if entity else None}


def _text(value, default: str = "") -> str:
    if value is None:
        return default
    return value if isinstance(value, str) else default


def _to_int(value, default: int = 0) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return default


def _to_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError, OverflowError):
        return default


# ---------------------------------------------------------------------------
# Analytics (Google-Search-Console style)
# ---------------------------------------------------------------------------
@app.get("/api/entities/{entity_id}/analytics")
def analytics(entity_id: int, days: int = 30):
    e = db.get_entity(entity_id)
    if not e:
        raise HTTPException(404, "entity not found")

    import datetime as dt
    from datetime import timezone

    days = max(1, min(days, 90))
    end = dt.datetime.now(timezone.utc)
    start = end - dt.timedelta(days=days)
    visits = db.visits_in_range(
        entity_id,
        start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )

    by_day: dict[str, dict] = {}
    for i in range(days):
        d = (start + dt.timedelta(days=i)).strftime("%Y-%m-%d")
        by_day[d] = {"date": d, "views": 0, "visitors": 0, "visitors_seen": set()}

    pages: dict[str, dict] = {}
    referrers: dict[str, int] = {}
    devices: dict[str, int] = {}
    browsers: dict[str, int] = {}
    visitors: set = set()
    durations: list = []
    bounces = 0
    total_duration = 0.0

    for v in visits:
        day = (v["ts"] or "")[:10]
        if day in by_day:
            by_day[day]["views"] += 1
            vid = v["visitor_id"] or v["id"]
            if vid not in by_day[day]["visitors_seen"]:
                by_day[day]["visitors_seen"].add(vid)
                by_day[day]["visitors"] += 1
        key = v["path"] or "/"
        pg = pages.setdefault(key, {"path": key, "views": 0, "durations": []})
        pg["views"] += 1
        pg["durations"].append(v["duration_s"] or 0)
        ref = (v["referrer"] or "").strip() or "(direct)"
        referrers[ref] = referrers.get(ref, 0) + 1
        devices[v["device"] or "desktop"] = devices.get(v["device"] or "desktop", 0) + 1
        browsers[v["browser"] or "unknown"] = browsers.get(v["browser"] or "unknown", 0) + 1
        if v["visitor_id"]:
            visitors.add(v["visitor_id"])
        if v["duration_s"] is not None:
            total_duration += v["duration_s"]
            durations.append(v["duration_s"])
        if (v["duration_s"] or 0) < 5:
            bounces += 1

    for pg in pages.values():
        pg["avg_time_s"] = round(sum(pg["durations"]) / len(pg["durations"]), 1) if pg["durations"] else 0
        pg.pop("durations", None)

    series = []
    for d in by_day.values():
        d.pop("visitors_seen", None)
        series.append(d)

    today_iso = end.strftime("%Y-%m-%d")
    hourly = [0] * 24
    for v in visits:
        if (v["ts"] or "").startswith(today_iso):
            try:
                hourly[int(v["ts"][11:13])] += 1
            except (ValueError, IndexError):
                pass

    live = db.live_visits(entity_id, minutes=10)
    avg_time = round(total_duration / len(durations), 1) if durations else 0
    bounce_rate = round(100 * bounces / len(visits), 1) if visits else 0

    return {
        "entity": e,
        "range_days": days,
        "totals": {
            "views": len(visits),
            "visitors": len(visitors),
            "avg_time_s": avg_time,
            "bounce_rate": bounce_rate,
            "live_now": len(live),
        },
        "timeseries": series,
        "hourly": {"hour": list(range(24)), "views": hourly},
        "top_pages": sorted(pages.values(), key=lambda p: p["views"], reverse=True)[:15],
        "referrers": sorted(referrers.items(), key=lambda x: x[1], reverse=True)[:15],
        "devices": sorted(devices.items(), key=lambda x: x[1], reverse=True),
        "browsers": sorted(browsers.items(), key=lambda x: x[1], reverse=True),
        "live": [
            {"path": v["path"], "device": v["device"], "ts": v["ts"], "referrer": v["referrer"]}
            for v in live[:20]
        ],
    }


@app.get("/api/entities/{entity_id}/analytics/live")
def analytics_live(entity_id: int):
    e = db.get_entity(entity_id)
    if not e:
        raise HTTPException(404, "entity not found")
    live = db.live_visits(entity_id, minutes=10)
    today = db.visits_today(entity_id)
    return {
        "live_now": len(live),
        "views_today": len(today),
        "live": [{"path": v["path"], "device": v["device"], "ts": v["ts"]} for v in live[:20]],
    }


# ---------------------------------------------------------------------------
# Assessment
# ---------------------------------------------------------------------------
@app.get("/api/questions")
def questions():
    return {"categories": qn.CATEGORIES, "questions": qn.QUESTIONS}


@app.post("/api/entities/{entity_id}/assessments")
def submit_assessment(entity_id: int, payload: dict):
    e = db.get_entity(entity_id)
    if not e:
        raise HTTPException(404, "entity not found")
    responses = payload.get("responses") or {}
    if not isinstance(responses, dict) or not responses:
        raise HTTPException(400, "responses object required")
    if len(json.dumps(responses)) > 100_000:
        raise HTTPException(400, "responses too large")

    report = build_report(responses)
    assessment_id = db.save_assessment(entity_id, {
        "responses_json": json.dumps(responses),
        "scores_json": json.dumps({
            "overall": report["score"],
            "category_scores": report["category_scores"],
            "verdict": report["verdict"],
        }),
        "swot_json": json.dumps(report["swot"]),
        "impact_json": json.dumps(report["impact"]),
    })
    return {"assessment_id": assessment_id, **report}


@app.get("/api/entities/{entity_id}/report")
def get_report(entity_id: int):
    e = db.get_entity(entity_id)
    if not e:
        raise HTTPException(404, "entity not found")
    last = db.latest_assessment(entity_id)
    if not last:
        return {"has_report": False, "entity": e}
    scores = _parse_json(last, "scores")
    return {
        "has_report": True,
        "entity": e,
        "assessment_id": last["id"],
        "created_at": last["created_at"],
        "score": scores.get("overall"),
        "category_scores": scores.get("category_scores", {}),
        "verdict": scores.get("verdict", {}),
        "swot": _parse_json(last, "swot"),
        "impact": _parse_json(last, "impact"),
        "agent": _parse_json(last, "agent_json"),
        "categories": qn.CATEGORIES,
    }


# ---------------------------------------------------------------------------
# AI audit agent + documents (Reach + OCR)
# ---------------------------------------------------------------------------
@app.get("/api/entities/{entity_id}/agent/reach")
def reach_status(entity_id: int):
    e = db.get_entity(entity_id)
    if not e:
        raise HTTPException(404, "entity not found")
    return {"entity": e, "reach": agent._reach_channels(), "ocr": ocr.status()}


@app.post("/api/entities/{entity_id}/agent/audit")
def run_audit(entity_id: int):
    if not _audit_global.allow("audit"):
        raise HTTPException(429, "too many audits — wait a minute and retry")
    e = db.get_entity(entity_id)
    if not e:
        raise HTTPException(404, "entity not found")
    docs = db.list_documents(entity_id)
    try:
        result = agent.run(e, docs)
    except Exception as exc:
        log.exception("audit failed for entity %s", entity_id)
        raise HTTPException(502, f"audit failed: {type(exc).__name__}")
    result_dict = result.to_dict()

    last = db.latest_assessment(entity_id)
    if last:
        agent_json = dict(_parse_json(last, "agent_json"))
        agent_json["audits"] = agent_json.get("audits", []) + [result_dict]
        agent_json["last_audit"] = result_dict
        db.save_assessment(entity_id, {
            "responses_json": last["responses"],
            "scores_json": last["scores"],
            "swot_json": last["swot"],
            "impact_json": last["impact"],
            "agent_json": json.dumps(agent_json),
        })
    return result_dict


@app.post("/api/entities/{entity_id}/documents")
async def upload_document(entity_id: int, file: UploadFile = File(...)):
    e = db.get_entity(entity_id)
    if not e:
        raise HTTPException(404, "entity not found")

    filename = file.filename or "upload"
    data = await file.read()
    if not data:
        raise HTTPException(400, "empty file")
    if len(data) > 100 * 1024 * 1024:
        raise HTTPException(400, "file too large (max 100MB)")

    kind = classify_file(filename)
    if kind == "other":
        raise HTTPException(400, "unsupported file type — upload PDF, PPTX, DOCX or an image")
    if not magic_matches(filename, data):
        raise HTTPException(400, "file content does not match its extension")

    text, source = "", "client"
    try:
        text, source = extract_with_ocr(ocr, data, filename)
    except OCRNotConfigured:
        source = "client (OCR not configured)"
    except RuntimeError as exc:
        log.warning("OCR failed for %s: %s", filename, exc)
        source = "client (OCR unavailable)"

    doc_id = db.save_document(entity_id, filename[:255], file.content_type or "", len(data), text, source)
    return db.get_document(doc_id)


@app.get("/api/entities/{entity_id}/documents")
def documents(entity_id: int):
    e = db.get_entity(entity_id)
    if not e:
        raise HTTPException(404, "entity not found")
    docs = db.list_documents(entity_id)
    return [{"id": d["id"], "filename": d["filename"], "mime": d["mime"],
             "size": d["size"], "source": d["source"], "text_preview": d["text"][:500],
             "text_len": len(d["text"]), "created_at": d["created_at"]} for d in docs]


@app.delete("/api/entities/{entity_id}/documents/{doc_id}")
def delete_document(entity_id: int, doc_id: int):
    doc = db.get_document(doc_id)
    if not doc or doc["entity_id"] != entity_id:
        raise HTTPException(404, "document not found")
    db.delete_document(doc_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Built frontend (SPA) — optional, served only if frontend/dist exists
# ---------------------------------------------------------------------------
if _SERVE_FRONTEND:
    app.mount("/assets", StaticFiles(directory=os.path.join(_DIST_DIR, "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str):
        if full_path.startswith(("api/", "tracker/")):
            raise HTTPException(404, "not found")
        index = os.path.join(_DIST_DIR, "index.html")
        if not os.path.isfile(index):
            raise HTTPException(404, "not found")
        return FileResponse(index)
