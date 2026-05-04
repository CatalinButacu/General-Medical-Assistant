---
title: Med Assist
emoji: 💊
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8000
pinned: false
license: mit
short_description: Romanian RAG triage chatbot over the ANMDM medicine nomenclator
---

# 💊 Med Assist — Romanian Pharmacy Triage Chatbot

> **Educational demo only.** Information here is NOT medical advice. Always consult a pharmacist or doctor.

Conversational triage + recommendation over the official ANMDM nomenclator
(7,555 authorized human-use medicines in Romania). Streams in Romanian via
Gemini 3 Flash, grounded on retrieval that won't let the model invent drug
names. Red-flag rules short-circuit emergencies straight to 112 — the LLM
is never in the safety path.

## 🏗️ Architecture

```
src/                       React + Vite + TypeScript frontend (GitHub Pages)
med_assist/                Python backend
├── api/main.py            FastAPI: /health /manifest /chat /scan
├── conversation.py        triage → followup-gating → retrieval → Gemini stream
├── service.py             RetrievalService.advise() — fusion + classifier
├── retrieval/             dense (FAISS+MiniLM) · sparse (BM25) · RRF · rerank
├── triage/                17 red-flag rules + three-way classifier
├── llm/                   Gemini chat (text) + Gemini Vision (camera scan)
├── eval/                  49-case golden set + metrics (recall@k, MRR, FN-emerg)
├── index/builder.py       builds FAISS+BM25 from chunks
└── data/                  Medicine + Chunk dataclasses
data_acquisition/          ANMDM scraper + RCP parser + auto-update orchestrator
```

## 🚀 Deployment

| Surface | Where | How |
|---|---|---|
| Frontend | GitHub Pages (`gh-pages` branch) | `.github/workflows/deploy.yml` builds + deploys on push to `main` |
| Backend | HuggingFace Space (Docker SDK) | `.github/workflows/deploy-hf.yml` mirrors repo to `huggingface.co/spaces/USER/SPACE` on push to `main` |

Set these GitHub repo secrets to enable CI:
- `VITE_BACKEND_URL` — public HF Space URL, e.g. `https://your-user-med-assist.hf.space`
- `HF_TOKEN` — HuggingFace write token from <https://huggingface.co/settings/tokens>
- `HF_USERNAME`, `HF_SPACE` — Space owner + name

Set this HF Space secret (Settings → Variables and secrets):
- `GOOGLE_API_KEY` — Gemini API key from <https://aistudio.google.com/apikey>

## 💻 Local development

Backend:
```bash
pip install -r requirements.txt
python data_acquisition/scripts/01_parse_anmdm.py
python data_acquisition/scripts/06_enrich.py --allow-missing-rcp
python -m med_assist.index.builder
uvicorn med_assist.api.main:app --port 8000 --reload
```

Frontend:
```bash
cp .env.example .env.local           # set VITE_BACKEND_URL=http://localhost:8000
npm install
npm run dev
```

`.env.local` is auto-loaded by FastAPI on startup — no shell sourcing needed.

## 📊 Eval

```bash
python -m med_assist.cli.eval
```

49-case Romanian golden set. Current numbers: 93.9% triage accuracy, **0%
false-negative emergency rate**, retrieval recall@5 = 89.7%, p95 latency 88ms.

## ⚠️ Disclaimer

Educational project. Not medical advice. Romanian SMURD: dial **112** for
emergencies; antitox 021 318 36 06; suicidal-ideation TelVerde 0800 801 200.

## 📝 License

MIT
