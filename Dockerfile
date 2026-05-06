# Multi-stage build for med_assist on HuggingFace Spaces (Docker SDK).
#
# Stage 1 (builder) installs Python deps + bakes the FAISS+BM25 index
# from the ANMDM xlsx that's already committed. The first deploy ships
# a reduced corpus (no per-medicine RCP clinical text) — the 1.5 GB
# of regulatory PDFs is gitignored and would blow up the container.
# To upgrade later, host medicines_enriched.json on HF Hub and pull
# during build instead of running 06_enrich.py with --allow-missing-rcp.
#
# Stage 2 (runtime) is slim: only the built artifacts + minimal Python
# deps. Excludes torch C++ libs that were only needed at index time —
# but in practice we keep them, since `sentence-transformers` is
# imported at runtime by the dense retriever to encode user queries.

FROM python:3.12-slim AS builder

WORKDIR /build

# System deps for faiss / torch wheels + curl for fetching binary corpus
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

# Source + plain-text data are COPYed from the build context.
COPY data_acquisition/processed/medicines_anmdm.json data_acquisition/processed/medicines_anmdm.json
COPY data_acquisition/scripts/ data_acquisition/scripts/
COPY med_assist/ med_assist/

# Binary inputs are fetched from the public GitHub repo at build time.
# HF Spaces' Xet storage rejects unwrapped binaries (.xlsx, .gz) on
# git push, so we keep them out of the deploy snapshot entirely and
# pull them here. Pinned to `main`; rebuild the Space to pick up new
# corpus snapshots that land on main.
ARG GH_REPO=CatalinButacu/General-Medical-Assistant
ARG GH_REF=main
RUN mkdir -p data_acquisition/raw data_acquisition/processed && \
    curl -fsSL -o data_acquisition/raw/anmdm_nomenclator.xlsx \
        "https://raw.githubusercontent.com/${GH_REPO}/${GH_REF}/data_acquisition/raw/anmdm_nomenclator.xlsx" && \
    curl -fsSL -o data_acquisition/processed/pdf_links.json \
        "https://raw.githubusercontent.com/${GH_REPO}/${GH_REF}/data_acquisition/processed/pdf_links.json"

# Re-derive the enriched corpus from the committed xlsx + pdf_links.
# `--allow-missing-rcp` produces a slimmer corpus (lay-summary chunks
# only, no RCP body text) since rcp_parsed.json isn't bundled.
RUN python data_acquisition/scripts/06_enrich.py --allow-missing-rcp

# Build FAISS+BM25 indices. Downloads the multilingual MiniLM model
# (~480 MB) once at build time and bakes it + the encoded vectors
# into the image. Slow on CPU (~3-5 min); fine for a one-shot deploy.
RUN python -m med_assist.index.builder

# ─────────────────────────────────────────────────────────────────────

FROM python:3.12-slim

WORKDIR /app

# Pull installed packages from the builder. This includes torch wheels,
# which are needed at runtime to encode the user's query.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Source + bundled artifacts. Everything downstream of /build maps
# 1:1 into /app so relative paths in the source still work.
COPY --from=builder /build/med_assist /app/med_assist
COPY --from=builder /build/data_acquisition /app/data_acquisition

# Cache the SentenceTransformer model so the runtime doesn't re-download.
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

# HF Spaces' default Docker port is 7860; matches app_port in README.
EXPOSE 7860

CMD ["uvicorn", "med_assist.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
