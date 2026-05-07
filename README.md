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

# 💊 Med Assist

Romanian pharmacy-triage chatbot grounded on the **official ANMDM nomenclator**
(7,555 authorized human-use drugs). Streams replies in Romanian, recommends
only from retrieved evidence, routes emergencies to 112 via deterministic rules
the LLM cannot override.

## Architecture

```
React SPA (GitHub Pages)
   │  Authorization: Bearer <Auth0 access token>
   ▼
FastAPI on HuggingFace Space  ── verifies JWT vs Auth0 JWKS ──
   │
   │  psycopg over SSL
   ▼
PostgreSQL 16 (serverless, Frankfurt)
```

## Engineering choices worth pointing at

- **Hybrid retrieval** — FAISS dense + BM25 sparse fused with RRF. Catches
  semantic queries (*„mă dor articulațiile dimineața"*) and brand-name lookups
  (*„Aspenter 75"*) that one retriever alone misses.
- **Rules-first safety layer** — 17 hand-authored red-flag rules scan every
  user turn before the LLM. Emergency phrases short-circuit to a 112 card.
  **0% false-negative emergency rate** on the eval set.
- **Confidence-gated orchestration** — followup-questioning while the
  classifier is uncertain, recommendation once retrieval is coherent, hard
  cap at 5 followups. Profile-aware prompting skips questions answered in
  the user's stored profile.
- **Grounded recommendation** — LLM may only mention drug names from the
  retrieved evidence list. Contraindication-aware via profile (gastrită →
  off ibuprofen, sarcină → off teratogens).
- **Server-mediated DB pattern** — frontend never sees DB credentials.
  FastAPI verifies Auth0 JWTs (RS256/JWKS) and uses the verified `sub`
  for every DB op; this structurally prevents leaked-key attacks.
- **Vision OCR for cabinet** — Gemini Vision extracts trade name + expiration
  date from a phone photo, matched back to ANMDM via the sparse retriever.

## Eval (`python -m med_assist.cli.eval`)

| Metric | Value |
|---|---|
| Triage accuracy | 93.9% |
| False-negative emergency rate | **0%** |
| Retrieval recall@5 | 89.7% |
| MRR | 0.71 |
| p95 retrieval latency | 88 ms |

## Layout

```
src/                React + Vite + TS · pages, hooks, components/ui, services
med_assist/         FastAPI · api, auth (JWT), db (SQLAlchemy), conversation,
                    retrieval, triage, llm (Gemini chat + vision), eval
infra/oci/          Terraform + cloud-init for Postgres 16 on OCI Ampere VM
db/schema.sql       Postgres DDL
data_acquisition/   ANMDM scraper + RCP parser
```

> The active demo runs against **Neon** (serverless Postgres free tier).
> `infra/oci/` is a complete IaC recipe for the same schema on **OCI
> Always-Free Ampere VM** — switching is a one-line `DATABASE_URL` change.

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 · PyJWT · sentence-transformers · faiss-cpu · rank-bm25 · Gemini 3 Flash + Vision · React + Vite + TS · TailwindCSS · Auth0 · HuggingFace Spaces · GitHub Pages · GitHub Actions (CodeQL + Quality gates) · Terraform (OCI)

## Disclaimer

Educational project, not medical advice. Dial **112** for Romanian emergencies.

## License

MIT
