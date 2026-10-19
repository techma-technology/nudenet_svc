# nudenet-svc — AGPL-3.0-or-later (see LICENSE)
FROM python:3.11-slim

ARG SOURCE_URL=""
ARG SOURCE_COMMIT=""
# NudeNet release v3.4-weights, asset 640m.onnx (103,538,690 bytes).
ARG MODEL_ASSET=https://api.github.com/repos/notAI-tech/NudeNet/releases/assets/176832019
ARG MODEL_SHA256=04fe3d77980780c1f8297dc6d7f942fd5b3abe6942a188f742a85241e4f634eb

LABEL org.opencontainers.image.title="nudenet-svc" \
      org.opencontainers.image.description="Stateless HTTP wrapper around NudeNet" \
      org.opencontainers.image.licenses="AGPL-3.0-or-later" \
      org.opencontainers.image.source="${SOURCE_URL}" \
      org.opencontainers.image.revision="${SOURCE_COMMIT}"

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    NUDENET_MODEL_PATH=/models/640m.onnx NUDENET_MODEL_SHA256=${MODEL_SHA256} \
    SOURCE_URL=${SOURCE_URL} SOURCE_COMMIT=${SOURCE_COMMIT}

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Model weights: fetched from the upstream release, checksum pinned.
COPY fetch_model.py .
RUN mkdir -p /models && python fetch_model.py "${MODEL_ASSET}" "${MODEL_SHA256}" /models/640m.onnx

COPY app.py LICENSE README.md COMPLIANCE.md ./
RUN useradd --system --uid 10001 svc
USER svc
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if b'\"ok\":true' in urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=4).read() else 1)"
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--no-access-log"]
