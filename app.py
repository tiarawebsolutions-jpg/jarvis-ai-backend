
import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
APP_TOKEN = os.environ.get("APP_TOKEN", "").strip()
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM = (
    "You are JARVIS, a friendly voice assistant inside an Android app. "
    "Reply in the same language the user speaks, including Hindi, "
    "Hinglish or English. Keep answers short and natural for voice."
)

@app.get("/")
def home():
    return "JARVIS Gemini backend is running"

@app.post("/chat")
def chat():
    if APP_TOKEN:
        sent = request.headers.get("Authorization", "")
        if sent != "Bearer " + APP_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "Message is empty"}), 400

    if not GEMINI_API_KEY:
        return jsonify({
            "error": "GEMINI_API_KEY is missing in Render Environment"
        }), 500

    contents = []
    history = data.get("history") or []

    for item in history[-10:]:
        if not isinstance(item, dict):
            continue

        role = item.get("role", "")
        content = item.get("content", "")

        if role not in ("user", "assistant", "model"):
            continue
        if not isinstance(content, str) or not content.strip():
            continue

        gemini_role = "model" if role in ("assistant", "model") else "user"

        if contents and contents[-1]["role"] == gemini_role:
            contents[-1]["parts"][0]["text"] += "\n" + content.strip()
        else:
            contents.append({
                "role": gemini_role,
                "parts": [{"text": content.strip()}]
            })

    # Ensure history ends with a user message
    if not contents or contents[-1]["role"] != "user":
        contents.append({
            "role": "user",
            "parts": [{"text": message}]
        })
    else:
        contents[-1]["parts"][0]["text"] += "\n" + message

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + MODEL + ":generateContent"
    )

    try:
        response = requests.post(
            url,
            headers={
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json"
            },
            json={
                "systemInstruction": {
                    "parts": [{"text": SYSTEM}]
                },
                "contents": contents,
                "generationConfig": {
                    "maxOutputTokens": 300
                }
            },
            timeout=60
        )

        if response.status_code != 200:
            return jsonify({
                "error": "Gemini API request failed",
                "status": response.status_code,
                "detail": response.text[:1000]
            }), 502

        result = response.json()
        answer = (
            result["candidates"][0]["content"]["parts"][0]["text"]
        )

        return jsonify({"answer": answer})

    except Exception as exc:
        app.logger.exception("JARVIS chat request failed")
        return jsonify({
            "error": "Backend request failed",
            "detail": str(exc)[:300]
        }), 502


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
