# Deploying to a small VM (current public site)

The public site runs on a 2 vCPU / 4 GB Ubuntu VM shared with other services, without Docker:

- **No local embedding model.** Known-case matching uses `CASE_MATCHER=jev`
  (`cases.JevCaseStore`: a bigram shortlist, then a Jev "same scam scheme?" judgment), so torch is never
  imported. The process uses about 100 MB.
- **No hunch.** With `HUNCH_URL=` empty, `/providers` reports `local: false`. Stage 1 offers Jev and Muse.
- **systemd unit:** [`foundfact.service`](foundfact.service). It runs uvicorn on 127.0.0.1:8020 with
  `MemoryMax=600M`.
- **nginx** proxies `foundfact.infominer.io` to 127.0.0.1:8020.
  - The DNS record goes through the Cloudflare proxy, with a certbot certificate on the origin.
  - SSE needs `proxy_buffering off`.
  - The real client IP for rate limiting comes from `CF-Connecting-IP`, passed on as `X-Forwarded-For`.

Update:

`/webapps/foundfact` is a git checkout of this repo (`main`). It pushes with a repo-scoped deploy key
(`~/.ssh/foundfact_deploy`, remote `github-foundfact:ywchiu/foundfact.git`). Change, commit and push there,
or pull a change pushed elsewhere, then restart:

```bash
cd /webapps/foundfact
git pull --ff-only                      # or: edit, git commit, git push
(cd backend && uv sync)                 # only when pyproject.toml or uv.lock changed
sudo systemctl restart foundfact
```

Server-only files (`.env`, `api.log`, `.backups/`, `*.bak-*`, `data/cases.npy*`) are ignored through
`.git/info/exclude` and never committed.

`/webapps/foundfact/.env` (mode 600) holds:

- `MUSE_API`
- `MUSE_MODEL=muse-ember-1.0` (since 2026-11-12; the code default is `muse-spark-1.3`)
- `OPENROUTER_KEY`
- `HUNCH_URL=`
- `CASE_MATCHER=jev`
- `DAILY_BUDGET_USD=15`
- `VERIFY_PER_IP_HOUR=3` (10 until 2026-11-12)

## Origin lock (after the final review)

The vhost accepts only Cloudflare's edge ranges, so nobody can reach the origin directly and forge
`CF-Connecting-IP` to dodge the per-IP limit. `/teacher/` is blocked at nginx as well as off in the app
(`TEACHER_ENABLED` unset).

```nginx
# /etc/nginx/snippets/foundfact-cloudflare-only.conf: one "allow <cidr>;" per line from
# https://www.cloudflare.com/ips-v4 and ips-v6, then "allow 127.0.0.1;" and "deny all;"
server {
    include /etc/nginx/snippets/foundfact-cloudflare-only.conf;
    location /teacher/ { return 404; }
    location / { ... }
}
```

Always gate the reload: `sudo nginx -t && sudo systemctl reload nginx`. The box hosts other sites.
