# ── Stage 1: base image with TF + CUDA support ───────────────────────────────
# Switch to tensorflow/tensorflow:2.17.0-gpu for GPU inference
FROM tensorflow/tensorflow:2.17.0 AS base

WORKDIR /app

# System dependencies for Pillow & OpenCV (future)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
        libgomp1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ── Stage 2: dependencies ─────────────────────────────────────────────────────
FROM base AS deps

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ── Stage 3: final image ──────────────────────────────────────────────────────
FROM deps AS final

# Copy application source
COPY app/ ./app/

# Model files are volume-mounted at runtime (see docker-compose.yml)
# Placeholder to document expected location
RUN mkdir -p app/models/ml

# Reduce TF verbosity at container startup
ENV TF_CPP_MIN_LOG_LEVEL=2
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

# Single worker — TF holds GPU context per process.
# Scale horizontally via container replicas, not --workers.
CMD ["uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--log-level", "warning"]
