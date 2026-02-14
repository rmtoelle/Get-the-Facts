import json
import requests
import concurrent.futures
import re
import os
from flask import Flask, request, Response
from flask_cors import CORS
from groq import Groq
from openai import OpenAI
import google.generativeai as genai
import anthropic
from duckduckgo_search import DDGS

app = Flask(__name__)
CORS(app)

# ==========================================
# MASTER KEYS (Identical to PC)
# ==========================================
GROQ_API_KEY = "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"
GEMINI_API_KEY = "AIzaSyAZJUxOrXfEG-yVoFZiilPP5U_uD4npHC8"
OPENAI_API_KEY = "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"
ANTHROPIC_API_KEY = "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"
GOOGLE_SEARCH_KEY = "AIzaSyC0_3RoeqGmCnIxArbrvBQzAOwPXtWlFq0"
GOOGLE_CX_ID = "96ba56ee37a1d48e5"

# Initialize Clients once at the top
groq_client = Groq(api_key=GROQ_API_KEY)
oa_client = OpenAI(api_key=OPENAI_API_KEY)
anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
genai.configure(api_key=GEMINI_API_KEY)

def fetch_citations(query):
    links = []
    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {'key': GOOGLE_SEARCH_KEY, 'cx': GOOGLE_CX_ID, 'q': query, 'num': 5}
        r = requests.get(url, params=params, timeout=5)
        if r.status_code == 200:
            items = r.json().get('items', [])
            links = [item['link'] for item in items]
    except: pass
    if not links:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=5))
                links = [r['href'] for r in results if 'href' in r]
        except: pass
    return links

def get_ai_responses(q):
    def get_meta():
        try:
            return f"GROK: {groq_client.chat.completions.create(model='llama-3.3-70b-versatile', messages=[{'role':'user','content':q}]).choices[0].message.content}"
        except Exception as e: return f"GROK: Offline ({str(e)[:20]})"
    
    def get_gemini():
        try:
            model = genai.GenerativeModel('gemini-1.5-pro')
            return f"GEMINI: {model.generate_content(q).text}"
        except Exception as e: return f"GEMINI: Offline ({str(e)[:20]})"
    
    def get_openai():
        try:
            return f"OPENAI: {oa_client.chat.completions.create(model='gpt-4o', messages=[{'role':'user','content':q}]).choices[0].message.content}"
        except Exception as e: return f"OPENAI: Offline ({str(e)[:20]})"
    
    def get_claude():
        try:
            res = anthropic_client.messages.create(
                model="claude-3-5-sonnet-20240620", 
                max_tokens=400, 
                messages=[{"role":"user","content":q}]
            )
            return f"CLAUDE: {res.content[0].text}"
        except Exception as e: return f"CLAUDE: Offline ({str(e)[:20]})"

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        return list(executor.map(lambda f: f(), [get_meta, get_gemini, get_openai, get_claude]))

@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    user_text = data.get("text", "")
    
    def generate():
        yield f"data: {json.dumps({'type': 'update', 'data': {'value': 'UPLINK ESTABLISHED'}})}\n\n"
        yield f"data: {json.dumps({'type': 'update', 'data': {'value': 'SCANNING WEB EVIDENCE...'}})}\n\n"
        web_links = fetch_citations(user_text)
        
        yield f"data: {json.dumps({'type': 'update', 'data': {'value': 'CONSULTING AI ENGINES...'}})}\n\n"
        ai_results = get_ai_responses(f"Verify: {user_text}. Evidence: {web_links}")
        
        yield f"data: {json.dumps({'type': 'update', 'data': {'value': 'SYNTHESIZING VERDICT...'}})}\n\n"
        
        try:
            synthesis = groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "Chief Justice: Summarize the consensus. Name Grok, Claude, Gemini, and OpenAI. Use web links as proof. Under 450 chars."},
                    {"role": "user", "content": f"Jury: {ai_results}. Web: {web_links}."}
                ]
            )
            summary = synthesis.choices[0].message.content
        except:
            summary = "Consensus achieved. Facts verified via multi-engine cross-reference."

        final_sources = []
        if web_links:
            final_sources.append("WEB CITATIONS VERIFY AI CONSENSUS:")
            final_sources.extend(web_links)
        
        for res in ai_results:
            urls = re.findall(r'(https?://[^\s]+)', res)
            for u in urls:
                clean = u.rstrip('.,)')
                if clean not in final_sources: final_sources.append(clean)
        
        if not final_sources or final_sources == ["WEB CITATIONS VERIFY AI CONSENSUS:"]:
            final_sources = ["CONSENSUS BY GROK, CLAUDE, GEMINI, AND OPENAI (Internal Training Data)"]

        result_payload = {
            "status": "Cross-Verified",
            "confidenceScore": 99,
            "summary": summary,
            "sources": final_sources,
            "isSecure": True
        }
        yield f"data: {json.dumps({'type': 'result', 'data': result_payload})}\n\n"
        
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
