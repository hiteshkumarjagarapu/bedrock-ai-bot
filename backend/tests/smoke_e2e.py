"""End-to-end smoke test against a running server: python tests/smoke_e2e.py [base_url]"""
import io
import json
import sys
import time

import httpx
from docx import Document

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8001"
email = f"smoke{int(time.time())}@example.com"

doc = Document()
doc.add_paragraph("Project Aurora is a satellite initiative led by Dr. Mira Castellanos. "
                  "The launch budget is 4.2 million dollars and launch is scheduled for March 2027.")
buf = io.BytesIO()
doc.save(buf)

with httpx.Client(base_url=BASE, timeout=120) as c:
    r = c.post("/auth/register", json={"email": email, "password": "secret123", "name": "Smoke"})
    assert r.status_code == 201, r.text
    h = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert c.post("/auth/login", json={"email": email, "password": "secret123"}).status_code == 200
    assert c.post("/auth/login", json={"email": email, "password": "bad"}).status_code == 401
    assert c.get("/docs/list").status_code == 401

    r = c.post("/docs/upload", headers=h, files={"file": ("aurora.docx", buf.getvalue())})
    print("upload:", r.status_code, r.text)
    assert r.status_code == 201
    doc_id = r.json()["document"]["id"]
    time.sleep(5)  # Pinecone eventual consistency

    for attempt in (1, 2):  # second call should hit Redis cache
        answer, session = "", None
        with c.stream("POST", "/chat", headers=h, json={"query": "Who leads Project Aurora and what is the budget?"}) as s:
            for line in s.iter_lines():
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                ev = json.loads(line[6:])
                if ev["type"] == "token":
                    answer += ev["content"]
                elif ev["type"] == "session":
                    session = ev["session_id"]
                elif ev["type"] == "error":
                    raise SystemExit(f"chat error: {ev['message']}")
        print(f"chat #{attempt}:", answer)
        assert "Castellanos" in answer

    hist = c.get(f"/chat/history/{session}", headers=h).json()
    assert len(hist["messages"]) == 2, hist
    assert c.delete(f"/docs/{doc_id}", headers=h).status_code == 204
    assert c.get("/docs/list", headers=h).json() == []
print("SMOKE OK")
