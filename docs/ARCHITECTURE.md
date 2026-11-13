# Architecture

Swotify turns a 20-question digital-presence assessment into a weighted score,
an impact ranking and a beginner-friendly SWOT report. A FastAPI backend owns
scoring, storage, visit tracking and an optional AI audit; a Vite frontend is
the questionnaire and report UI.

## Components

| Path | Responsibility |
|---|---|
| `backend/main.py` | FastAPI app, routes, visit tracking, static frontend mount |
| `backend/scoring.py` | Weighted scoring, verdict bands, impact ranking, SWOT generation |
| `backend/questions.py` | Five categories, twenty questions, option points and notes |
| `backend/database.py` | SQLite persistence for entities, reports and documents |
| `backend/agent.py` | Digital audit agent (site + search + OCR findings) |
| `backend/ocr.py` | OCR provider abstraction and file classification |
| `backend/security.py` | Rate limiting, admin token checks, client IP handling |
| `frontend/` | Vite SPA: questionnaire, report, tracker dashboard |
| `public/tracker.js` | Embeddable visit tracker |

## Scoring

```
responses {question_id: option_label or points}
  → per-category mean of selected option points
  → weighted sum (website .25, social .20, seo .25, content .15, brand .15)
  → overall 0-100 + verdict band
  → impact list sorted by weakest category
  → SWOT: category strengths/weaknesses + rule-based threats + agent findings
```

Answers that do not match a known option are reported in `unanswered` and are
not scored, so a partial questionnaire still produces a report.

## Trust boundaries

- The admin token is generated or supplied by environment and checked on every
  admin route; it is never embedded in the frontend bundle.
- The rate limiter keys on the client IP and applies to the public assessment
  and tracker endpoints.
- OCR and AI providers are optional: when their credentials are absent the
  report is produced from the deterministic engine alone.
- Uploaded documents are stored with their MIME type and size, and only a
  500-character preview is returned in list responses.

## Verification

```bash
python -m unittest discover -s tests -v
cd frontend && npm ci && npm run build
```

The suite checks perfect and worst-case scores, unanswered handling, numeric
answers, category weights, verdict boundaries, impact tiers and the merged
SWOT report. CI runs the units and the frontend build on every push and pull
request.
