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
only from retrieved evidence, routes emergencies to 112 via deterministic
rules the LLM cannot override.

| Capability | Number |
|---|---|
| Indexed medicines | 7,555 |
| Triage accuracy (49-case golden set) | 93.9% |
| False-negative emergency rate | **0%** |
| Retrieval recall@5 | 89.7% |
| MRR | 0.71 |
| p95 retrieval latency | 88 ms |

## 🏆 LLM Zoomcamp Peer Review Checklist

> 🎓 **DataTalksClub LLM Zoomcamp Capstone Project Submission**  
> Below is the explicit mapping of this project to the 8 official evaluation rubric criteria to simplify peer reviewing:

| # | Evaluation Criteria | Implementation Details & Code Links |
| :-: | :--- | :--- |
| **1** | **Problem Description** | Romanian pharmacy-triage chatbot grounded on official ANMDM nomenclator (7,555 drugs). See [Architecture](#architecture). |
| **2** | **Ingestion Pipeline** | Automated acquisition & enrichment in [`data_acquisition/scripts/06_enrich.py`](data_acquisition/scripts/06_enrich.py) and index builder in [`med_assist/index/builder.py`](med_assist/index/builder.py). |
| **3** | **Retrieval Flow** | Hybrid search (FAISS dense vector + BM25 keyword search) with Reciprocal Rank Fusion (RRF) and confidence thresholding. See [`med_assist/retrieval/hybrid.py`](med_assist/retrieval/hybrid.py). |
| **4** | **Retrieval Evaluation** | Automated evaluation CLI (`python -m med_assist.cli.eval`). Results: **Recall@5 = 89.7%**, **MRR = 0.71**. Includes Reranker A/B comparison. See [`med_assist/cli/eval.py`](med_assist/cli/eval.py). |
| **5** | **LLM Evaluation** | 49-case Romanian golden set evaluation with LLM-as-a-Judge faithfulness scoring (`--faithfulness`). **Triage accuracy = 93.9%**, **0% false-negative emergency rate**. |
| **6** | **Interface** | Interactive React 19 + Vite SPA frontend ([`src/`](src/)) with FastAPI SSE streaming backend ([`med_assist/api/`](med_assist/api/)). |
| **7** | **Monitoring & Logging** | PostgreSQL persistence for `chat_sessions`, `chat_messages`, and user health profiles ([`med_assist/db/`](med_assist/db/)) + optional Langfuse tracing ([`med_assist/observability.py`](med_assist/observability.py)). |
| **8** | **Reproducibility & Docker** | Containerized via [`Dockerfile`](Dockerfile), pinned dependencies in [`requirements.txt`](requirements.txt), and `.env.example` setup. See [Local Development](#local-development). |

## Architecture

```
┌──────────────────────────┐    Bearer JWT    ┌──────────────────────────┐
│  React SPA               │  ─────────────►  │  FastAPI                 │
│  GitHub Pages            │                  │  HuggingFace Space       │
│  (Auth0 SDK,             │                  │  (Docker, port 7860)     │
│   localStorage session)  │                  │                          │
└──────────────────────────┘                  │  - JWT verify (JWKS)     │
       ▲                                      │  - Rate limit + req-IDs  │
       │                                      │  - Retrieval (FAISS+BM25)│
       │ login                                │  - Triage rules          │
       ▼                                      │  - Gemini chat + Vision  │
┌──────────────────────────┐                  └──────────────────────────┘
│  Auth0                   │                            │
│  - SPA app               │                            │ psycopg + SSL
│  - "Med Assist API"      │                            ▼
│  - JWKS endpoint         │                  ┌──────────────────────────┐
└──────────────────────────┘                  │  Postgres 16 (Neon)      │
                                              │  - health_profiles       │
                                              │  - cabinet_items         │
                                              │  - chat_sessions         │
                                              │  - chat_messages         │
                                              └──────────────────────────┘
```

The frontend never talks to Postgres directly. Every authenticated request
goes through FastAPI, which verifies the Bearer token against Auth0's signing
keys before touching the DB.

## Tech stack

Python 3.12 · FastAPI · SQLAlchemy 2.0 · PyJWT · sentence-transformers · faiss-cpu · rank-bm25 · Gemini 3 Flash + Vision · React 19 + Vite + TS · TailwindCSS · Auth0 · HuggingFace Spaces · GitHub Pages · GitHub Actions (CodeQL + Quality + Eval) · Terraform (OCI)

## Runtime workflows

### Login + onboarding

1. User clicks **Login** on the home page → Auth0 SDK calls `loginWithRedirect()` with `audience=https://med-assist-api`.
2. Auth0 hosts the Google login form. After auth, user returns with an authorization code in the URL.
3. SDK exchanges code for an access token (RS256-signed JWT, contains `sub`, `aud`, `iss`, `exp`) + refresh token. Both stored in localStorage (`useRefreshTokens: true`).
4. `Home.tsx` mounts a `useEffect` that calls `GET /user/profile`. Backend returns either the existing profile or a default with `onboarded: false`.
5. If `!profile.onboarded`, frontend redirects to `/onboarding` (3-step wizard: name+age+gender → pregnancy → allergies/conditions/medications).
6. On finish, `PUT /user/profile` saves to Postgres with `onboarded: true`. Future sessions skip the wizard.

### Chat

Frontend opens an SSE stream to `POST /chat` with `{ messages, profile }`. The orchestrator:

1. **Red-flag scan** on the latest user turn. Any emergency or urgent rule fires → emit a single `triage` event with `label: EMERGENCY` and short-circuit. The LLM never sees emergency-class queries.
2. **Cumulative retrieval** — concatenate all user turns into one query, run hybrid FAISS+BM25 with reciprocal rank fusion. Classifier returns `OTC_SAFE | UNCERTAIN` plus a confidence score.
3. **Phase decision** — `MIN_FOLLOWUPS_WITH_PROFILE = 2`, `MIN_FOLLOWUPS_NO_PROFILE = 2`, `MAX_FOLLOWUPS = 4`:
   - `user_turns < min_followups` → followup, ask one targeted question
   - `OTC_SAFE` and `confidence ≥ 0.5` → recommend, emit medicine cards + stream a grounded Gemini reply
   - `user_turns ≥ 4` (cap) without confidence → recommend with empty evidence, LLM gracefully refuses and suggests pharmacist
   - else → followup, keep gathering
4. **Category-driven first-question override** — if retrieval lands in `Alergii`, the first followup is hard-coded to ask about the trigger (food/pollen/drug/contact) instead of letting the LLM pick. Prevents recommending an antihistamine for an unknown trigger that might be anaphylactic.
5. **Stream** — Gemini 3 Flash with `thinking_budget=0` so reasoning tokens don't eat the visible output. Each chunk arrives as a `token` SSE event; frontend accumulates them into the assistant message and renders triage badge + medicine cards as their events fire.

#### Chat UX surfaces

The frontend layers five interaction patterns on top of the SSE stream to keep the followup loop from feeling like an interrogation:

- **Quick-query bar** — `Sugestii rapide` chevron above the composer expands a 2-col chip grid of starter prompts (paracetamol, tuse, alergie, …). Hidden in the welcome state (the bigger inline grid handles that) and while streaming. Persistent across turns so the starter prompts don't vanish after the first message.
- **Suggested-reply chips on followups** — Followup questions are matched against priority regex rules in `src/lib/suggestedReplies.ts` (one rule per question type in `followup.ro.j2`): `de cât timp` → time-bucket chips, `declanșat` → trigger chips, `unde + doare` → body-region chips, etc. Diacritic-folded match. No protocol change, no extra LLM call. Falls back to free-text typing whenever the regex doesn't match.
- **`Profil aplicat` header pill** — Small purple `ShieldCheck` pill in the chat header when the loaded profile has meaningful data (pregnancy / allergies / conditions / medications). Mirrors the backend's `UserProfile.has_meaningful_data()` so the pill is honest about what the orchestrator actually considers. Tap → `/profile`.
- **Post-recommend follow-up chips** — After a recommend/explain reply lands, four chips appear at the bottom of the assistant bubble: `Cât timp?`, `Cu altceva?`, `Efecte adverse?`, `Alternative?`. Gated by `citation_valid != null` so they don't appear on followup or emergency phases.
- **`Sari direct la sugestii` escape** — On followup bubbles after `user_turn_count >= 2`, an amber button skips the followup loop. Sends `skip_followups=true` to `POST /chat`; the orchestrator flips `in_followup_phase` off and takes the recommend branch with whatever signal it has (low-confidence recommend template). Safety gates (red-flag scan, intent classification) still run — the flag only affects the clarifying-question loop, never emergency routing.

### Scanner

1. User opens `/scanner`, grants camera permission. The `MediaStream` is attached to a `<video>` element via `useEffect` (must wait until the element is mounted before setting `srcObject`).
2. Capture button: canvas draws the current video frame, exports as base64 JPEG.
3. `POST /scan` with `{ image_base64, mime_type }`. Backend pipes the image to Gemini Vision with a JSON-schema response — returns `{ trade_name, expiration_date, dosage, form, confidence, all_text }`.
4. Backend matches the OCR'd `trade_name` against ANMDM titles via BM25. If the score is weak, retries with dose/form noise stripped (`"PARACETAMOL ZENTIVA 500MG"` → `"PARACETAMOL ZENTIVA"`). If still weak, falls back to multi-word tokens from the full OCR dump. Returns top-3 candidates plus the raw OCR for transparency.
5. Frontend shows the best match + alternatives. User picks one → navigates to `/cabinet` with state pre-filled (including the OCR'd expiration date).

### Chat history (auth'd users only)

- Sessions auto-save: every user message creates the session if needed and persists. Every assistant reply is persisted on stream `done`.
- Header has a **+** (start new session) and **clock** (open drawer) button.
- Drawer lists past sessions ordered by `updated_at`, with title (auto-derived from first user turn, ≤80 chars), message count, and timestamp.
- Click a row → loads the session into the chat view. Click trash → confirm-then-delete; cascades all messages.
- `/chat` itself stays stateless and unauthenticated — anonymous chats are ephemeral. Persistence is purely the frontend's responsibility once it has a token.

### Cabinet + profile

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/user/profile` | Load profile; used for chat context and onboarding-redirect check |
| `PUT` | `/user/profile` | Save profile from onboarding or HealthProfile page |
| `GET` | `/user/cabinet` | List user's cabinet items, ordered by expiration date |
| `POST` | `/user/cabinet` | Add a new item |
| `PUT` | `/user/cabinet/{id}` | Edit |
| `DELETE` | `/user/cabinet/{id}` | Remove |
| `POST` | `/user/chats` | Create a chat session |
| `GET` | `/user/chats` | List sessions (with `message_count`) |
| `GET` | `/user/chats/{id}` | Session + ordered messages |
| `POST` | `/user/chats/{id}/messages` | Append a `{role, text}` message |
| `DELETE` | `/user/chats/{id}` | Drop session + cascade messages |
| `POST` | `/chat` | SSE stream: triage / medicines / token / done / error events |
| `POST` | `/scan` | OCR a medicine box (Gemini Vision) and match to ANMDM |
| `GET`  | `/health` | Liveness probe |
| `GET`  | `/manifest` | Index manifest (counts, embedding dim, build time) |

The user's `sub` is **never** sent in the JSON body — it's always extracted from the verified JWT. A forged `user_id` in a request body cannot reach another user's data.

## Auth + DB security flow

A request to any `/user/*` endpoint:

1. Frontend's `useUserApi()` hook calls Auth0's `getAccessTokenSilently()` → returns the cached or silently-refreshed JWT.
2. Request goes out with `Authorization: Bearer <jwt>`.
3. FastAPI's `current_user_sub()` dependency:
   - Decodes the JWT header → extracts `kid`
   - Fetches JWKS from `https://{AUTH0_DOMAIN}/.well-known/jwks.json` (cached in-process via `@lru_cache`)
   - Finds the public key matching `kid`, verifies the RS256 signature
   - Verifies `iss`, `aud`, `exp`
   - Returns `payload["sub"]`
4. Any failed check → 401. Otherwise the route handler runs with `sub: str` injected.
5. SQLAlchemy queries scope every read/write by `user_id == sub`.

The DB connection string lives only as an HF Space secret. The browser bundle is published to GitHub Pages — anything baked at build time (`VITE_BACKEND_URL`, `VITE_AUTH0_DOMAIN`, `VITE_AUTH0_CLIENT_ID`, `VITE_AUTH0_AUDIENCE`) is public by design. Nothing in the bundle can reach Postgres directly.

## Production hardening

Beyond auth, three middleware-level concerns run on every request:

- **Rate limiting** (`api/ratelimit.py`) — in-memory token bucket per `X-Forwarded-For` IP. `/chat` capped at 30/min (burst 10), `/scan` at 10/min (burst 3). Returns `429` with `Retry-After` header.
- **Request IDs** (`api/middleware.py`) — every request gets a 12-char UUID, returned as `X-Request-ID`. Honored if the client sends one, otherwise generated. Injected into every `LogRecord` via `setLogRecordFactory` so `docker logs | grep req=abcd1234e5f6` traces the full lifecycle of one request.
- **Structured access log** — one line per request: `13:42:07 [INFO] req=a3f1b2c4d5e6 medassist.access: POST /chat -> 200 (412.3 ms)`. Logger names are namespaced `medassist.{api,auth,chat,vision,llm,access,ratelimit,tracing}` — grep-stable across module renames.

## Tracing (optional)

Per-turn traces light up in [Langfuse](https://langfuse.com) when three env vars are set: `LANGFUSE_HOST`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` (free-tier cloud or self-hosted both work). `med_assist/observability.py` exposes an `@observe` decorator applied to the hot path:

- `IntentClassifier.classify` — routing decision (label, confidence, matched terms).
- `RetrievalService.advise` and `match_by_name` — query, hits, score.
- `GeminiClient.stream` — system prompt, contents, model, token output (typed as a `generation` span).
- `VisionClient.extract_medicine` — OCR input shape and the structured `VisionExtraction` result.

The decorator is a no-op when `langfuse` isn't installed or the env vars are unset, so dev and CI pay zero cost. The orchestration is unchanged: this is observability, not an agent layer. The agent-design research note in this branch documents why a LangGraph migration is deferred until the project genuinely needs the model to choose between tools.

## CI/CD

Five workflows fire from `main`:

### `deploy.yml` — "Deploy frontend" (push to main, GitHub Pages)
Checkout → `npm ci` → `npm run check` (tsc) → `npm run build` (Vite). Build env injects `VITE_*` from secrets. Upload `dist/` as Pages artifact, deploy via `actions/deploy-pages@v4`.

### `deploy-hf.yml` — "Deploy backend" (push to main, HuggingFace Space)
1. Checkout main, build an **orphan branch** (`hf-deploy`) — single fresh commit, no history.
2. Delete binaries (`anmdm_nomenclator.xlsx`, `pdf_links.json`) — HF rejects committed binaries via Xet storage. The Dockerfile re-fetches them from `raw.githubusercontent.com` at build time.
3. Force-push the orphan to `main` of `huggingface.co/spaces/catalinbutacu/med-assist` using `HF_TOKEN`.
4. HF detects the push, rebuilds the Docker image (~5–8 min): `pip install` → `06_enrich.py` → `med_assist.index.builder` → multi-stage runtime image.
5. Container starts, FastAPI binds 7860, health probe goes green.

### `quality.yml` — "Quality" (push + PR)
- **Frontend job:** `npm run lint` (ESLint, no errors allowed) + `npm run check` (`tsc --noEmit`).
- **Backend job:** install ruff + pytest + minimal deps → `ruff check med_assist/ data_acquisition/scripts/` → `pytest med_assist/tests/`.

No `continue-on-error` — broken types or red tests block the merge.

### `eval.yml` — "Eval" (`workflow_dispatch` only)
Manual trigger from the Actions tab. Builds the corpus + index from scratch, runs `python -m med_assist.cli.eval` against the 49-case Romanian golden set, uploads `eval-results.json` and a markdown summary as artifacts.

Two boolean inputs on the dispatch form:

| Input | Default | When to flip on |
|---|---|---|
| `measure_rerank` | `false` | Whenever you've touched the retrieval pipeline (fusion, rerank, BM25, dense encoder, chunker). Runs the eval twice — once with `RERANK_ENABLED=true`, once `=false` — then diffs every metric. The job summary shows the rerank delta on accuracy, recall@k, MRR, context_precision@k, and p95 latency. Use this to keep the rerank earning its inference cost. |
| `with_faithfulness` | `false` | When the orchestrator, prompt templates, or retrieval pipeline changed. Runs the LLM-as-judge faithfulness pass — ~2 extra Gemini calls per OTC_SAFE case (~100 calls on the 49-case set, several minutes + quota). Skip for unrelated changes; the deterministic metrics already catch most regressions. |

### `codeql.yml` — "CodeQL" (push + PR + weekly)
`security-and-quality` query suites for `javascript-typescript` and `python`. Findings appear in **Security → Code scanning**. Repo-level branch protection blocks merges on High+ severity.

## Local development

Backend:
```bash
pip install -r requirements.txt
python data_acquisition/scripts/01_parse_anmdm.py    # one-time
python data_acquisition/scripts/06_enrich.py --allow-missing-rcp
python -m med_assist.index.builder                   # builds FAISS+BM25
uvicorn med_assist.api.main:app --port 8000 --reload
```

Frontend (separate terminal):
```bash
npm install
npm run dev -- --host 0.0.0.0    # --host so phone can connect over WiFi
```

`.env.local` provides `GOOGLE_API_KEY` (server) + the `VITE_*` envs (client). FastAPI auto-loads it via `python-dotenv` on startup.

DB schema:
```bash
psql "$DATABASE_URL" -f db/schema.sql   # idempotent — safe to re-run
```

Tests:
```bash
python -m pytest med_assist/tests/ -q   # all tests run against in-memory SQLite
```

## Project layout

```
General-Medical-Assistant/
├── README.md                           ← this file
├── Dockerfile                          ← multi-stage HF Space image
├── requirements.txt                    ← Python deps
├── package.json                        ← frontend deps + scripts
├── vite.config.ts, tsconfig.json       ← Vite + TS config
├── eslint.config.js                    ← ESLint flat config
│
├── src/                                ← React frontend
│   ├── App.tsx, main.tsx               ← root + router
│   ├── config/auth0.ts                 ← Auth0 SDK config (audience pinned)
│   ├── components/
│   │   ├── AuthGuard.tsx               ← redirects to /login if no token
│   │   ├── MobileNavigation.tsx        ← bottom tab bar
│   │   └── ui/{Button,FormField}.tsx   ← typed primitives
│   ├── hooks/
│   │   ├── useUserApi.ts               ← fetch wrapper that injects Bearer
│   │   └── useChatHistory.ts           ← session list + persist + load
│   ├── pages/
│   │   ├── Home.tsx                    ← landing + onboarding redirect
│   │   ├── Onboarding.tsx              ← 3-step wizard
│   │   ├── HealthProfile.tsx           ← profile editor + safety check
│   │   ├── Chat.tsx                    ← SSE chat + history drawer
│   │   ├── CameraScanner.tsx           ← video capture + /scan
│   │   └── MedicineCabinet.tsx         ← cabinet CRUD UI
│   ├── services/
│   │   ├── api.ts                      ← /chat, /scan, /health, /manifest
│   │   └── userApi.ts                  ← /user/* DTOs + path constants
│   ├── types/index.ts                  ← shared DTO types
│   └── lib/utils.ts                    ← cn() classname helper
│
├── med_assist/                         ← FastAPI backend (Python package)
│   ├── api/
│   │   ├── main.py                     ← FastAPI app + lifecycle
│   │   ├── users.py                    ← /user/profile + /user/cabinet
│   │   ├── chats.py                    ← /user/chats + messages
│   │   ├── middleware.py               ← RequestIDMiddleware + log factory
│   │   └── ratelimit.py                ← TokenBucketLimiter + dependency
│   ├── auth/jwt.py                     ← Auth0 JWKS verification
│   ├── db/
│   │   ├── models.py                   ← SQLAlchemy 2.0 declarative
│   │   └── session.py                  ← engine + session factory
│   ├── conversation.py                 ← orchestrator (red-flag→retrieve→phase)
│   ├── llm/
│   │   ├── client.py                   ← Gemini chat (streaming)
│   │   ├── vision.py                   ← Gemini Vision OCR
│   │   └── prompts.py                  ← Romanian system prompts
│   ├── retrieval/                      ← FAISS dense + BM25 sparse + RRF fusion
│   ├── triage/
│   │   ├── redflags.py                 ← 17 deterministic emergency rules
│   │   └── classifier.py               ← OTC_SAFE | UNCERTAIN decision
│   ├── data/                           ← models + chunker + loader
│   ├── service.py                      ← RetrievalService (advise + scan match)
│   ├── index/builder.py                ← rebuild FAISS + BM25 indices
│   ├── eval/                           ← golden-set runner + metrics
│   ├── cli/{advise,eval}.py            ← `python -m` entrypoints
│   └── tests/                          ← pytest suite
│
├── data_acquisition/                   ← ANMDM scraper + RCP parser
│   ├── scripts/                        ← 01_parse_anmdm → 06_enrich
│   └── processed/                      ← built corpus (gitignored)
│
├── db/schema.sql                       ← Postgres DDL (idempotent)
│
├── infra/oci/                          ← Terraform + cloud-init for OCI
│                                         (capacity-deferred, Neon active)
│
└── .github/workflows/
    ├── deploy.yml                      ← "Deploy frontend"
    ├── deploy-hf.yml                   ← "Deploy backend"
    ├── quality.yml                     ← "Quality"
    ├── eval.yml                        ← "Eval" (manual)
    └── codeql.yml                      ← "CodeQL"
```

## Database

The active demo runs against **Neon** (serverless Postgres free tier, Frankfurt). Schema in `db/schema.sql`:

| Table | Purpose | PK |
|---|---|---|
| `health_profiles` | one row per Auth0 `sub` — age, gender, allergies (JSONB), conditions, medications, onboarded flag | `user_id` |
| `cabinet_items` | medicines the user owns — name, expiration_date, quantity | `id (UUID)` |
| `chat_sessions` | one row per saved conversation | `id (UUID)` |
| `chat_messages` | role + text, ordered by `created_at`, FK to session | `id (UUID)` |
| `triage_audit_log` | one row per `/chat` turn — input + retrieved context + rule fired + output + citation_valid. Forensic / EU AI Act compliance store; see [docs/REGULATORY.md](docs/REGULATORY.md). | `id (UUID)` |

`infra/oci/` is a complete Terraform recipe for the same schema on **OCI Always-Free Ampere VM** — switching is a one-line `DATABASE_URL` change. The network layer applied cleanly in production; the compute half hit Always-Free capacity exhaustion in Frankfurt and was deferred. Kept in repo as IaC capability proof.

## Eval

49-case Romanian golden set covering OTC scenarios, ambiguity, profile constraints, and emergency red flags. The headline numbers above come from `python -m med_assist.cli.eval`. To run in CI: open Actions → "Eval" → Run workflow.

Plus 6 pure-Python pytest cases for the red-flag scanner — must-fire (chest pain, anaphylaxis, suicidal ideation), must-not-fire (mild cold, routine headache), and Romanian diacritic robustness.

## Regulatory posture

Symptom-triage chatbots recommending OTC drugs are the borderline case Notified Bodies inspect under MDR 2017/745, and MDR-classified software is automatically high-risk under the EU AI Act (full obligations August 2027). The disclaimer below is *not* a defence — function over labelling. Get a written regulatory opinion before marketing this as anything other than an educational artefact. Concrete checklist + the prompt to send a consultant: [docs/REGULATORY.md](docs/REGULATORY.md).

The audit-log half (Article 12 record-keeping) is implemented in the `triage_audit_log` table — every `/chat` turn writes its input, retrieved context, rule fired, and assistant output for forensic replay.

## Disclaimer

Educational reference implementation, not for clinical use. Dial **112** for Romanian emergencies.

## License

MIT
