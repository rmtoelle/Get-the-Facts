import json
import requests
import concurrent.futures
import re
import os
import warnings

# Suppress duckduckgo_search rename warning

warnings.filterwarnings(“ignore”, category=RuntimeWarning, module=“duckduckgo_search”)

from flask import Flask, request, Response
from flask_cors import CORS

# AI Engines

from groq import Groq
from openai import OpenAI
import google.genai as genai
import anthropic

# Search Engines

from duckduckgo_search import DDGS
import wolframalpha

app = Flask(**name**)
CORS(app)

# ============================================================

# API KEYS — FROM ENVIRONMENT VARIABLES (set on Render)

# ============================================================

GROQ_API_KEY      = os.getenv(“GROQ_API_KEY”)
GEMINI_API_KEY    = os.getenv(“GEMINI_API_KEY”)
OPENAI_API_KEY    = os.getenv(“OPENAI_API_KEY”)
CLAUDE_API_KEY    = os.getenv(“CLAUDE_API_KEY”)
GOOGLE_SEARCH_KEY = os.getenv(“GOOGLE_API_KEY”)
GOOGLE_CX_ID      = os.getenv(“GOOGLE_CX”)
WOLFRAM_APPID     = os.getenv(“WOLFRAM_APPID”)
XAI_API_KEY       = os.getenv(“XAI_API_KEY”)

# ============================================================

# STARTUP: SHOW WHICH KEYS ARE LOADED

# ============================================================

print(”=” * 60)
print(“GET THE FACTS — STARTUP KEY CHECK”)
print(”=” * 60)
for name, val in [
(“GROQ_API_KEY”,   GROQ_API_KEY),
(“GEMINI_API_KEY”, GEMINI_API_KEY),
(“OPENAI_API_KEY”, OPENAI_API_KEY),
(“CLAUDE_API_KEY”, CLAUDE_API_KEY),
(“GOOGLE_API_KEY”, GOOGLE_SEARCH_KEY),
(“GOOGLE_CX”,      GOOGLE_CX_ID),
(“WOLFRAM_APPID”,  WOLFRAM_APPID),
(“XAI_API_KEY”,    XAI_API_KEY),
]:
status = “OK” if val else “MISSING”
print(f”  {name:<20} {status}”)
print(”=” * 60)

# ============================================================

# INITIALIZE CLIENTS

# ============================================================

