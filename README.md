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

## Architecture

```
┌──────────────────────────┐    Bearer JWT    ┌──────────────────────────┐
│  React SPA               │  ─────────────►  │  FastAPI                 │
│  GitHub Pages            │                  │  HuggingFace Space       │
│  (Auth0 SDK,             │                  │  (Docker, port 7860)     │
│   localStorage session)  │                  │                          │
└──────────────────────────┘                  │  - JWT verify (JWKS)     │
       ▲                                      │  - Retrieval (FAISS+BM25)│
       │                                      │  - Triage rules          │
       │ login                                │  - Gemini chat + Vision  │
       ▼                                      └──────────────────────────┘
┌──────────────────────────┐                            │
│  Auth0                   │                            │ psycopg + SSL
│  - SPA app               │                            ▼
│  - "Med Assist API"      │                  ┌──────────────────────────┐
│  - JWKS endpoint         │                  │  Postgres 16 (Neon)      │
└──────────────────────────┘                  │  - health_profiles       │
                                              │  - cabinet_items         │
                                              └──────────────────────────┘
```

The frontend never talks to Postgres directly. Every authenticated request
goes through FastAPI, which verifies the Bearer token against Auth0's signing
keys before touching the DB.

## Runtime workflows

### Login + onboarding

1. User clicks **Login** on the home page → Auth0 SDK calls `loginWithRedirect()` with `audience=https://med-assist-api`.
2. Auth0 hosts the Google login form. After auth, user returns to `/General-Medical-Assistant/` with an authorization code in the URL.
3. SDK exchanges code for an access token (RS256-signed JWT, contains `sub`, `aud`, `iss`, `exp`) + refresh token. Both stored in localStorage (`useRefreshTokens: true`).
4. `Home.tsx` mounts a `useEffect` that calls `GET /user/profile`. Backend returns either the existing profile or a default with `onboarded: false`.
5. If `!profile.onboarded`, frontend redirects to `/onboarding` (3-step wizard: name+age+gender → pregnancy → allergies/conditions/medications).
6. On finish, `PUT /user/profile` saves to Postgres with `onboarded: true`. Future sessions skip the wizard.

### Chat

Frontend opens an SSE stream to `POST /chat` with `{ messages, profile }`. The orchestrator:

1. **Red-flag scan** on the latest user turn. Any emergency or urgent rule fires → emit a single `triage` event with `label: EMERGENCY` and short-circuit. The LLM never sees emergency-class queries.
2. **Cumulative retrieval**: concatenate all user turns into one query, run hybrid FAISS+BM25 with reciprocal rank fusion, classifier returns `OTC_SAFE | UNCERTAIN` plus a confidence score.
3. **Phase decision**:
   - `user_turns < min_followups` (1 with profile, 2 without) → followup, ask one targeted question
   - `OTC_SAFE` and `confidence ≥ 0.5` → recommend, emit medicine cards + stream a grounded Gemini reply
   - `user_turns ≥ 4` (cap) without confidence → recommend with empty evidence, LLM gracefully refuses and suggests pharmacist
   - else → followup, keep gathering
4. **Stream**: Gemini 3 Flash with `thinking_budget=0` so reasoning tokens don't eat the visible output. Each chunk arrives as a `token` SSE event; frontend accumulates them into the assistant message and renders triage badge + medicine cards as their events fire.

### Scanner

1. User opens `/scanner`, grants camera permission. The `MediaStream` is attached to a `<video>` element via `useEffect` (must wait until the element is mounted before setting `srcObject`).
2. Capture button: canvas draws the current video frame, exports as base64 JPEG.
3. `POST /scan` with `{ image_base64, mime_type }`. Backend pipes the image to Gemini Vision with a JSON-schema response — returns `{ trade_name, expiration_date, dosage, form, confidence }`.
4. Backend matches the OCR'd `trade_name` against ANMDM titles via BM25. If the score is weak, retries with dose/form noise stripped (`"PARACETAMOL ZENTIVA 500MG"` → `"PARACETAMOL ZENTIVA"`). Returns top-3 candidates plus the raw OCR.
5. Frontend shows the best match + alternatives. User picks one → navigates to `/cabinet` with state pre-filled (including the OCR'd expiration date).

### Cabinet + profile

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/user/profile` | Load profile, used for chat context and onboarding-redirect check |
| `PUT` | `/user/profile` | Save profile from onboarding or HealthProfile page |
| `GET` | `/user/cabinet` | List user's cabinet items, ordered by expiration date |
| `POST` | `/user/cabinet` | Add a new item |
| `PUT` | `/user/cabinet/{id}` | Edit |
| `DELETE` | `/user/cabinet/{id}` | Remove |

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

## CI/CD

Four workflows fire from `main`:

### `deploy.yml` — frontend → GitHub Pages
Checkout → `npm ci` → `npm run check` (tsc) → `npm run build` (Vite). Build env injects `VITE_*` from secrets. Upload `dist/` as Pages artifact, deploy via `actions/deploy-pages@v4`.

### `deploy-hf.yml` — backend → HuggingFace Space
1. Checkout main, build an **orphan branch** (`hf-deploy`) — single fresh commit, no history.
2. Delete binaries (`anmdm_nomenclator.xlsx`, `pdf_links.json`) — HF rejects committed binaries via Xet storage. The Dockerfile re-fetches them from `raw.githubusercontent.com` at build time.
3. Force-push the orphan to `main` of `huggingface.co/spaces/catalinbutacu/med-assist` using `HF_TOKEN`.
4. HF detects the push, rebuilds the Docker image (~5–8 min): `pip install` → `06_enrich.py` → `med_assist.index.builder` → multi-stage runtime image.
5. Container starts, FastAPI binds 7860, health probe goes green.

### `quality.yml` — gating checks (push + PR)
- **Frontend job:** `npm run lint` (ESLint, no errors allowed) + `npm run check` (`tsc --noEmit`).
- **Backend job:** install ruff + pytest + minimal deps → `ruff check med_assist/ data_acquisition/scripts/` → `pytest med_assist/tests/`.

No `continue-on-error` — broken types or red tests block the merge.

### `codeql.yml` — security scanning
Push + PR + weekly: `security-and-quality` query suites for `javascript-typescript` and `python`. Findings appear in **Security → Code scanning**. Repo-level branch protection blocks merges on High+ severity.

## Eval (`python -m med_assist.cli.eval`)

49-case Romanian golden set:

| Metric | Value |
|---|---|
| Triage accuracy | 93.9% |
| False-negative emergency rate | **0%** |
| Retrieval recall@5 | 89.7% |
| MRR | 0.71 |
| p95 retrieval latency | 88 ms |

Plus 6 pure-Python pytest cases for the red-flag scanner — must-fire (chest pain, anaphylaxis, suicidal ideation), must-not-fire (mild cold, routine headache), and Romanian diacritic robustness.

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

## Layout

```
src/                React + Vite + TS · pages, hooks, components/ui, services
med_assist/         FastAPI · api, auth (JWT), db (SQLAlchemy), conversation,
                    retrieval, triage, llm (Gemini chat + vision), eval, tests
infra/oci/          Terraform + cloud-init for Postgres 16 on OCI Ampere VM
db/schema.sql       Postgres DDL
data_acquisition/   ANMDM scraper + RCP parser
.github/workflows/  deploy.yml, deploy-hf.yml, quality.yml, codeql.yml
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
