# PostgreSQL via Neon (active demo backend)

Neon is a serverless Postgres host with a generous free tier. The actual
demo's `DATABASE_URL` points at Neon because OCI Always Free Ampere
capacity is exhausted in our region. The OCI Terraform under `infra/oci/`
remains in the repo as the IaC-capability proof; once OCI capacity opens,
swap `DATABASE_URL` and the application code is unchanged (server-mediated
pattern is host-agnostic).

## Setup (~3 min)

### 1. Create a Neon project
1. https://console.neon.tech/signup → **Sign in with GitHub**
2. **Create project**:
   - Project name: `medassist`
   - Postgres version: 16
   - Region: **Europe (Frankfurt)** (matches Auth0 + HF Space latency)
   - Database name: `medassist`
3. Copy the **Connection string** Neon shows on the next screen. Looks like:
   ```
   postgresql://medassist_owner:xxxxx@ep-xxx.eu-central-1.aws.neon.tech/medassist?sslmode=require
   ```
   This is your `DATABASE_URL`.

### 2. Apply the schema
Two options:

**Option A — Neon SQL Editor (browser, no install needed):**
1. Neon dashboard → **SQL Editor** (left sidebar)
2. Paste the contents of `db/schema.sql`
3. Click **Run**
4. Should see: `CREATE TABLE` × 2, `CREATE INDEX` × 2

**Option B — `psql` from your machine:**
```powershell
psql "<connection-string>" -f db/schema.sql
```

### 3. Wire it up
Add as HuggingFace Space secret:
- Name: `DATABASE_URL`
- Value: the Neon connection string

The HF Space auto-restarts on secret change. After ~30s the user-data
endpoints come online.

### 4. Smoke-test
```bash
curl -i https://catalinbutacu-med-assist.hf.space/user/profile
```
Expect **`401 Unauthorized`** — JWT auth is wired and rejecting the
anonymous request. That's the success state.

## Why Neon (the CV-friendly summary)

- **Serverless Postgres** — autoscale-to-zero, no idle compute charges
- **Same Postgres 16** as our OCI Terraform target — schema portable
- **Branchable databases** (per-PR DB copies) — production-quality dev workflow
- **No client-side credentials** — only the FastAPI on HF Space talks to Neon, gated by Auth0 JWT verification

## Free-tier limits (Neon)
- 0.5 GB storage (more than enough for tens of thousands of cabinet items)
- 191 compute hours/month — auto-resumes on first query
- No card required for signup
