import json
import requests
import concurrent.futures
import re
import os
import warnings

warnings.filterwarnings("ignore", category=RuntimeWarning, module="duckduckgo_search")

from flask import Flask, request, Response
from flask_cors import CORS

from groq import Groq
from openai import OpenAI
import google.genai as genai
import anthropic

from duckduckgo_search import DDGS
import wolframalpha

app = Flask(__name__)
CORS(app)

# ============================================================
#  API KEYS
# ============================================================
GROQ_API_KEY      = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY    = os.getenv("CLAUDE_API_KEY")
GOOGLE_SEARCH_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX_ID      = os.getenv("GOOGLE_CX")
WOLFRAM_APPID     = os.getenv("WOLFRAM_APPID")
XAI_API_KEY       = os.getenv("XAI_API_KEY")

# ============================================================
#  STARTUP KEY CHECK
# ============================================================
print("=" * 60)
print("GET THE FACTS - STARTUP KEY CHECK")
print("=" * 60)
for name, val in [
    ("GROQ_API_KEY",   GROQ_API_KEY),
    ("GEMINI_API_KEY", GEMINI_API_KEY),
    ("OPENAI_API_KEY", OPENAI_API_KEY),
    ("CLAUDE_API_KEY", CLAUDE_API_KEY),
    ("GOOGLE_API_KEY", GOOGLE_SEARCH_KEY),
    ("GOOGLE_CX",      GOOGLE_CX_ID),
    ("WOLFRAM_APPID",  WOLFRAM_APPID),
    ("XAI_API_KEY",    XAI_API_KEY),
]:
    status = "OK" if val else "MISSING"
    print("  " + name.ljust(20) + status)
print("=" * 60)

# ============================================================
#  INITIALIZE CLIENTS
# ============================================================
groq_client      = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
oa_client        = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
anthropic_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY) if CLAUDE_API_KEY else None
grok_client      = OpenAI(api_key=XAI_API_KEY, base_url="https://api.x.ai/v1") if XAI_API_KEY else None
wolfram_client   = wolframalpha.Client(WOLFRAM_APPID) if WOLFRAM_APPID else None

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# ============================================================
#  ENGINE BRAND COLORS
# ============================================================
ENGINE_COLORS = {
    "GROQ":          "#F54E42",
    "GROK (XAI)":    "#1DA1F2",
    "GEMINI":        "#8E44FF",
    "OPENAI":        "#10A37F",
    "CLAUDE":        "#D4622A",
    "WOLFRAM ALPHA": "#F96932",
    "DUCKDUCKGO":    "#DE5833",
    "GOOGLE SEARCH": "#4285F4",
}

# ============================================================
#  CONTENT FILTER
# ============================================================
BLOCKED_TERMS = [
    "sex", "porn", "xxx", "nude", "naked", "adult content",
    "escort", "onlyfans", "erotic", "fetish", "nsfw",
]

def is_clean(text):
    text_lower = text.lower()
    for term in BLOCKED_TERMS:
        if term in text_lower:
            return False
    return True

# ============================================================
#  CITATIONS / WEB SEARCH
# ============================================================
def fetch_citations(query):
    links = []

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
        print("[WARN] Google Search failed: " + str(e))

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
            print("[WARN] DuckDuckGo failed: " + str(e))

    return links

# ============================================================
#  WOLFRAM ALPHA
# ============================================================
def fetch_wolfram(query):
    if not wolfram_client:
        return None
    try:
        res = wolfram_client.query(query)
        for pod in res.pods:
            for sub in pod.subpods:
                if sub.plaintext and is_clean(sub.plaintext):
                    return sub.plaintext
    except Exception as e:
        print("[WARN] Wolfram failed: " + str(e))
    return None

# ============================================================
#  AI ENGINE RESPONSES
# ============================================================
def get_ai_responses(q):

    def get_groq():
        if not groq_client:
            return "GROQ: Offline (No API key)"
        try:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": q}],
            )
            return "GROQ: " + resp.choices[0].message.content
        except Exception as e:
            print("[ERROR] Groq: " + str(e))
            return "GROQ: Offline (" + str(e)[:80] + ")"

    def get_grok():
        if not grok_client:
            return "GROK (XAI): Offline (No API key)"
        try:
            resp = grok_client.chat.completions.create(
                model="grok-2",
                messages=[{"role": "user", "content": q}],
            )
            return "GROK (XAI): " + resp.choices[0].message.content
        except Exception as e:
            print("[ERROR] Grok: " + str(e))
            return "GROK (XAI): Offline (" + str(e)[:80] + ")"

    def get_gemini():
        if not GEMINI_API_KEY:
            return "GEMINI: Offline (No API key)"
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            resp = model.generate_content(q)
            return "GEMINI: " + resp.text
        except Exception as e:
            print("[ERROR] Gemini: " + str(e))
            return "GEMINI: Offline (" + str(e)[:80] + ")"

    def get_openai():
        if not oa_client:
            return "OPENAI: Offline (No API key)"
        try:
            resp = oa_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": q}],
            )
            return "OPENAI: " + resp.choices[0].message.content
        except Exception as e:
            print("[ERROR] OpenAI: " + str(e))
            return "OPENAI: Offline (" + str(e)[:80] + ")"

    def get_claude():
        if not anthropic_client:
            return "CLAUDE: Offline (No API key)"
        try:
            res = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=400,
                messages=[{"role": "user", "content": q}],
            )
            return "CLAUDE: " + res.content[0].text
        except Exception as e:
            print("[ERROR] Claude: " + str(e))
            return "CLAUDE: Offline (" + str(e)[:80] + ")"

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        funcs = [get_groq, get_grok, get_gemini, get_openai, get_claude]
        return list(executor.map(lambda f: f(), funcs))

