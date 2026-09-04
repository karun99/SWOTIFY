"""Assessment questionnaire for the Swotify digital profile.

5 categories x 4 questions. Each option carries a 0-100 point value
plus a beginner-friendly note. Category score = mean of selected options.
"""

CATEGORIES = [
    {"key": "website", "label": "Website Presence", "weight": 0.25},
    {"key": "social", "label": "Social Media", "weight": 0.20},
    {"key": "seo", "label": "Search Visibility (SEO)", "weight": 0.25},
    {"key": "content", "label": "Content & Engagement", "weight": 0.15},
    {"key": "brand", "label": "Branding & Trust", "weight": 0.15},
]

QUESTIONS = [
    # ---------------- Website ----------------
    {
        "id": "w1",
        "category": "website",
        "text": "Does your business have a website?",
        "options": [
            {"label": "No website yet", "points": 0, "note": "A website is your digital storefront — this is the biggest gap."},
            {"label": "Basic one-page site", "points": 40, "note": "A good start, but it can't rank or convert on its own."},
            {"label": "Multi-page professional site", "points": 75, "note": "Solid foundation — now focus on visitors finding you."},
            {"label": "Modern, fast, mobile-first site", "points": 100, "note": "Excellent — built for today's mobile-first search."},
        ],
    },
    {
        "id": "w2",
        "category": "website",
        "text": "Is your website fast and mobile-friendly?",
        "options": [
            {"label": "Not sure / haven't tested", "points": 0, "note": "Half your visitors use phones. Test now (free tools exist)."},
            {"label": "Works on mobile, a bit slow", "points": 50, "note": "Slow pages lose visitors — aim for under 3 seconds."},
            {"label": "Mobile-friendly and quick", "points": 100, "note": "Great — speed and mobile are ranking signals."},
        ],
    },
    {
        "id": "w3",
        "category": "website",
        "text": "Does your site clearly explain what you offer?",
        "options": [
            {"label": "Visitors can't tell in 5 seconds", "points": 0, "note": "You have ~5 seconds to explain your value."},
            {"label": "Somewhat clear", "points": 50, "note": "Lead with your offer in the headline."},
            {"label": "Crystal clear on every page", "points": 100, "note": "Clear messaging drives conversions."},
        ],
    },
    {
        "id": "w4",
        "category": "website",
        "text": "Does your site have contact details and a call-to-action (CTA)?",
        "options": [
            {"label": "No contact info / no CTA", "points": 0, "note": "Without a CTA you're losing every undecided visitor."},
            {"label": "Contact page only", "points": 50, "note": "Add a CTA on every page — 'Contact us', 'Get a quote'."},
            {"label": "Contact + CTA on every page", "points": 100, "note": "Perfect — you're converting attention into leads."},
        ],
    },
    # ---------------- Social ----------------
    {
        "id": "s1",
        "category": "social",
        "text": "Which social platforms does your business use?",
        "options": [
            {"label": "None", "points": 0, "note": "You're invisible where customers scroll."},
            {"label": "One platform", "points": 40, "note": "Good — pick the platform your customers use most."},
            {"label": "2-3 platforms", "points": 75, "note": "Healthy presence — keep them active."},
            {"label": "4+ platforms, managed", "points": 100, "note": "Wide reach — keep content consistent."},
        ],
    },
    {
        "id": "s2",
        "category": "social",
        "text": "How often do you post on social media?",
        "options": [
            {"label": "Rarely / never", "points": 0, "note": "Inactive accounts signal an inactive business."},
            {"label": "A few times a month", "points": 50, "note": "Consistency beats volume — start weekly."},
            {"label": "Weekly or more", "points": 100, "note": "Consistent posting builds recall and reach."},
        ],
    },
    {
        "id": "s3",
        "category": "social",
        "text": "Do you reply to comments and messages?",
        "options": [
            {"label": "No / ignore them", "points": 0, "note": "Unanswered messages lose sales and trust."},
            {"label": "Sometimes", "points": 50, "note": "Aim to reply within 24 hours."},
            {"label": "Yes, quickly and kindly", "points": 100, "note": "Fast replies build a loyal community."},
        ],
    },
    {
        "id": "s4",
        "category": "social",
        "text": "Is your branding consistent across platforms?",
        "options": [
            {"label": "Different logo/name everywhere", "points": 0, "note": "Inconsistent branding confuses customers."},
            {"label": "Mostly consistent", "points": 60, "note": "Tighten it up so you're instantly recognisable."},
            {"label": "Fully consistent", "points": 100, "note": "Recognition is a superpower for small brands."},
        ],
    },
    # ---------------- SEO ----------------
    {
        "id": "e1",
        "category": "seo",
        "text": "Have you set up Google Search Console?",
        "options": [
            {"label": "What's that?", "points": 0, "note": "It's Google's free dashboard showing how people find you."},
            {"label": "Heard of it, not set up", "points": 30, "note": "Free and easy — this is step one for visibility."},
            {"label": "Set up, I check it", "points": 100, "note": "You have eyes on your search performance."},
        ],
    },
    {
        "id": "e2",
        "category": "seo",
        "text": "Do you have a Google Business Profile?",
        "options": [
            {"label": "No", "points": 0, "note": "Local searches happen on Google Maps — claim your spot."},
            {"label": "Yes, basic info", "points": 55, "note": "Add photos, hours and offers to rank higher locally."},
            {"label": "Yes, fully optimised", "points": 100, "note": "You're winning local search visibility."},
        ],
    },
    {
        "id": "e3",
        "category": "seo",
        "text": "Do you write pages around words people actually search?",
        "options": [
            {"label": "No, I write what I like", "points": 0, "note": "Think like a customer — what would they type?"},
            {"label": "Somewhat", "points": 55, "note": "Research simple keywords for each page."},
            {"label": "Yes, keyword-first", "points": 100, "note": "You're building a page that search engines rank."},
        ],
    },
    {
        "id": "e4",
        "category": "seo",
        "text": "Is your site secure (HTTPS)?",
        "options": [
            {"label": "No / not sure", "points": 0, "note": "Browsers warn visitors and Google penalises non-HTTPS."},
            {"label": "Yes, HTTPS", "points": 100, "note": "Trust badge secured."},
        ],
    },
    # ---------------- Content ----------------
    {
        "id": "c1",
        "category": "content",
        "text": "How often do you publish new content?",
        "options": [
            {"label": "Never", "points": 0, "note": "Content is how you get found and stay relevant."},
            {"label": "Occasionally", "points": 50, "note": "Start a simple monthly cadence."},
            {"label": "Regularly (weekly+)", "points": 100, "note": "Fresh content keeps search and social alive."},
        ],
    },
    {
        "id": "c2",
        "category": "content",
        "text": "Do you have a blog or resources section?",
        "options": [
            {"label": "No", "points": 0, "note": "A blog is your engine for organic visitors."},
            {"label": "Yes, small", "points": 60, "note": "Expand with posts answering customer questions."},
            {"label": "Yes, active", "points": 100, "note": "You're compounding organic reach."},
        ],
    },
    {
        "id": "c3",
        "category": "content",
        "text": "Do you use images and video in your content?",
        "options": [
            {"label": "Text only", "points": 0, "note": "Visuals double engagement — add photos now."},
            {"label": "Some images", "points": 55, "note": "Add short videos for a big engagement lift."},
            {"label": "Rich media (images + video)", "points": 100, "note": "Engaging content keeps people on your page."},
        ],
    },
    {
        "id": "c4",
        "category": "content",
        "text": "Do you collect email sign-ups?",
        "options": [
            {"label": "No", "points": 0, "note": "Your audience is on rented land — email is yours."},
            {"label": "Sign-up form on site", "points": 60, "note": "Now nurture them with useful updates."},
            {"label": "Yes, active newsletter", "points": 100, "note": "A direct line to repeat customers."},
        ],
    },
    # ---------------- Brand ----------------
    {
        "id": "b1",
        "category": "brand",
        "text": "Do you have a consistent logo, colours and fonts?",
        "options": [
            {"label": "No", "points": 0, "note": "Consistent visuals build instant recognition."},
            {"label": "Partial", "points": 55, "note": "Write it down — a simple brand style guide."},
            {"label": "Yes, documented", "points": 100, "note": "Strong identity across every touchpoint."},
        ],
    },
    {
        "id": "b2",
        "category": "brand",
        "text": "Can you state your value proposition in one sentence?",
        "options": [
            {"label": "No / it's unclear", "points": 0, "note": "If you can't say it, neither can your customers."},
            {"label": "Vague idea", "points": 50, "note": "Craft: 'We help [who] achieve [what] by [how]'."},
            {"label": "Yes, crystal clear", "points": 100, "note": "Clear value beats any discount."},
        ],
    },
    {
        "id": "b3",
        "category": "brand",
        "text": "Do you show reviews or testimonials?",
        "options": [
            {"label": "No", "points": 0, "note": "Social proof is your cheapest marketing asset."},
            {"label": "Somewhere", "points": 60, "note": "Put a testimonial on the homepage."},
            {"label": "Yes, prominent", "points": 100, "note": "Trust converts — keep collecting reviews."},
        ],
    },
    {
        "id": "b4",
        "category": "brand",
        "text": "Do you have a privacy policy and terms page?",
        "options": [
            {"label": "No", "points": 0, "note": "Required for trust and often by law."},
            {"label": "Yes", "points": 100, "note": "Handled — compliance is trust."},
        ],
    },
]

QUESTIONS_BY_ID = {q["id"]: q for q in QUESTIONS}
