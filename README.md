---
title: Med Assist
emoji: 💊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
license: mit
short_description: Romanian RAG triage chatbot over ANMDM medicines
---

# 💊 Med Assist — Romanian Pharmacy Triage Chatbot

> Educational portfolio project. Not medical advice.

A grounded RAG assistant over the **official Romanian ANMDM medicine
nomenclator** (7,555 authorized human-use drugs). Streams replies in
Romanian, recommends only from retrieved evidence, and routes emergencies
to 112 via a deterministic rule layer that the LLM cannot override.

**Live**: frontend on GitHub Pages · backend on a HuggingFace Space (Docker SDK).

## What this project demonstrates

End-to-end ML engineering on a real-world corpus, not a toy dataset:

- **Hybrid retrieval** — dense (FAISS + multilingual MiniLM) **+** sparse
  (BM25 over Romanian-tokenized chunks), fused with Reciprocal Rank Fusion.
  Catches both semantic queries (*"mă dor articulațiile dimineața"*) and
  brand-name lookups (*"Aspenter 75"*) that one retriever alone misses.
- **Rules-first safety layer** — 17 hand-authored red-flag rules scan every
  user turn before the LLM sees it. Emergency phrases (chest pain, anaphylaxis,
  suicidal ideation) short-circuit straight to a 112 card; the LLM is **never**
  in the safety path. 0% false-negative emergency rate on the eval set.
- **Three-way triage classifier** — combines top fused score, score floor of
  relevant hits, and ATC/brand coherence in the top-3 to decide
  `EMERGENCY | OTC_SAFE | UNCERTAIN`. Coherence path catches single-retriever
  wins that the score-only path misses.
- **Adaptive conversational orchestration** — confidence-gated phases:
  followup-questioning while the classifier is uncertain, recommendation
  once retrieval is coherent, hard cap at 5 followups. Profile-aware
  prompting skips questions already answered in the user's stored profile
  (allergies, conditions, pregnancy).
- **Grounded recommendation** — the LLM may only mention drug names from
  the retrieved evidence list. Contraindication-aware: a profile flag for
  "gastrită" steers it off ibuprofen, "graviditate" off teratogens.
- **Vision OCR for medicine cabinet** — Gemini Vision extracts trade name,
  dose, form, and expiration date from a phone photo of a box, then matches
  the trade name back to the ANMDM corpus via the same sparse retriever.

## Architecture

```
React (GitHub Pages)
  │  Authorization: Bearer <Auth0 access token>
  ▼
FastAPI on HuggingFace Space  ──[verifies JWT vs Auth0 JWKS]──
  │
  │  psycopg over SSL
  ▼
PostgreSQL 16 on Oracle Cloud (Always Free Ampere A1)
       provisioned via Terraform + cloud-init
```

```
src/                       React + Vite + TypeScript (GitHub Pages)
├── pages/                  Chat (SSE) · CameraScanner · HealthProfile · MedicineCabinet · Onboarding
├── services/api.ts         /chat (SSE) and /scan (REST) clients
├── services/userApi.ts     /user/profile and /user/cabinet typed clients
├── hooks/useUserApi.ts     auth-aware fetch (auto-attaches Auth0 access token)
├── components/ui/          shared primitives (Button, Card, FormField, Badge)
└── config/auth0.ts         SPA + access token audience config

med_assist/                Python backend (FastAPI on HF Spaces)
├── api/main.py             /health /manifest /chat /scan
├── api/users.py            /user/profile /user/cabinet — auth-required
├── auth/jwt.py             Auth0 JWT verification (RS256, JWKS-cached)
├── db/                     SQLAlchemy 2.0 models + lazy-init engine
├── conversation.py         confidence-gated followup ↔ recommend orchestrator
├── service.py              RetrievalService.advise() — fusion + classifier
├── retrieval/              dense (FAISS+MiniLM) · sparse (BM25) · RRF · rerank
├── triage/                 17 red-flag rules + three-way classifier
├── llm/                    Gemini chat (text) + Gemini Vision (camera scan)
├── eval/                   49-case Romanian golden set + metrics
└── index/builder.py        builds FAISS+BM25 from medicine chunks

infra/oci/                 Terraform — OCI Always-Free Ampere VM + Postgres
├── main.tf, network.tf, compute.tf, outputs.tf
└── cloud-init.yaml         PGDG Postgres 16 install + role/db + schema apply

db/schema.sql              Postgres DDL for health_profiles + cabinet_items
data_acquisition/          ANMDM scraper + RCP parser + auto-update orchestrator
```

## Why these choices

**FAISS + BM25 instead of just dense.** Romanian medical text mixes brand
names (BM25 wins) with lay-language symptom descriptions (dense wins).
Picking one alone leaves a recall gap on the other.

**Rules-first emergency routing instead of asking the LLM.** An LLM that
"usually" routes chest pain correctly is a malpractice incident waiting to
happen. The 17 red-flag rules are deterministic, auditable, and never
hallucinate — at the cost of less natural phrasing on rare cases.

**Confidence-gated phases instead of fixed-turn followups.** Earlier
versions hard-coded a 2-question intake before recommending. Real users
either gave enough on turn 1 (vague "headache" goes nowhere; specific
"sinus pressure 3 days" hits a strong cluster) or kept being vague through
4 turns. Gating on the classifier confidence + a 5-turn cap matches both.

**Docker SDK on HF Spaces, not Gradio.** The backend is a FastAPI service
and Gradio's auto-UI wasn't useful — we have our own React frontend. Docker
gives full control over the build (FAISS index baked at image build time,
~480 MB MiniLM weights cached) at the cost of a longer first-deploy.

## Eval

49-case Romanian golden set, run with `python -m med_assist.cli.eval`:

| Metric | Value |
|---|---|
| Triage accuracy | 93.9% |
| False-negative emergency rate | **0%** |
| Retrieval recall@5 | 89.7% |
| MRR | 0.71 |
| p95 retrieval latency | 88 ms |

## Tech stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy 2.0, psycopg, PyJWT (RS256/JWKS), sentence-transformers, faiss-cpu, rank-bm25, google-genai (Gemini 3 Flash + Vision)
- **Frontend**: React + Vite + TypeScript, TailwindCSS, Auth0 (Google OAuth, access tokens with API audience)
- **Infra**: HuggingFace Spaces (Docker), GitHub Pages, GitHub Actions (CodeQL + orphan-snapshot mirror + GH Pages deploy), **Oracle Cloud Always Free** (Ampere A1 VM + self-managed Postgres 16, provisioned via Terraform)

## Disclaimer

Educational project, not medical advice. Romanian SMURD: dial **112** for
emergencies; antitox 021 318 36 06; suicide-prevention TelVerde 0800 801 200.

## License

MIT
