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

## How it works

### Runtime — what happens on each user action

**Chat.** Frontend opens an SSE stream to `POST /chat` with `{messages, profile}`. The orchestrator scans for red flags first; if any fires, it returns an emergency card and the LLM never sees the query. Otherwise it joins the cumulative user turns, runs FAISS+BM25 retrieval, and decides:
- low classifier confidence → ask one targeted followup question (capped at 4)
- coherent retrieval → emit medicine cards + stream a Gemini reply grounded in those cards

**Scanner.** Camera frame → base64 JPEG → `POST /scan`. Backend pipes it to Gemini Vision with a JSON schema → returns trade name, dose, form, expiration. The trade name is matched back to ANMDM via BM25 (with a fallback that strips dose/form noise for partial OCR), top-3 candidates returned. User picks one → frontend prefills the cabinet add form including the OCR'd expiration date.

**Cabinet & profile.** `GET/POST/PUT/DELETE /user/cabinet` and `GET/PUT /user/profile`. The user's `sub` is taken from the verified JWT, never from the request body — a forged `user_id` in JSON cannot reach another user's data.

### Auth + DB security flow

A request to `/user/*`:

1. Frontend's `useUserApi()` hook calls Auth0's `getAccessTokenSilently()` → JWT (RS256, signed by Auth0).
2. Sent as `Authorization: Bearer <jwt>`.
3. FastAPI's `current_user_sub` dependency verifies signature against JWKS (cached in-process), checks `iss` / `aud` / `exp`, returns the `sub` claim.
4. The route handler queries Postgres scoped by `user_id == sub` via SQLAlchemy.

The DB connection string lives only as an HF Space secret (server-side). Nothing in the browser bundle can reach Postgres directly — by design, not by hope.

### Deployment pipelines (GitHub Actions on `main`)

| Workflow | Trigger | What it does |
|---|---|---|
| `deploy.yml` | push to main | Vite build with `VITE_*` envs from secrets → upload `dist/` → publish to GitHub Pages |
| `deploy-hf.yml` | push to main | Orphan-snapshot (drops binaries — HF Xet rejects them; Dockerfile re-fetches via curl) → force-push to the HF Space's git repo → HF rebuilds the Docker image |
| `quality.yml` | push + PR | ESLint + tsc, Ruff + Pytest. No `continue-on-error` — broken types or red tests block the merge |
| `codeql.yml` | push + PR + weekly | `security-and-quality` queries for python and javascript-typescript |

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
