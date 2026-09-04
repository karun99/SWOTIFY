"""Scoring engine: turns assessment responses into a digital profile score,
impact suggestions, and a beginner-level SWOT analysis.

Digital Profile Score  = weighted average of the 5 category scores.
Category Score         = mean of the option points selected in that category.
"""

from questions import CATEGORIES, QUESTIONS, QUESTIONS_BY_ID

VERDICT_BANDS = [
    (85, "Outstanding", "You have a strong, well-rounded digital presence. Focus on scale and consistency."),
    (65, "Good", "Solid digital presence with clear room to grow. Prioritise your weakest category."),
    (45, "Fair", "Digital foundations exist but important gaps are holding back growth."),
    (25, "Weak", "Significant gaps. Focus on the fundamentals before chasing scale."),
    (0, "Critical", "Your digital presence is at risk. Start with the quick wins below."),
]

CATEGORY_METRICS = {
    "website": ("trust and conversion", "bounce rate"),
    "social": ("audience reach", "engagement"),
    "seo": ("organic traffic", "search visibility"),
    "content": ("leads and engagement", "content output"),
    "brand": ("customer loyalty", "brand recall"),
}

CATEGORY_ADVICE = {
    "website": "Your website is your digital storefront — improving it lifts trust and conversion.",
    "social": "Active social channels put you where your customers already spend time.",
    "seo": "Search visibility means being found the moment someone needs you.",
    "content": "Consistent content compounds — every post becomes future traffic.",
    "brand": "A clear, consistent brand makes every other channel work harder.",
}


def score_responses(responses: dict) -> dict:
    """responses: {question_id: selected_option_label}. Returns category
    scores, overall score and per-question detail."""
    category_points = {c["key"]: [] for c in CATEGORIES}
    detail = []
    unknown = []

    for q in QUESTIONS:
        qid = q["id"]
        chosen = responses.get(qid)
        option = None
        if chosen is not None:
            option = next((o for o in q["options"] if o["label"] == chosen), None)
            if option is None and isinstance(chosen, (int, float)):
                option = next((o for o in q["options"] if o["points"] == chosen), None)
        if option is None:
            unknown.append(qid)
            continue
        category_points[q["category"]].append(option["points"])
        detail.append(
            {
                "id": qid,
                "category": q["category"],
                "question": q["text"],
                "answer": option["label"],
                "points": option["points"],
                "note": option["note"],
            }
        )

    category_scores = {}
    for c in CATEGORIES:
        pts = category_points[c["key"]]
        category_scores[c["key"]] = round(sum(pts) / len(pts), 1) if pts else 0

    weighted = sum(category_scores[c["key"]] * c["weight"] for c in CATEGORIES)
    overall = round(weighted, 1)

    for c in CATEGORIES:
        pts = category_points[c["key"]]
        c["answered"] = len(pts)

    return {
        "overall": overall,
        "category_scores": category_scores,
        "detail": detail,
        "unanswered": unknown,
        "answered_count": len(detail),
    }


def verdict_for(score: float) -> dict:
    for band, label, desc in VERDICT_BANDS:
        if score >= band:
            return {"label": label, "description": desc}
    return {"label": VERDICT_BANDS[-1][1], "description": VERDICT_BANDS[-1][2]}


def _band_score(score: float) -> str:
    if score >= 85:
        return "strong"
    if score >= 65:
        return "healthy"
    if score >= 45:
        return "developing"
    return "at-risk"


def generate_impact(category_scores: dict) -> list[dict]:
    """One impact suggestion per category with an estimated lift."""
    impact = []
    for c in CATEGORIES:
        key = c["key"]
        s = category_scores.get(key, 0)
        metric, counter = CATEGORY_METRICS[key]
        if s >= 85:
            tier = "maintain"
            lift = "consolidate your advantage and protect this strength"
            detail = f"{c['label']} is a proven strength. Invest to keep it sharp."
        elif s >= 65:
            tier = "optimise"
            lift = f"raising {c['label'].lower()} toward 85 could add ~15-20% more {metric}"
            detail = CATEGORY_ADVICE[key]
        elif s >= 45:
            tier = "priority"
            lift = f"moving {c['label'].lower()} from {int(s)} to 70 could lift {metric} by up to ~30%"
            detail = CATEGORY_ADVICE[key]
        else:
            tier = "critical"
            lift = f"this is your biggest opportunity — taking {c['label'].lower()} from {int(s)} to 60 could more than double {metric}"
            detail = CATEGORY_ADVICE[key]
        impact.append(
            {
                "category": key,
                "category_label": c["label"],
                "tier": tier,
                "lift": lift,
                "detail": detail,
                "current": int(s),
            }
        )
    impact.sort(key=lambda x: x["current"])
    return impact


def _threats_from_responses(responses: dict, category_scores: dict) -> list[str]:
    threats = []
    ans = responses

    def picked(qid, *labels):
        return any(ans.get(qid) == lab for lab in labels)

    if picked("e4", "No / not sure"):
        threats.append("Non-HTTPS site: browsers warn visitors and Google suppresses the site in results.")
    if picked("w1", "No website yet"):
        threats.append("No website: you are invisible to search and losing every online enquiry.")
    if picked("s1", "None"):
        threats.append("No social presence: competitors capture customers who search for you first.")
    if picked("e2", "No"):
        threats.append("No Google Business Profile: local customers cannot find you on Maps.")
    if picked("b4", "No"):
        threats.append("No privacy policy/terms: risks trust, advertising approval and legal compliance.")
    if category_scores.get("website", 0) >= 80 and category_scores.get("social", 0) < 40:
        threats.append("Heavy website reliance with weak social: any channel change hits you hard.")
    return threats


def _opportunities_from_impact(impact: list[dict], n: int = 3) -> list[str]:
    return [f"{i['category_label']}: {i['lift']}." for i in impact[:n]]


def generate_swot(category_scores: dict, responses: dict, impact: list[dict], agent_findings: list[dict] | None = None) -> dict:
    strengths = []
    weaknesses = []
    opportunities = _opportunities_from_impact(impact)
    threats = _threats_from_responses(responses, category_scores)

    for c in CATEGORIES:
        key, s = c["key"], category_scores.get(c["key"], 0)
        if s >= 65:
            strengths.append(f"{c['label']} ({int(s)}/100): a solid asset to build on.")
        elif s <= 45:
            weaknesses.append(f"{c['label']} ({int(s)}/100): the weakest link in your profile.")

    if agent_findings:
        for f in agent_findings:
            ftype = f.get("type", "neutral")
            entry = f"{f.get('title', '')} — {f.get('detail', '')}"
            if ftype == "positive":
                strengths.append(entry)
            elif ftype == "negative":
                weaknesses.append(entry)
            elif ftype == "opportunity":
                opportunities.append(entry)
            else:
                threats.append(entry)

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats,
    }


def build_report(responses: dict, agent_findings: list[dict] | None = None) -> dict:
    scored = score_responses(responses)
    impact = generate_impact(scored["category_scores"])
    swot = generate_swot(scored["category_scores"], responses, impact, agent_findings)
    return {
        "score": scored["overall"],
        "category_scores": scored["category_scores"],
        "verdict": verdict_for(scored["overall"]),
        "impact": impact,
        "swot": swot,
        "detail": scored["detail"],
        "answered_count": scored["answered_count"],
        "unanswered": scored["unanswered"],
        "categories": CATEGORIES,
    }
