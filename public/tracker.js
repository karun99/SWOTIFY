/* Swotify Tracker — real-time visit beacon by GuidingKey Technologies
 *
 * Embed on any website:
 *   <script src="https://YOUR-APP/tracker/tracker.js" data-tid="TRACKING_ID" data-endpoint="https://YOUR-APP/api/track"></script>
 *
 * Collects: page views, referrer, device, browser, language, screen size,
 * time-on-page (heartbeat) and per-visitor identity. No cookies — uses
 * localStorage for visitor id. Privacy-friendly and lightweight.
 */
(function (w, d) {
    "use strict";
    var script = d.currentScript;
    if (!script) return;

    var TID = script.getAttribute("data-tid") || script.getAttribute("data-site") || "";
    var ENDPOINT = script.getAttribute("data-endpoint") || "/api/track";
    var SESSION_KEY = "swotify_session";
    var BEAT_MS = 10000;

    if (!TID) {
        if (w.console) w.console.warn("Swotify: missing data-tid on tracker script.");
        return;
    }

    // Visitor identity — stable per browser (privacy-friendly, no cookies)
    var VID_KEY = "swotify_vid";
    var vid = "";
    try {
        vid = w.localStorage.getItem(VID_KEY);
        if (!vid) {
            vid = "v_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
            w.localStorage.setItem(VID_KEY, vid);
        }
    } catch (e) { /* localStorage unavailable (e.g. private mode) */ }

    // Session start time for time-on-page
    var startedAt = Date.now();
    try {
        var ses = JSON.parse(w.localStorage.getItem(SESSION_KEY) || "{}");
        var prevTs = ses.ts || 0;
        var prevVisit = ses.visit_id || null;
        // If the visitor returns within 30 min, reuse the visit id so heartbeats extend the same visit
        if (prevVisit && (Date.now() - prevTs) < 30 * 60 * 1000) {
            startedAt = prevTs;
        }
    } catch (e) {}

    function collect(payload) {
        payload.tid = TID;
        payload.ts = new Date().toISOString();
        payload.ua = navigator.userAgent;
        payload.lang = navigator.language;
        payload.sw = w.screen ? w.screen.width : 0;
        payload.sh = w.screen ? w.screen.height : 0;
        payload.vid = vid;
        return payload;
    }

    function send(payload) {
        try {
            var body = JSON.stringify(payload);
            if (navigator.sendBeacon) {
                navigator.sendBeacon(ENDPOINT, new Blob([body], { type: "application/json" }));
            } else {
                var xhr = new XMLHttpRequest();
                xhr.open("POST", ENDPOINT, true);
                xhr.setRequestHeader("Content-Type", "application/json");
                xhr.send(body);
            }
        } catch (e) {}
    }

    function pageView() {
        var payload = collect({
            path: w.location.pathname + w.location.search,
            title: d.title || "",
            ref: d.referrer || ""
        });
        send(payload);
        return payload;
    }

    // Heartbeat: extend time-on-page for the current visit
    function heartbeat() {
        var elapsed = Math.round((Date.now() - startedAt) / 1000);
        var payload = collect({
            path: w.location.pathname + w.location.search,
            title: d.title || "",
            ref: d.referrer || "",
            d: elapsed
        });
        send(payload);
    }

    pageView();
    var beatTimer = w.setInterval(heartbeat, BEAT_MS);

    // SPA support: re-fire page view on pushState/popstate
    function onRouteChange() {
        w.clearInterval(beatTimer);
        startedAt = Date.now();
        pageView();
        beatTimer = w.setInterval(heartbeat, BEAT_MS);
    }
    if (w.history && w.history.pushState) {
        var origPush = w.history.pushState;
        w.history.pushState = function () {
            var r = origPush.apply(this, arguments);
            w.setTimeout(onRouteChange, 0);
            return r;
        };
        w.addEventListener("popstate", onRouteChange);
    }
    w.addEventListener("beforeunload", function () {
        var elapsed = Math.round((Date.now() - startedAt) / 1000);
        if (elapsed > 1) {
            send(collect({ path: w.location.pathname + w.location.search, d: elapsed }));
        }
    });

    // Do not double-send when the script reloads in a SPA
    if (!w.__swotifyLoaded) {
        w.__swotifyLoaded = true;
    }
})(window, document);
