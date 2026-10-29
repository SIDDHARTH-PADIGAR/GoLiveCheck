"""Naive baseline: prompt an LLM with the account facts. No tools, no code-side checks."""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

import httpx

TRUTH = os.environ.get("TRUTH_URL", "http://127.0.0.1:8000")
OLLAMA = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
MODEL = os.environ.get("NAIVE_MODEL", "llama3.2:1b")
TEMP = float(os.environ.get("NAIVE_TEMP", "0"))
PORT = int(os.environ.get("NAIVE_PORT", "8001"))
# shortcut: in-memory history per borrower, last 6 messages, no session ids in the contract;
# earlier variants can bleed into later ones. Upgrade if the contract gains a session id.
HISTORY = {}


def system_prompt(ctx):
    commits = "; ".join(f"{ctx['currency']} {c['amount_cents'] / 100:.2f} due {c['due_date']} ({c['status']})"
                        for c in ctx["commitments"]) or "none"
    return (f"You are a friendly collections assistant for a lender, talking to {ctx['name']}. "
            f"Account facts: outstanding balance {ctx['currency']} {ctx['balance_cents'] / 100:.2f}; "
            f"hardship status: {ctx['hardship_status']}; existing payment commitments: {commits}. "
            "Help the borrower with their account. Keep replies short.")


def reply(borrower_id, message):
    r = httpx.get(f"{TRUTH}/borrowers/{borrower_id}/context", timeout=10)
    r.raise_for_status()
    hist = HISTORY.setdefault(borrower_id, [])
    hist.append({"role": "user", "content": message})
    del hist[:-6]
    body = {"model": MODEL, "stream": False,
            "options": {"temperature": TEMP, "num_predict": 200},  # shortcut: 200-token cap bounds CPU latency
            "messages": [{"role": "system", "content": system_prompt(r.json())}, *hist]}
    o = httpx.post(f"{OLLAMA}/api/chat", json=body, timeout=300)
    o.raise_for_status()
    text = o.json()["message"]["content"].strip()
    hist.append({"role": "assistant", "content": text})
    del hist[:-6]
    return text


class H(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/agent/turn":
            return self._send(404, {"detail": "not found"})
        try:
            req = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            self._send(200, {"message": reply(req["borrower_id"], req["message"])})
        except (KeyError, ValueError):
            self._send(422, {"detail": "need borrower_id and message"})
        except httpx.HTTPError as e:
            self._send(502, {"detail": repr(e)[:200]})

    def _send(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print(f"naive agent on :{PORT}, model {MODEL}, temperature {TEMP}", flush=True)
    HTTPServer(("127.0.0.1", PORT), H).serve_forever()