import os
from flask import Flask, request, Response, stream_with_context
from duckduckgo_search import DDGS
from groq import Groq
import json
import requests
import time

app = Flask(__name__)

# --- CONFIGURATION ---
# In a real production app, these should be Environment Variables,
# but for now, we keep them here for simplicity.
GROQ_API_KEY = "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"
GOOGLE_API_KEY = "AIzaSyCcmyqWEDkF6-S9YyUIUQnUOY5SieS5OcM"
GOOGLE_CX_ID = "96ba56ee37a1d48e5"

# Initialize Groq
client = Groq(api_key=GROQ_API_KEY)

# --- HELPER: SSE FORMATTER ---
def format_sse(data, event_type="update"):
    payload = json.dumps({"type": event_type, "data": data})
    return f"data: {payload}\n\n"

# --- ENGINE 1: KEYWORD GENERATOR ---
def generate_keywords(user_text):
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a Research Specialist. Return ONLY the search string."},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3 
        )
        return completion.choices[0].message.content.strip().replace('"', '')
    except:
        return user_text

# --- ENGINE 2: DEEP SEARCH ---
def perform_deep_search(query, original_text):
    results = []
    seen_urls = set()

    # A. GOOGLE PREMIUM
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {'key': GOOGLE_API_KEY, 'cx': GOOGLE_CX_ID, 'q': query, 'num': 5}
        resp = requests.get(url, params=params).json()
        if 'items' in resp:
            for item in resp['items']:
                if item['link'] not in seen_urls:
                    results.append({"title": item.get('title'), "body": item.get('snippet'), "href": item['link'], "source": "Google Premium"})
                    seen_urls.add(item['link'])
    except Exception as e:
        print(f"Google Error: {e}")

    # B. DUCKDUCKGO
    try:
        with DDGS() as ddgs:
            # News
            for r in ddgs.news(query, region='us-en', max_results=4):
                if r['url'] not in seen_urls:
                    results.append({"title": r['title'], "body": r['body'], "href": r['url'], "source": "DDG News"})
                    seen_urls.add(r['url'])
            # Web
            for r in ddgs.text(query, region='us-en', max_results=4):
                if r['href'] not in seen_urls:
                    results.append({"title": r['title'], "body": r['body'], "href": r['href'], "source": "DDG Web"})
                    seen_urls.add(r['href'])
    except Exception as e:
        print(f"DDG Error: {e}")

    return results

# --- ENGINE 3: THE RUTHLESS JUDGE ---
def analyze_evidence(user_text, evidence_text, sources_list):
    system_prompt = f"""
    You are a Forensic Truth Auditor. Your job is not to be polite; it is to be ACCURATE and DECISIVE.
    
    USER QUERY: "{user_text}"
    
    EVIDENCE FOUND:
    {evidence_text}
    
    MANDATES:
    1. START WITH THE VERDICT: Your summary MUST start with one of these tags: "VERIFIED:", "DEBUNKED:", "HIGHLY SUSPICIOUS:", "DATA INCONCLUSIVE:", or "MARKET CONSENSUS:".
    2. BE RUTHLESS: If the evidence is weak (e.g., just Reddit or Blogs), say "Evidence is anecdotal and unreliable."
    3. CUT THE FLUFF: Do not say "The provided search results suggest..." Say "The data proves X." or "There is zero hard evidence for Y."
    4. STOCKS/FINANCE: If asking about stock, explicitly state the Bull Case vs. the Bear Case.
    
    OUTPUT JSON (Strict Format):
    {{
      "status": "String (Use the Verdict Tag from Mandate 1)",
      "confidenceScore": Integer (0-100. Be harsh. If no hard data, score < 30),
      "summary": "String (3-4 sentences. Hard hitting. No filler.)",
      "sources": {json.dumps(sources_list)},
      "isSecure": true
    }}
    """
    try:
        completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except:
        return None

# --- STREAMING ENDPOINT ---
@app.route('/verify', methods=['POST'])
def verify_stream():
    data = request.json
    user_text = data.get('text', '')

    def generate():
        yield format_sse("INITIALIZING V9 PROTOCOLS...")
        time.sleep(0.3)
        
        keywords = generate_keywords(user_text)
        yield format_sse(f"SEARCHING: {keywords}")
        
        results = perform_deep_search(keywords, user_text)
        yield format_sse(f"ANALYZING {len(results)} SOURCES...")
        
        evidence_text = ""
        sources_list = []
        for i, res in enumerate(results[:10]):
            evidence_text += f"{res['title']}\n{res['body']}\n"
            sources_list.append(res['href'])

        final_json = analyze_evidence(user_text, evidence_text, sources_list)
        
        if final_json:
            yield format_sse(final_json, event_type="result")
        else:
            yield format_sse({"status": "Error"}, event_type="result")

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    # Cloud Port Logic
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)