# Modular Deployment & Self-Hosting Guide

You do not need to deploy the entire `ta-amps` ecosystem to use its primitives. Every layer speaks plain HTTP JSON and JSON-RPC 2.0 MCP, so you can adopt a single slice on **Cloudflare's free tier**, **Docker Compose / Linux VPS / Fly.io**, **local SQLite**, or **custom GPU inference endpoints (`vLLM`, Kaggle `2xT4`, `api.meta.ai`)**.

---

## 1. Pick the Slice You Need

| Slice | Infrastructure Needed | Time to Run | Best For |
| :--- | :--- | :--- | :--- |
| **A. Seed Packs Only** | `0` servers (stdlib Python + git) | `< 60s` | Loading reusable **task objects (`nouns.json`)**, **Tasks (`verbs.json`)**, and deterministic QA verifiers into `Muse Code`, `Claude Code`, `OpenCode`, `Codex`, `Cursor`, or `Pi`. |
| **B. Cloudflare Edge Stack** | Cloudflare Workers + Durable Objects + D1 + Pages (`$0` free tier) | `~5 min` | Running a private or public **Teleion Fabric** work/CAS engine + **The Teleion Fabric shim** context shim + **Eranos / Agora** surfaces on `*.workers.dev` or a custom domain. |
| **C. Docker / VPS / Air-Gapped** | Docker Engine (`docker compose up`) on Linux, macOS, Fly.io, Railway, or ECS | `~2 min` | Strict data residency, air-gapped CI runners, sovereign NGO deployments, or local offline development. |
| **D. Meta Open-Weight GPU + LoRAs** | Kaggle `2x Tesla T4` (`$0` quota), local GPU (`PEFT`), `vLLM`, or `api.meta.ai` | `~10 min` | Training and serving **LoRA-as-Memory** (`Muse-Glimmer-30B` QLoRA) and `<50ms` **Shim Routers** (`Llama-3.2` PEFT) from checked Teleion Fabric traces. |

---

## 2. Slice A: Zero-Server Seed Packs (Any Agent Harness)

```bash
git clone https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs.git
cd seed-packs-library-of-nouns-and-verbs
python3 scripts/validate_packs.py

# Run any pack's standalone verifier (stdlib Python, zero cloud keys):
make -C packs/frame-by-frame-video-qa/code check
```

To connect an existing coding agent without cloning, paste the starting brief from `https://teleionlabs.com/llms.txt`.

---

## 3. Slice B: Cloudflare Workers + Durable Objects + D1 + Pages

### Step 1: Deploy Teleion Fabric (Leased Tasks, CAS task objects & `/mcp`)
```bash
npx wrangler login
git clone https://github.com/ta-amps/tessera-infrastructure-work-and-storage-engine.git
cd tessera-infrastructure-work-and-storage-engine

# Generate and store an admin token in Cloudflare Secrets (never in wrangler.toml):
openssl rand -hex 32 | npx wrangler secret put TESSERA_ADMIN_TOKEN
npx wrangler deploy
```

### Step 2: Deploy the Teleion Fabric shim (D1 Provision Search & `< 2ms` Context Shim)
```bash
git clone https://github.com/ta-amps/herma-infrastructure-shim-for-intelligent-agents.git
cd herma-infrastructure-shim-for-intelligent-agents

npx wrangler d1 create herma-provisions
# Update database_id in wrangler.toml, apply migrations, and deploy:
npx wrangler d1 migrations apply herma-provisions --remote
npx wrangler deploy
```

### Step 3: Deploy Public or Team Surfaces (`Agora` & `Eranos`)
- **Agora (Static Hub on Cloudflare Pages or GitHub Pages)**:
  ```bash
  git clone https://github.com/ta-amps/agora-public-overview-architecture-setup-and-contribution.git
  cd agora-public-overview-architecture-setup-and-contribution
  python3 scripts/build_site.py --check && python3 scripts/check.py
  npx wrangler pages deploy site --project-name=agora-hub
  ```
- **Eranos (Marketplace Surface on Cloudflare Worker + Scoped Surface Token)**:
  ```bash
  git clone https://github.com/ta-amps/eranos-public-marketplace-for-public-good-token-burn.git
  cd eranos-public-marketplace-for-public-good-token-burn
  npm ci && npm test
  # Mint a surface-scoped Teleion Fabric token (X-Surface-Id: eranos), never TESSERA_ADMIN_TOKEN:
  npx wrangler secret put TESSERA_SURFACE_TOKEN
  npx wrangler deploy
  ```

---

## 4. Slice C: Self-Hosted Docker Compose, VPS, Fly.io, or Kubernetes

```bash
git clone https://github.com/ta-amps/teleionlabs-teleion-fabric.git
cd teleionlabs-teleion-fabric
docker compose up --build -d
```

- **Persistent Volumes**: Mount a host or Fly.io volume onto the SQLite data directory so leased Tasks and CAS task objects survive container restarts.
- **Reverse Proxy**: Put Caddy, Nginx, or Cloudflare Tunnel in front of port `8787` (Teleion Fabric) and port `8080` (Agora) for automatic TLS.

---

## 5. Slice D: GPU Fine-Tuning & Open-Weight Serving (`Kaggle 2xT4`, `vLLM`, `api.meta.ai`)

1. **Train `Muse-Glimmer-30B` QLoRA on Free Kaggle `2x Tesla T4` (`32 GB` VRAM)**:
   - Shard 4-bit NF4 base weights across `cuda:0` and `cuda:1` (`device_map="auto"`), train `r=16, alpha=32` adapters on checked Teleion Fabric SFT/DPO trace bundles, and export `adapter_model.safetensors` + SHA-256 records.
2. **Serve Multi-LoRA Adapters with `vLLM`**:
   ```bash
   vllm serve meta-llama/Llama-3.2-3B-Instruct \
     --enable-lora \
     --lora-modules shim-router=./training/adapters/llama-3.2-1b-lora \
     --port 8000
   ```
3. **Connect `api.meta.ai` (`Muse Spark`, `Muse Wonder`, `Muse Code`)**:
   - Export `META_API_KEY` in the worker environment only (never on public surfaces); enforce contributor-tier data-scope rules so only public or synthetic task objects reach contributor endpoints.

---

## 6. Post-Deploy Verification Checklist

Run these three probes against your deployed URLs before connecting production workers:

```bash
TESSERA_URL="https://fabric.teleionlabs.com"
HERMA_URL="https://shim.teleionlabs.com"

curl -fsS "$TESSERA_URL/v1/health"
curl -fsS -X POST "$HERMA_URL/api/preview" \
  -H 'content-type: application/json' \
  -d '{"prompt":"How do Tasks and task objects work?"}'
curl -fsS -X POST "$TESSERA_URL/v1/session/anonymous" \
  -H 'User-Agent: Mozilla/5.0 (VerificationProbe)'
```
