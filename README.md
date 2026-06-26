# Prahari — Digital Public Safety Intelligence System

A working, demo-ready prototype that shifts fraud defence from **point of complaint** to
**point of contact** — equipping citizens, banks, and law enforcement with proactive tools to
detect digital-arrest scams, phishing links, voice fraud, and coordinated fraud networks in real time.

Built for the *Digital Public Safety Intelligence* challenge (digital-arrest scams, fraud-network
graph intelligence, geospatial crime mapping, multi-channel citizen shield).

---

## Why this matters

India logged 1.14M cybercrime complaints in 2023; "digital arrest" scams alone defrauded citizens
of ₹1,776 cr in the first nine months of 2024. The gap isn't post-incident evidence — it's
**intelligence before mass victimisation**. Prahari attacks that gap on four fronts at once:
message/voice classification, live session escalation, link safety, and fraud-network graphs,
fused into auditable case files.

---

## Quick start (zero dependencies)

The default server runs on the Python **standard library only** — no install, works fully offline
(a hard requirement for field/edge deployment).

```bash
cd safety_system
python3 -m api.server 8000        # serves API + frontend
# open http://localhost:8000
```

Run the test suite:

```bash
python3 run_tests.py              # 15 checks across all 7 modules
```

### Optional: FastAPI / production ASGI

```bash
pip install -r requirements.txt
uvicorn api.app_fastapi:app --port 8000     # adds OpenAPI docs at /docs
```

---

## The 7 modules

| # | Module | What it does | Tech |
|---|--------|--------------|------|
| 1 | **Scam Detection Engine** | SAFE / SUSPICIOUS / FRAUD with score + explanation. Hinglish/Hindi/English. | TF-IDF (word + char n-grams) + Logistic Regression, fused with a rule-override layer + benign-context guard |
| 2 | **Active Session Detector** | Tracks an ongoing interaction; flags ACTIVE SCAM + severity (LOW/HIGH/CRITICAL) as urgency escalates. | In-memory sliding window (Redis-swappable) |
| 3 | **Fraud Graph Intelligence** | Maps phones/accounts/devices into rings; finds kingpins (PageRank), mules, shared infra. | NetworkX |
| 4 | **Geo Fraud Layer** | Heatmap + ranked hotspots for patrol prioritisation. | Grid-bucket density clustering |
| 5 | **Link Safety Engine** | SAFE / SUSPICIOUS / DANGEROUS for URLs — spoofing, shorteners, bad TLDs, homoglyphs. | Structural heuristics, offline |
| 6 | **Voice Fraud Detection** | REAL / SUSPICIOUS / FRAUD on call transcripts — isolation, fear, authority, payment coercion. | Script-pattern cues + Module 1 |
| 7 | **Case File Generator** | Auditable intelligence package per detection: signals, timeline, graph links, SHA-256 integrity hash. | Deterministic JSON (PDF-ready) |

---

## Measured performance (held-out synthetic eval, 308 messages)

```
Precision 0.928   Recall 1.000   F1 0.963
False-positive rate (overall)         7.8%
False-positive rate (hard "DANGER")   0.6%   <- citizen-facing metric
API latency                           ~2.3 ms/request  (target <500 ms)
```

Recall 1.0 means no fraud slips through; the residual false positives land on the softer
"verify before acting" verdict, while the alarming FRAUD label fires on only 0.6% of safe
messages — the metric that matters for a citizen tool.

---

## API reference

| Method | Endpoint | Body | Returns |
|--------|----------|------|---------|
| POST | `/analyze_message` | `{text}` | risk_level, score, reason, signals, recommended_action |
| POST | `/analyze_session` | `{session_id, text}` | active_scam_session, severity, triggers |
| POST | `/analyze_url` | `{url}` | risk_level, score, signals |
| POST | `/analyze_voice` | `{transcript}` | risk_level, score, signals |
| POST | `/graph/add_interaction` | `{src, dst, type, amount}` | node/edge counts |
| GET  | `/graph/analyze` | — | nodes, edges, clusters, central_nodes |
| GET  | `/geo/analyze` | — | heatmap, hotspots |
| POST | `/case/generate` | `{text?, transcript?, url?, session_id?, subject?}` | full case file |
| POST | `/graph/seed`, `/geo/seed` | — | load synthetic demo data |

---

## Architecture

```
                    ┌──────────────── FRONTEND (single file) ────────────────┐
                    │  Citizen Shield  ·  Command Centre  ·  Live Intercept   │
                    └───────────────────────────┬────────────────────────────┘
                                                 │ REST/JSON
                    ┌────────────────────────────▼────────────────────────────┐
                    │        API LAYER  (stdlib http.server / FastAPI)         │
                    └──┬──────┬──────┬──────┬──────┬──────┬──────┬─────────────┘
                       │      │      │      │      │      │      │
                    ┌──▼─┐ ┌─▼──┐ ┌─▼──┐ ┌─▼──┐ ┌─▼──┐ ┌─▼──┐ ┌─▼────┐
                    │ M1 │ │ M2 │ │ M3 │ │ M4 │ │ M5 │ │ M6 │ │  M7  │
                    │scam│ │sess│ │grph│ │geo │ │link│ │voic│ │ case │
                    └──┬─┘ └──┬─┘ └────┘ └────┘ └────┘ └──┬─┘ └──▲───┘
                       └──────┴───────── shared detector ─┘      │
                                  synthetic data (offline) ──────┘
```

Modular by design (`ml/ graph/ geo/ link/ voice/ casefile/ api/ frontend/`); each module runs
and tests standalone. Swap the in-memory stores for Redis/Neo4j without touching interfaces.

---

## Demo script (90 seconds)

1. **Citizen Shield** — paste a CBI digital-arrest message → instant FRAUD + plain advice; paste a
   real HDFC OTP → SAFE (false-positive guard in action).
2. **Live Intercept** — send the scam sequence; watch severity climb NONE → HIGH → CRITICAL and the
   "telecom + victim alert dispatched" fire *before* money moves.
3. **Command Centre** — Load live intelligence → fraud graph lights up the two kingpins and mules;
   heatmap surfaces Jamtara/Delhi hotspots; one click files an auditable case package.

---

## Production extensions (designed-in, not bolted-on)

- **Redis** session store (interface already isolated in `ml/session.py`).
- **Neo4j** graph backend for cross-jurisdiction scale (NetworkX is the MVP).
- **sentence-transformers** drop-in for the classifier (pipeline keeps the rule layer).
- **Whisper** front-end to feed real audio into Module 6.
- **PDF export** of case files (the dict is already render-ready).