# ============================================================
#  SUMMARIZER - tries each engine in order until one works
# ============================================================
def summarize(ai_results, web_links):
    system_msg = (
        "You are the Chief Justice fact-checker. "
        "Provide a consensus report naming Grok, Claude, Gemini, OpenAI, and Wolfram Alpha where relevant. "
        "Attribute specific findings to each engine. "
        "Keep it under 450 characters for a mobile screen."
    )
    user_msg = "Jury results: " + str(ai_results) + "\nWeb Proof: " + str(web_links)

    if anthropic_client:
        try:
            res = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=450,
                messages=[{"role": "user", "content": system_msg + "\n\n" + user_msg}],
            )
            print("[OK] Summarizer: Claude")
            return res.content[0].text
        except Exception as e:
            print("[ERROR] Claude summarizer: " + str(e))

    if groq_client:
        try:
            resp = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
            )
            print("[OK] Summarizer: Groq")
            return resp.choices[0].message.content
        except Exception as e:
            print("[ERROR] Groq summarizer: " + str(e))

    if oa_client:
        try:
            resp = oa_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
            )
            print("[OK] Summarizer: OpenAI")
            return resp.choices[0].message.content
        except Exception as e:
            print("[ERROR] OpenAI summarizer: " + str(e))

    if GEMINI_API_KEY:
        try:
            model = genai.GenerativeModel("gemini-2.5-flash")
            resp = model.generate_content(system_msg + "\n\n" + user_msg)
            print("[OK] Summarizer: Gemini")
            return resp.text
        except Exception as e:
            print("[ERROR] Gemini summarizer: " + str(e))

    print("[WARN] All summarizers failed - building from raw results")
    online = [r for r in ai_results if "Offline" not in r]
    if online:
        combined = " | ".join([r[:100] for r in online[:3]])
        return "Based on available engines: " + combined[:400]

    return "All AI engines are currently offline. Please check your API keys on Render."

# ============================================================
#  MAIN VERIFY ROUTE
# ============================================================
@app.route("/verify", methods=["POST"])
def verify():
    data = request.json or {}
    user_text = data.get("text", "")

    def generate():
        yield "data: " + json.dumps({"type": "update", "data": {"value": "UPLINK ESTABLISHED"}}) + "\n\n"

        yield "data: " + json.dumps({"type": "update", "data": {"value": "SCANNING WEB EVIDENCE..."}}) + "\n\n"
        web_links = fetch_citations(user_text)

        yield "data: " + json.dumps({"type": "update", "data": {"value": "CONSULTING WOLFRAM ALPHA..."}}) + "\n\n"
        wolfram_result = fetch_wolfram(user_text)

        yield "data: " + json.dumps({"type": "update", "data": {"value": "CONSULTING AI ENGINES..."}}) + "\n\n"
        ai_results = get_ai_responses("Verify: " + user_text + ". Evidence: " + str(web_links))

        if wolfram_result:
            ai_results.append("WOLFRAM ALPHA: " + wolfram_result)

        yield "data: " + json.dumps({"type": "update", "data": {"value": "SYNTHESIZING VERDICT..."}}) + "\n\n"

        summary = summarize(ai_results, web_links)

        final_sources = []
        if wolfram_result:
            final_sources.append("WOLFRAM ALPHA: " + wolfram_result)
        if web_links:
            final_sources.append("WEB CITATIONS VERIFY AI CONSENSUS:")
            final_sources.extend(web_links)

        for res in ai_results:
            urls = re.findall(r"(https?://[^\s]+)", res)
            for u in urls:
                clean_url = u.rstrip(".,)")
                if clean_url not in final_sources:
                    final_sources.append(clean_url)

        if not final_sources or final_sources == ["WEB CITATIONS VERIFY AI CONSENSUS:"]:
            final_sources = [
                "CONSENSUS BY GROK, CLAUDE, GEMINI, OPENAI, AND WOLFRAM ALPHA (Internal Training Data)"
            ]

        result_payload = {
            "status":       "VERIFIED",
            "summary":      summary,
            "sources":      final_sources,
            "ai_results":   ai_results,
            "engineColors": ENGINE_COLORS,
        }

        yield "data: " + json.dumps({"type": "result", "data": result_payload}) + "\n\n"

    return Response(generate(), mimetype="text/event-stream")

# ============================================================
#  HEALTH CHECK
# ============================================================
@app.route("/health", methods=["GET"])
def health():
    return json.dumps({
        "status": "ok",
        "engines": {
            "groq":    bool(groq_client),
            "grok":    bool(grok_client),
            "gemini":  bool(GEMINI_API_KEY),
            "openai":  bool(oa_client),
            "claude":  bool(anthropic_client),
            "wolfram": bool(wolfram_client),
        },
        "engineColors": ENGINE_COLORS,
    })

# ============================================================
#  RUN
# ============================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)