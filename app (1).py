import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
APP_TOKEN = os.environ.get("APP_TOKEN", "")
MODEL = os.environ.get("MODEL", "claude-sonnet-5-5")

SYSTEM = (
    "You are JARVIS, a friendly voice assistant inside an Android app. "
    "Reply in the same language the user speaks (Hindi, Hinglish or English). "
    "Keep answers short, 1-3 sentences, because they are read aloud."
)


@app.get("/")
def home():
    return "JARVIS backend is running"


@app.post("/chat")
def chat():
    if APP_TOKEN:
        sent = request.headers.get("Authorization", "")
        if sent != "Bearer " + APP_TOKEN:
            return jsonify({"error": "unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    if not message:
        return jsonify({"error": "message is empty"}), 400

    history = data.get("history") or []
    msgs = []
    for h in history[-10:]:
        if isinstance(h, dict) and h.get("role") in ("user", "assistant") and h.get("content"):
            msgs.append({"role": h["role"], "content": str(h["content"])})
    msgs.append({"role": "user", "content": message})

    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": MODEL, "max_tokens": 300, "system": SYSTEM, "messages": msgs},
            timeout=60,
        )
        r.raise_for_status()
        answer = r.json()["content"][0]["text"]
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": "AI request failed", "detail": str(e)[:200]}), 502


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
