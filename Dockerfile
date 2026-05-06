FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -r requirements.txt

COPY data_acquisition/processed/medicines_anmdm.json data_acquisition/processed/medicines_anmdm.json
COPY data_acquisition/scripts/ data_acquisition/scripts/
COPY med_assist/ med_assist/

# Binaries pulled from GitHub raw; HF Xet rejects committed binaries.
ARG GH_REPO=CatalinButacu/General-Medical-Assistant
ARG GH_REF=main
RUN mkdir -p data_acquisition/raw data_acquisition/processed && \
    curl -fsSL -o data_acquisition/raw/anmdm_nomenclator.xlsx \
        "https://raw.githubusercontent.com/${GH_REPO}/${GH_REF}/data_acquisition/raw/anmdm_nomenclator.xlsx" && \
    curl -fsSL -o data_acquisition/processed/pdf_links.json \
        "https://raw.githubusercontent.com/${GH_REPO}/${GH_REF}/data_acquisition/processed/pdf_links.json"

RUN python data_acquisition/scripts/06_enrich.py --allow-missing-rcp
RUN python -m med_assist.index.builder

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /build/med_assist /app/med_assist
COPY --from=builder /build/data_acquisition /app/data_acquisition
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_DISABLE_SYMLINKS_WARNING=1

EXPOSE 7860

CMD ["uvicorn", "med_assist.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