groq_client      = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
oa_client        = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
anthropic_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None
grok_client      = OpenAI(api_key=XAI_API_KEY, base_url=“https://api.x.ai/v1”) if XAI_API_KEY else None
wolfram_client   = wolframalpha.Client(WOLFRAM_APPID) if WOLFRAM_APPID else None

if GEMINI_API_KEY:
genai.configure(api_key=GEMINI_API_KEY)

# ============================================================

# ENGINE BRAND COLORS

# ============================================================

ENGINE_COLORS = {
“GROQ”:          “#F54E42”,   # Groq red
“GROK (XAI)”:    “#1DA1F2”,   # X/Twitter blue
“GEMINI”:        “#8E44FF”,   # Google Gemini purple
“OPENAI”:        “#10A37F”,   # OpenAI green
“CLAUDE”:        “#D4622A”,   # Anthropic orange
“WOLFRAM ALPHA”: “#F96932”,   # Wolfram orange
“DUCKDUCKGO”:    “#DE5833”,   # DDG orange-red
“GOOGLE SEARCH”: “#4285F4”,   # Google blue
}

# ============================================================

# CONTENT FILTER

# ============================================================

BLOCKED_TERMS = [
“sex”, “porn”, “xxx”, “nude”, “naked”, “adult content”,
“سكس”, “اباحي”, “جنس”, “بورنو”, “نيك”, “مقاطع”,
“escort”, “onlyfans”, “erotic”, “fetish”, “nsfw”,
]

def is_clean(text):
text_lower = text.lower()
for term in BLOCKED_TERMS:
if term in text_lower:
return False
return True

# ============================================================

# CITATIONS / WEB SEARCH

# ============================================================

def fetch_citations(query: str):
links = []

```
# First try Google Custom Search
try:
    if GOOGLE_SEARCH_KEY and GOOGLE_CX_ID:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_SEARCH_KEY,
            "cx": GOOGLE_CX_ID,
            "q": query,
            "num": 5,
        }
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            items = r.json().get("items", [])
            links = [item["link"] for item in items if is_clean(item.get("snippet", ""))]
except Exception as e:
    print(f"[WARN] Google Search failed: {e}")

# Fallback to DuckDuckGo
if not links:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=10))
            for r in results:
                href = r.get("href", "")
                snippet = r.get("body") or r.get("snippet") or ""
                if href and is_clean(snippet):
                    links.append(href)
                if len(links) >= 5:
                    break
    except Exception as e:
        print(f"[WARN] DuckDuckGo failed: {e}")

return links
```

# ============================================================

# WOLFRAM ALPHA

# ============================================================

def fetch_wolfram(query: str):
if not wolfram_client:
return None
try:
res = wolfram_client.query(query)
for pod in res.pods:
for sub in pod.subpods:
if sub.plaintext and is_clean(sub.plaintext):
return sub.plaintext
except Exception as e:
print(f”[WARN] Wolfram failed: {e}”)
return None

# ============================================================

# AI ENGINE RESPONSES

# ============================================================

def get_ai_responses(q: str):

```
def get_groq():
    if not groq_client:
        return "GROQ: Offline (No API key)"
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": q}],
        )
        return f"GROQ: {resp.choices[0].message.content}"
    except Exception as e:
        print(f"[ERROR] Groq: {e}")
        return f"GROQ: Offline ({str(e)[:80]})"

def get_grok():
    if not grok_client:
        return "GROK (XAI): Offline (No API key)"
    try:
        resp = grok_client.chat.completions.create(
            model="grok-2",
            messages=[{"role": "user", "content": q}],
        )
        return f"GROK (XAI): {resp.choices[0].message.content}"
    except Exception as e:
        print(f"[ERROR] Grok: {e}")
        return f"GROK (XAI): Offline ({str(e)[:80]})"

def get_gemini():
    if not GEMINI_API_KEY:
        return "GEMINI: Offline (No API key)"
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        resp = model.generate_content(q)
        return f"GEMINI: {resp.text}"
    except Exception as e:
        print(f"[ERROR] Gemini: {e}")
        return f"GEMINI: Offline ({str(e)[:80]})"

def get_openai():
    if not oa_client:
        return "OPENAI: Offline (No API key)"
    try:
        resp = oa_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": q}],
        )
        return f"OPENAI: {resp.choices[0].message.content}"
    except Exception as e:
        print(f"[ERROR] OpenAI: {e}")
        return f"OPENAI: Offline ({str(e)[:80]})"

def get_claude():
    if not anthropic_client:
        return "CLAUDE: Offline (No API key)"
    try:
        res = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=400,
            messages=[{"role": "user", "content": q}],
        )
        return f"CLAUDE: {res.content[0].text}"
    except Exception as e:
        print(f"[ERROR] Claude: {e}")
        return f"CLAUDE: Offline ({str(e)[:80]})"

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    funcs = [get_groq, get_grok, get_gemini, get_openai, get_claude]
    return list(executor.map(lambda f: f(), funcs))
```

# ============================================================

# SUMMARIZER — tries each engine in order until one works

# ============================================================

def summarize(ai_results, web_links):
prompt_content = (
“You are the Chief Justice fact-checker. “
“Provide a consensus report naming Grok, Claude, Gemini, OpenAI, and Wolfram Alpha where relevant. “
“Attribute specific findings to each engine. “
“Keep it under 450 characters for a mobile screen.\n\n”
f”Jury results: {ai_results}\nWeb Proof: {web_links}”
)

```
# Try Claude first
if anthropic_client:
    try:
        res = anthropic_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=450,
            messages=[{"role": "user", "content": prompt_content}],
        )
        print("[OK] Summarizer: Claude")
        return res.content[0].text
    except Exception as e:
        print(f"[ERROR] Claude summarizer failed: {e}")

# Try Groq second
if groq_client:
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are the Chief Justice. Provide a consensus report. Name Grok, Claude, Gemini, OpenAI, and Wolfram Alpha where relevant. Keep it under 450 characters for a mobile screen."},
                {"role": "user", "content": f"Jury results: {ai_results}. Web Proof: {web_links}."},
            ],
        )
        print("[OK] Summarizer: Groq")
        return resp.choices[0].message.content
    except Exception as e:
        print(f"[ERROR] Groq summarizer failed: {e}")

# Try OpenAI third
if oa_client:
    try:
        resp = oa_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a fact-checker. Summarize the consensus from multiple AI engines. Keep it under 450 characters."},
                {"role": "user", "content": f"Jury results: {ai_results}. Web Proof: {web_links}."},
            ],
        )
        print("[OK] Summarizer: OpenAI")
        return resp.choices[0].message.content
    except Exception as e:
        print(f"[ERROR] OpenAI summarizer failed: {e}")

# Try Gemini fourth
if GEMINI_API_KEY:
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        resp = model.generate_content(prompt_content)
        print("[OK] Summarizer: Gemini")
        return resp.text
    except Exception as e:
        print(f"[ERROR] Gemini summarizer failed: {e}")

# All engines failed — build a real summary from what we have
print("[WARN] All summarizers failed — building summary from raw results")
online = [r for r in ai_results if "Offline" not in r]
if online:
    combined = " | ".join([r[:100] for r in online[:3]])
    return f"Based on available engines: {combined[:400]}"

return "All AI engines are currently offline. Please check your API keys on Render."
```

# ============================================================

# MAIN VERIFY ROUTE

# ============================================================

@app.route(”/verify”, methods=[“POST”])
def verify():
data = request.json or {}
user_text = data.get(“text”, “”)

```
def generate():
    yield f"data: {json.dumps({'type': 'update', 'data': {'value': 'UPLINK ESTABLISHED'}})}\n\n"

    yield f"data: {json.dumps({'type': 'update', 'data': {'value': 'SCANNING WEB EVIDENCE...'}})}\n\n"
    web_links = fetch_citations(user_text)

    yield f"data: {json.dumps({'type': 'update', 'data': {'value': 'CONSULTING WOLFRAM ALPHA...'}})}\n\n"
    wolfram_result = fetch_wolfram(user_text)

    yield f"data: {json.dumps({'type': 'update', 'data': {'value': 'CONSULTING AI ENGINES...'}})}\n\n"
    ai_results = get_ai_responses(f"Verify: {user_text}. Evidence: {web_links}")

    if wolfram_result:
        ai_results.append(f"WOLFRAM ALPHA: {wolfram_result}")

    yield f"data: {json.dumps({'type': 'update', 'data': {'value': 'SYNTHESIZING VERDICT...'}})}\n\n"

    summary = summarize(ai_results, web_links)

    # Build sources list
    final_sources = []
    if wolfram_result:
        final_sources.append(f"WOLFRAM ALPHA: {wolfram_result}")
    if web_links:
        final_sources.append("WEB CITATIONS VERIFY AI CONSENSUS:")
        final_sources.extend(web_links)

    for res in ai_results:
        urls = re.findall(r"(https?://[^\s]+)", res)
        for u in urls:
            clean = u.rstrip(".,)")
            if clean not in final_sources:
                final_sources.append(clean)

    if not final_sources or final_sources == ["WEB CITATIONS VERIFY AI CONSENSUS:"]:
        final_sources = [
            "CONSENSUS BY GROK, CLAUDE, GEMINI, OPENAI, AND WOLFRAM ALPHA (Internal Training Data)"
        ]

    result_payload = {
        "status":      "VERIFIED",
        "summary":     summary,
        "sources":     final_sources,
        "ai_results":  ai_results,
        "engineColors": ENGINE_COLORS,
    }

    yield f"data: {json.dumps({'type': 'result', 'data': result_payload})}\n\n"

return Response(generate(), mimetype="text/event-stream")
```

# ============================================================

# HEALTH CHECK

# ============================================================

@app.route(”/health”, methods=[“GET”])
def health():
return json.dumps({
“status”: “ok”,
“engines”: {
“groq”:   bool(groq_client),
“grok”:   bool(grok_client),
“gemini”: bool(GEMINI_API_KEY),
“openai”: bool(oa_client),
“claude”: bool(anthropic_client),
“wolfram”: bool(wolfram_client),
},
“engineColors”: ENGINE_COLORS,
})

if **name** == “**main**”:
app.run(host=“0.0.0.0”, port=5000, debug=False)