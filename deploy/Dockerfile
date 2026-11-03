# FoundFact backend + web app + hunch (local EmbeddingGemma 2 student) in one Cloud Run container.
# Build from the repo root:  docker build -f deploy/Dockerfile -t foundfact .   (see deploy/cloudrun.md)
# Keys are NOT baked in: MUSE_API / OPENROUTER_KEY come from Secret Manager at runtime.

# ---- 1. hunch + eg2cpu wheels (eg2cpu is a Rust/PyO3 extension built with maturin) ----
FROM python:3.12-slim AS hunch
ARG HUNCH_REPO=https://github.com/undrgrnd-labs/hunch
ARG HUNCH_REV=6541bd1
RUN apt-get update && apt-get install -y --no-install-recommends git curl build-essential ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
ENV PATH=/root/.cargo/bin:$PATH
RUN git clone "$HUNCH_REPO" /src/hunch && git -C /src/hunch checkout "$HUNCH_REV"
RUN pip install --no-cache-dir "maturin>=1.9,<2" \
 && pip wheel --no-cache-dir --no-deps -w /wheels /src/hunch/eg2cpu /src/hunch/hunch

# ---- 2. runtime ----
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 HF_HOME=/opt/hf PORT=8080 HUNCH_LAYER=12
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv

# Backend deps from the lockfile; CPU-only torch keeps the image ~3 GB smaller than the CUDA build.
COPY backend/pyproject.toml backend/uv.lock backend/
RUN cd backend && uv export --frozen --no-dev --no-hashes --no-emit-project -o /tmp/req.txt \
 && uv pip install --system --no-cache --index-url https://download.pytorch.org/whl/cpu \
      --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match -r /tmp/req.txt

COPY --from=hunch /wheels /wheels
RUN uv pip install --system --no-cache /wheels/*.whl scikit-learn

# Bake the EmbeddingGemma 2 checkpoint (Apache-2.0, not gated) so cold starts don't download 1+ GB.
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('google/embeddinggemma-2')"

COPY backend/app backend/app
COPY shared shared
COPY web web
# Case store + its embedding cache, and the graduated hunch student (WAL checkpointed by
# deploy/prepare.sh before the build). hunch.db holds teacher answers for public posts; it ships in the
# image only, never in git.
COPY data/cases.jsonl data/cases.npy data/cases.npy.meta data/blocklist.tsv data/
COPY data/hunch.db data/hunch.db
COPY deploy/start.sh /app/start.sh

EXPOSE 8080
CMD ["/app/start.sh"]
