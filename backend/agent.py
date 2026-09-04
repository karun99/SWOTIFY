"""DigitalAuditAgent — a reach agent that audits an entity's real digital
presence using internet Reach tools plus uploaded documents/OCR.

Toolkit (Collabuild-inspired "reach"):
  • web_fetch   — fetch + parse a website (title, meta, headings, links, media)
  • search      — web search for the entity (DuckDuckGo HTML, no API key = unlimited)
  • social_check— look for social profile links on the site
  • ocr_file    — Baidu OCR unlimited document parsing (optional)

The agent runs a visible step loop (thought → tool_calls → output) and emits
structured findings that are merged into the SWOT report.
"""

import ipaddress
import json
import logging
import re
import socket
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("swotify.agent")

TIMEOUT = 15
USER_AGENT = "SwotifyAuditBot/1.0 (+https://guidingkey.com)"

MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5

# IP ranges the audit agent must never fetch (SSRF guard): loopback, RFC1918,
# link-local, CGNAT, metadata, multicast, reserved + IPv6 equivalents.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("198.18.0.0/15"),
    ipaddress.ip_network("224.0.0.0/4"),
    ipaddress.ip_network("240.0.0.0/4"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("64:ff9b::/96"),
    ipaddress.ip_network("::ffff:0:0/96"),
    ipaddress.ip_network("::ffff:127.0.0.0/104"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("ff00::/8"),
]


def _is_blocked_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str.split("%")[0])
    except ValueError:
        return False
    if ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return True
    return any(ip in net for net in _BLOCKED_NETWORKS)


def _is_blocked_host(host: str) -> bool:
    host = (host or "").strip().rstrip(".").lower()
    if not host or host == "localhost":
        return True
    try:
        return _is_blocked_ip(ipaddress.ip_address(host).compressed)
    except ValueError:
        pass
    try:
        addrs = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except OSError:
        return True  # unresolvable — refuse rather than probe
    return any(_is_blocked_ip(a) for a in addrs)


def _validate_web_url(url: str) -> None:
    u = urllib.parse.urlparse(url)
    if u.scheme not in ("http", "https"):
        raise ValueError("only http/https URLs are allowed")
    if not u.hostname:
        raise ValueError("URL has no host")
    if u.username or u.password:
        raise ValueError("URL credentials are not allowed")
    if _is_blocked_host(u.hostname):
        raise ValueError(f"host '{u.hostname}' is not allowed")

SOCIAL_DOMAINS = {
    "facebook.com": "Facebook",
    "instagram.com": "Instagram",
    "x.com": "X/Twitter",
    "twitter.com": "X/Twitter",
    "linkedin.com": "LinkedIn",
    "youtube.com": "YouTube",
    "tiktok.com": "TikTok",
    "whatsapp.com": "WhatsApp",
    "pinterest.com": "Pinterest",
    "threads.net": "Threads",
}


class ToolCall:
    def __init__(self, tool: str, args: dict, result: str, success: bool, duration_ms: float, error: str = ""):
        self.tool = tool
        self.args = args
        self.result = result
        self.success = success
        self.duration_ms = round(duration_ms, 1)
        self.error = error

    def to_dict(self) -> dict:
        return {
            "tool": self.tool,
            "args": self.args,
            "result": self.result,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class AgentStep:
    def __init__(self, step_num: int, title: str, thought: str):
        self.step_num = step_num
        self.title = title
        self.thought = thought
        self.tool_calls: list[ToolCall] = []
        self.output = ""

    def to_dict(self) -> dict:
        return {
            "step": self.step_num,
            "title": self.title,
            "thought": self.thought,
            "tool_calls": [t.to_dict() for t in self.tool_calls],
            "output": self.output,
        }


class AuditResult:
    def __init__(self, entity: dict):
        self.entity = entity
        self.steps: list[AgentStep] = []
        self.findings: list[dict] = []
        self.reach_report: dict = {}
        self.summary = ""
        self.total_duration_ms = 0.0
        self.success = True
        self.error = ""

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "steps": [s.to_dict() for s in self.steps],
            "findings": self.findings,
            "reach_report": self.reach_report,
            "summary": self.summary,
            "total_duration_ms": round(self.total_duration_ms, 1),
            "success": self.success,
            "error": self.error,
        }


def _norm_url(url: str) -> str:
    if not url:
        return ""
    if not re.match(r"^https?://", url):
        url = "https://" + url
    return url.rstrip("/")


def _clean_text(t: str, limit: int = 400) -> str:
    t = re.sub(r"\s+", " ", t or "").strip()
    return t[:limit] + ("…" if len(t) > limit else "")


