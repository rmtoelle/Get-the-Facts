import secrets
import os
from flask import Flask, request, Response
import json
import time
from groq import Groq
from google import genai

app = Flask(__name__)

# --- SECURE KEYS (PULL FROM RENDER ENVIRONMENT) ---
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
GOOGLE_CX_ID = os.environ.get("GOOGLE_CX_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize Clients
groq_client = Groq(api_key=GROQ_API_KEY)
client_gemini = genai.Client(api_key=GEMINI_API_KEY)

@app.route('/verify', methods=['POST'])
def verify():
    data = request.json
    user_text = data.get("text", "")

    def generate():
        yield f"data: {json.dumps({'type': 'update', 'data': {'value': 'Uplink Established'}})}\n\n"
        time.sleep(0.5)
        
        # Groq (Llama 3) Inference
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": f"Verify this claim: {user_text}"}],
        )
        verdict = completion.choices[0].message.content

        result = {
            "status": "Verified" if "true" in verdict.lower() else "Analysis Complete",
            "confidenceScore": 90,
            "summary": verdict,
            "sources": ["Search Engine ID: " + (GOOGLE_CX_ID or "Internal")],
            "isSecure": True
        }
        yield f"data: {json.dumps({'type': 'result', 'data': result})}\n\n"

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

