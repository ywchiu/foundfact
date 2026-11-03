# Deploying FoundFact to Cloud Run

One container serves the web app (`/`), the API (`/screen`, `/verify`, `/providers`, `/privacy`) and the hunch
proxy (internal, port 8765). Deploying creates a public URL that spends Muse credits — check the daily budget
(`DAILY_BUDGET_USD`, default 15) before you do it.

## 1. Prepare data (local)

```bash
# stop `hunch serve` first, then:
deploy/prepare.sh            # checkpoints data/hunch.db, checks cases.npy exists
```

## 2. Secrets (once)

```bash
gcloud config set project <PROJECT>
gcloud services enable run.googleapis.com cloudbuild.googleapis.com secretmanager.googleapis.com artifactregistry.googleapis.com
printf %s "$MUSE_API"       | gcloud secrets create muse-api       --data-file=-
printf %s "$OPENROUTER_KEY" | gcloud secrets create openrouter-key --data-file=-
```

## 3. Build

eg2cpu compiles Rust; building amd64 on an Apple Silicon Mac under emulation is slow, so build in Cloud Build:

```bash
gcloud artifacts repositories create foundfact --repository-format=docker --location=asia-east1   # once
gcloud builds submit --region=asia-east1 --machine-type=e2-highcpu-8 \
  --tag asia-east1-docker.pkg.dev/<PROJECT>/foundfact/app:latest \
  --config=<(printf 'steps:\n- name: gcr.io/cloud-builders/docker\n  args: [build, -f, deploy/Dockerfile, -t, asia-east1-docker.pkg.dev/<PROJECT>/foundfact/app:latest, .]\nimages: [asia-east1-docker.pkg.dev/<PROJECT>/foundfact/app:latest]\n')
```

(Locally with Docker running: `docker build --platform linux/amd64 -f deploy/Dockerfile -t foundfact .`)

## 4. Deploy

```bash
gcloud run deploy foundfact --region=asia-east1 \
  --image asia-east1-docker.pkg.dev/<PROJECT>/foundfact/app:latest \
  --cpu 4 --memory 8Gi --min-instances 1 --max-instances 3 --concurrency 40 \
  --no-cpu-throttling --timeout 300 --allow-unauthenticated \
  --set-secrets MUSE_API=muse-api:latest,OPENROUTER_KEY=openrouter-key:latest \
  --set-env-vars DAILY_BUDGET_USD=15,VERIFY_PER_IP_HOUR=10
```

- `--no-cpu-throttling`: hunch runs as a background process; with request-only CPU it would stall between requests.
- `--min-instances 1`: the EmbeddingGemma 2 load takes ~20 s; keep one warm for judges.
- The rate limiter, budget guard and result cache are in-process, so the effective per-IP limit is
  `VERIFY_PER_IP_HOUR × instances`. Fine for a demo; move them to Redis/Memorystore for real traffic.
- hunch keeps learning from Muse answers inside the container, but that state is lost on restart (the baked
  `hunch.db` is the floor).

## 5. Smoke test

```bash
URL=$(gcloud run services describe foundfact --region=asia-east1 --format='value(status.url)')
curl -s $URL/health; curl -s $URL/providers
curl -s -X POST $URL/screen -H 'content-type: application/json' \
  -d '{"provider":"local","posts":[{"id":"t1","platform":"facebook","text":"今天去爬山，天氣很好"}]}'
```

Then open `$URL`, run the three examples, and check that the 11th `/verify` from one IP within an hour gets 429
and that `DAILY_BUDGET_USD=0` gives 503.

## 6. Extension pointing at the public backend

```bash
bash extension/build.sh --release "$URL"     # writes dist/foundfact.zip
```

`manifest.json` already allows `https://*.run.app/*`; a custom domain needs a new host permission.