class DigitalAuditAgent:
    def __init__(self, ocr=None, timeout: int = TIMEOUT):
        self.ocr = ocr
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    # ── Tools ────────────────────────────────────────────────
    def _reach_channels(self) -> dict:
        checks = {}
        try:
            r = self.session.get("https://www.google.com", timeout=8)
            checks["web"] = "ok" if r.status_code == 200 else f"http-{r.status_code}"
        except Exception as e:
            checks["web"] = f"error: {type(e).__name__}"
        try:
            r = self.session.get(
                "https://html.duckduckgo.com/html/?q=swotify+test",
                timeout=10,
            )
            checks["search"] = "ok" if r.status_code == 200 else f"http-{r.status_code}"
        except Exception as e:
            checks["search"] = f"error: {type(e).__name__}"
        if self.ocr and self.ocr.configured:
            checks["ocr"] = "ok (baidu unlimited)"
        else:
            checks["ocr"] = "disabled (client-side pdf.js / pptx.js used instead)"
        return checks

    def _http_get_safe(self, url: str):
        """GET with SSRF guard, manual redirect checks and a size cap."""
        _validate_web_url(url)
        current = url
        for _ in range(MAX_REDIRECTS + 1):
            _validate_web_url(current)
            resp = self.session.get(
                current, timeout=self.timeout, allow_redirects=False, stream=True
            )
            if resp.status_code in (301, 302, 303, 307, 308):
                loc = resp.headers.get("location")
                status, content_type = resp.status_code, resp.headers.get("content-type", "")
                resp.close()
                if not loc:
                    return current, status, content_type, b""
                current = urllib.parse.urljoin(current, loc)
                continue
            status, content_type = resp.status_code, resp.headers.get("content-type", "")
            body = b""
            for chunk in resp.iter_content(65536):
                body += chunk
                if len(body) > MAX_PAGE_BYTES:
                    resp.close()
                    raise ValueError("response too large (max 5MB)")
            resp.close()
            return current, status, content_type, body
        raise ValueError("too many redirects")

    def _web_fetch(self, url: str) -> dict:
        """Fetch and parse a page. Returns extracted site data."""
        out = {
            "url": url, "status": None, "final_url": url, "title": "",
            "meta_description": "", "https": False, "mobile_viewport": False,
            "h1": [], "headings": [], "links": [], "images": 0,
            "text_len": 0, "snapshot": "",
        }
        try:
            final_url, status, content_type, body = self._http_get_safe(url)
            out["status"] = status
            out["final_url"] = final_url
            out["https"] = final_url.startswith("https://")
            if status != 200 or not content_type.startswith("text/html"):
                return out
            soup = BeautifulSoup(body, "html.parser")
            out["title"] = soup.title.get_text(strip=True) if soup.title else ""
            meta = soup.find("meta", attrs={"name": re.compile("description", re.I)})
            out["meta_description"] = (meta.get("content", "") if meta else "").strip()
            vp = soup.find("meta", attrs={"name": "viewport"})
            out["mobile_viewport"] = bool(vp and vp.get("content"))
            out["h1"] = [h.get_text(strip=True) for h in soup.find_all("h1")][:3]
            out["headings"] = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2"])][:8]
            out["links"] = [a.get("href") for a in soup.find_all("a", href=True)][:40]
            out["images"] = len(soup.find_all("img"))
            out["text_len"] = len(soup.get_text(" ", strip=True))
            out["snapshot"] = _clean_text(soup.get_text(" ", strip=True), 500)
        except Exception as e:
            log.warning("web_fetch failed for %s: %s", url, e)
            out["error"] = type(e).__name__
        return out

    def _search(self, query: str, max_results: int = 5) -> list[dict]:
        results = []
        try:
            r = self.session.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                timeout=self.timeout,
            )
            if r.status_code != 200:
                return results
            soup = BeautifulSoup(r.text, "html.parser")
            for res in soup.select(".result")[:max_results]:
                a = res.select_one(".result__a")
                if not a:
                    continue
                snip = res.select_one(".result__snippet")
                results.append({
                    "title": a.get_text(strip=True),
                    "url": a.get("href", ""),
                    "snippet": snip.get_text(strip=True) if snip else "",
                })
        except Exception:
            pass
        return results

    def _social_found(self, links: list[str], title: str) -> list[str]:
        found = []
        for link in links:
            for domain, name in SOCIAL_DOMAINS.items():
                if domain in link and name not in found:
                    found.append(name)
        # heuristic: brand mention on social-looking anchors (text check)
        return found

    # ── Analysis rules (beginner-level, transparent) ─────────
    def _analyze_site(self, site: dict, entity_name: str, entity_website: str) -> list[dict]:
        findings = []

        if not site.get("status"):
            findings.append({"category": "website", "type": "negative", "title": "Website unreachable",
                             "detail": f"Could not load {entity_website} during the audit. Visitors may be hitting errors too."})
            return findings

        if site["status"] != 200:
            findings.append({"category": "website", "type": "negative", "title": f"Website returned HTTP {site['status']}",
                             "detail": "A non-200 response means search engines and visitors can be blocked."})
            return findings

        if site["https"]:
            findings.append({"category": "website", "type": "positive", "title": "Secure (HTTPS) connection confirmed",
                             "detail": f"{site['final_url']} loads over HTTPS."})
        else:
            findings.append({"category": "website", "type": "negative", "title": "Site is NOT served over HTTPS",
                             "detail": "Browsers warn visitors and Google deprioritises non-secure sites."})

        if site["title"]:
            if len(site["title"]) < 10 or len(site["title"]) > 70:
                findings.append({"category": "seo", "type": "negative", "title": "Weak page title length",
                                 "detail": f"Title '{_clean_text(site['title'], 60)}' is {len(site['title'])} chars — search engines prefer 30-60."})
            else:
                findings.append({"category": "seo", "type": "positive", "title": "Well-sized page title",
                                 "detail": _clean_text(site["title"], 80)})
        else:
            findings.append({"category": "seo", "type": "negative", "title": "No page title found",
                             "detail": "Every page needs a unique <title> for search results."})

        if site["meta_description"]:
            findings.append({"category": "seo", "type": "positive", "title": "Meta description present",
                             "detail": _clean_text(site["meta_description"], 120)})
        else:
            findings.append({"category": "seo", "type": "negative", "title": "Missing meta description",
                             "detail": "Google shows the snippet from your meta description — write one for each page."})

        if site["mobile_viewport"]:
            findings.append({"category": "website", "type": "positive", "title": "Mobile-responsive design detected",
                             "detail": "A viewport meta tag was found — the site adapts to phones."})
        else:
            findings.append({"category": "website", "type": "negative", "title": "No mobile viewport tag",
                             "detail": "The site likely renders poorly on phones, hurting mobile ranking."})

        social = self._social_found(site["links"], site["title"])
        if social:
            findings.append({"category": "social", "type": "positive", "title": "Social profiles linked",
                             "detail": "Found: " + ", ".join(social) + "."})
        else:
            findings.append({"category": "social", "type": "negative", "title": "No social links found on site",
                             "detail": "Add links to your social profiles so visitors can follow you."})

        if entity_name.lower() and entity_name.lower() not in site["title"].lower():
            findings.append({"category": "brand", "type": "neutral", "title": "Brand not in page title",
                             "detail": "Include your business name in the title for brand recognition."})

        if site["images"] == 0:
            findings.append({"category": "content", "type": "negative", "title": "No images detected",
                             "detail": "Visual content improves engagement and time on page."})
        elif site["images"] >= 5:
            findings.append({"category": "content", "type": "positive", "title": f"{site['images']} images on homepage",
                             "detail": "Rich visuals keep visitors engaged."})

        if site["text_len"] < 300:
            findings.append({"category": "content", "type": "negative", "title": "Very little text content",
                             "detail": f"Only ~{site['text_len']} characters of text — thin content ranks poorly."})

        return findings

    def _analyze_search(self, results: list[dict], entity_name: str, entity_website: str) -> list[dict]:
        findings = []
        if not results:
            findings.append({"category": "seo", "type": "negative", "title": "No search results found for your brand",
                             "detail": f"Searching '{entity_name}' returned nothing. You are invisible to searchers."})
            return findings
        domain = urllib.parse.urlparse(_norm_url(entity_website)).netloc if entity_website else ""
        owned = [r for r in results if domain and domain in r.get("url", "")]
        if owned:
            findings.append({"category": "seo", "type": "positive", "title": f"{len(owned)} of your own pages appear in search",
                             "detail": "Your site is indexed by search engines."})
        else:
            findings.append({"category": "seo", "type": "negative", "title": "Search shows mentions, but not your site",
                             "detail": "Set up Google Search Console and submit your sitemap to get indexed."})
        other_domains = [r for r in results if not (domain and domain in r.get("url", ""))]
        if other_domains:
            names = {urllib.parse.urlparse(r["url"]).netloc for r in other_domains}
            findings.append({"category": "brand", "type": "neutral", "title": "Others talk about you in search",
                             "detail": "You appear via " + ", ".join(sorted(names)[:4]) + " — ensure the information is accurate."})
        return findings

    def _analyze_documents(self, documents: list[dict]) -> list[dict]:
        findings = []
        if not documents:
            return findings
        texts = [(d["filename"], d.get("text") or "") for d in documents]
        themes = {
            "website": ["website", "web", "online", "site"],
            "social": ["social", "instagram", "facebook", "linkedin", "twitter", "tiktok"],
            "seo": ["google", "seo", "search", "rank", "keyword"],
            "content": ["blog", "content", "post", "article", "video"],
            "brand": ["brand", "logo", "identity", "value", "mission", "customer"],
        }
        for fname, text in texts:
            low = text.lower()
            mentioned = [label for label, kws in themes.items() if any(k in low for k in kws)]
            found_categories = mentioned[:3]
            if text and len(text) < 50:
                findings.append({"category": "content", "type": "negative",
                                 "title": f"'{fname}' produced almost no extractable text",
                                 "detail": "The document may be scanned/images — run OCR or upload a text version."})
                continue
            if text:
                findings.append({"category": "content", "type": "positive",
                                 "title": f"'{fname}' parsed successfully",
                                 "detail": f"Extracted {len(text)} chars. Covers: {', '.join(found_categories) or 'general content'}."})
        return findings

    # ── Run ──────────────────────────────────────────────────
    def run(self, entity: dict, documents: list[dict] | None = None) -> AuditResult:
        start = time.time()
        result = AuditResult(entity)
        name = entity.get("name", "")
        website = entity.get("website", "")

        # Step 1 — reach check
        s = AgentStep(1, "Reach check", "Verify which internet reach channels are available before auditing.")
        tc = ToolCall("reach_channels", {"toolkit": "web, search, social, ocr"}, "", True, 0)
        t0 = time.time()
        try:
            report = self._reach_channels()
            tc.result = json.dumps(report)
            result.reach_report = report
        except Exception as e:
            tc.success = False
            tc.error = str(e)
        tc.duration_ms = (time.time() - t0) * 1000
        s.tool_calls.append(tc)
        s.output = "Channels ready." if tc.success else "Reach degraded — continuing with available tools."
        result.steps.append(s)

        # Step 2 — fetch website
        s = AgentStep(2, "Fetch website", f"Retrieve and parse {website or 'the entity website'} to inspect the live digital presence.")
        tc = ToolCall("web_fetch", {"url": website}, "", True, 0)
        site: dict = {}
        t0 = time.time()
        if website:
            site = self._web_fetch(_norm_url(website))
            tc.args["final_url"] = site.get("final_url", website)
            tc.result = json.dumps({k: site[k] for k in ("status", "final_url", "title", "https", "mobile_viewport", "images", "text_len")})
            tc.success = "error" not in site and site.get("status") is not None
            tc.error = site.get("error", "")
        else:
            tc.success = False
            tc.error = "no website URL configured"
        tc.duration_ms = (time.time() - t0) * 1000
        s.tool_calls.append(tc)
        s.output = f"Fetched {site.get('final_url', website)} (HTTP {site.get('status')})." if tc.success else "Website fetch unavailable."
        result.steps.append(s)

        # Step 3 — search brand
        s = AgentStep(3, "Search brand", f"Search the web for '{name}' to check visibility and indexation.")
        tc = ToolCall("search", {"query": name}, "", True, 0)
        t0 = time.time()
        search_results = self._search(f'"{name}"') if name else []
        tc.result = json.dumps([{"title": r["title"], "url": r["url"]} for r in search_results])
        tc.success = len(search_results) > 0
        tc.duration_ms = (time.time() - t0) * 1000
        s.tool_calls.append(tc)
        s.output = f"Found {len(search_results)} result(s)."
        result.steps.append(s)

        # Step 4 — analyze
        s = AgentStep(4, "Analyze findings", "Convert raw signals into digital-presence findings for the SWOT.")
        t0 = time.time()
        findings = []
        if site:
            findings += self._analyze_site(site, name, website)
        findings += self._analyze_search(search_results, name, website)
        findings += self._analyze_documents(documents or [])
        tc = ToolCall("analyze", {"signals": {"website": bool(site), "search_results": len(search_results), "documents": len(documents or [])}},
                      f"Emitted {len(findings)} findings.", True, 0)
        tc.duration_ms = (time.time() - t0) * 1000
        s.tool_calls.append(tc)
        result.findings = findings
        s.output = tc.result
        result.steps.append(s)

        result.summary = self._summarize(findings)
        result.total_duration_ms = (time.time() - start) * 1000
        return result

    def _summarize(self, findings: list[dict]) -> str:
        pos = sum(1 for f in findings if f["type"] == "positive")
        neg = sum(1 for f in findings if f["type"] == "negative")
        if not findings:
            return "No signals captured — add a website URL and/or upload documents for a richer audit."
        return f"Reach agent audited the live digital presence: {pos} strengths and {neg} weaknesses detected. " \
               f"These were merged into the SWOT below."
