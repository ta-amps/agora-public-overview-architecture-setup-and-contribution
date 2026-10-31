# Providers, harnesses and compute

Observed October 29, 2026. A harness runs the worker's tool loop; a provider
supplies model inference; a training worker updates model weights. Access to one
does not establish access to the others. The [status report](status.md) separates
merged source, deployed versions, local observations and remaining work.

## Protocols and responsibility

| Component | Role and supported direction | Boundary |
| --- | --- | --- |
| OpenAI | Herma Responses adapter | API credentials and allowance are separate from a signed-in ChatGPT/Codex session |
| Anthropic | Herma Messages adapter | Claude Code subscription authentication is not an Anthropic backend API key |
| Ollama Cloud | Native chat provider; Messages compatibility exercised by the Claude fixture | Cloud inference access does not supply training GPUs or model-weight rights |
| Muse / Meta | Meta model provider and a separate native harness family | Record both harness and exact requested/reported model; do not silently substitute models |
| OpenRouter | Explicit Chat Completions gateway | Pin the model and underlying provider; no hidden gateway fallback, presets or automatic routing |
| Jev / TypeSafe | Worker-side typed System One decision adapter | Typed state/questions, not a generative-chat fallback; no live qualification |
| Claude Code, OpenCode, Pi, Muse Code, nanoMuse, Hermes and OpenClaw | Native harnesses with distinct versions and tool integrations | A passing fixture does not qualify every provider, feature or workflow |

Herma's [provider and conversation contracts](https://github.com/ta-amps/herma-infrastructure-shim-for-intelligent-agents/blob/main/docs/conversations.md)
own wire protocols and configuration. The ordinary shim preserves supported
caller generation settings, including an omitted output limit. An explicitly
enabled server conversation capability requires its own declared allowance;
that spending reservation is not a universal harness response ceiling.

Reusable assets must be nouns and independently schedulable work must be verbs.
Surfaces expose them; seed packs bundle them. Limited infrastructure retains its
explicit scope rather than creating another work authority. Ordinary research,
planning, generation and review belong to authorized workers.
Server-side inference requires a scoped exception with purpose, principal, data,
provider/model, destination, payer, allowance, deadline and retry policy.
Provider plans are private nouns; they do not create authority. Deterministic
selection must satisfy both the caller's plan and the operator's allowlist.
Persist attempts before dispatch and retain each requested/reported model,
outcome and usage. Unknown usage stays unknown, with its reservation retained.
Storage, scope, coordination and caller/global budget failures must stop. A known
per-provider budget denial may advance only to another explicitly permitted,
independently budgeted provider; it never creates extra allowance.
Deterministic actions record `model: null` and their parent attempt where captured.

These contracts cover explicit capabilities. They do not establish complete
attribution for every older embedding, routing or demo path. Legacy migration,
general shim admission/activation/rollback and the OpenMuse TypeScript connector
remain separate work.

## Observed inference and native coverage

These observations use synthetic inputs and specific fixtures. Local Herma
calling a real provider is different from a deployed Herma test or a native
harness completing a Tessera verb.

| October 29 observation | Result | Limit |
| --- | --- | --- |
| Local Herma → OpenAI Responses | `gpt-6-luna` completed the bounded typed-conversation check | One provider/model fixture; no broad reliability claim |
| Local Herma → Anthropic | Original HTTP 400 retained; a later diagnostic attempt reported credit or quota exhaustion | No successful inference; operator-funded calls are temporarily paused |
| Local Herma → OpenRouter | Original HTTP 404 retained; a later diagnostic attempt reported no eligible provider endpoint | Exact exclusion constraint remains unknown; operator-funded calls are temporarily paused |
| Native Claude Code → Ollama | Local actual-workerd lifecycle passed; six provider calls | Does not prove native Anthropic subscription availability |
| Native Pi → Ollama | Local actual-workerd lifecycle passed; seven provider calls | One workload and configuration |
| Native Muse Code → Meta | Local actual-workerd lifecycle passed; twelve provider calls | One workload and configuration |
| Jev | Adapter and validation work only | No live call or inference qualification |

Read-only authentication probes are distinct from these inference observations.
The original failures remain unresolved in their original receipts. A later
diagnostic run recorded only bounded, allowlisted error metadata and retained
unknown-usage reservations. The OpenRouter diagnosis does not establish a credit
failure: it reports endpoint eligibility, with the precise constraint unknown.

The operator separately requested a temporary Anthropic/OpenRouter pause for
credit/budget reasons. This is an operating decision, not an independently
verified balance. Their adapters and configuration remain available.
Herma's managed conversations share limit state across callers under a stable
operator account identity. They honor provider retry/reset guidance, use increasing
backoff when guidance is absent, and admit one recovery request after cooldown.
That request must be fresh, already authorized and within its existing allowance;
there is no background probe or replay of the failed turn. Uncertain charged
outcomes keep their reservations and require the existing uncertainty grants.

`HERMA_CONVERSATION_DISABLED_PROVIDERS` separately pauses operator-funded managed
conversations and native proxy traffic that would use an operator fallback key
for a recognized provider origin. Explicit caller-owned proxy credentials retain
their own authorization and limits. Clearing the manual pause does not erase
automatic health state. The proxy gains no automatic retry or provider rotation.
Legacy embedding and micro-routing paths still need their own migration evidence.
The [status report](status.md) identifies tested source and deployment limits;
configuration in source alone does not establish hosted enforcement. Jev remains
unqualified and makes no live calls.

The health migration adds fields to existing coordinator tables. Its documented
recovery procedure stops new conversations and rolls forward with the capability
disabled; older writers cannot simply resume against the expanded tables. Keep
health and allowance records. Separate deployments do not automatically share
provider-account health.

The accounting follow-up checks the selected credential before reserving any
allowance. Accepted but unfinished responses retain unknown outcomes and their
reservations. The managed one-proposal profile rejects unpriced multiple outputs,
opaque stored prompts and unsupported pricing overrides; it fixes OpenAI to the
standard `default` tier and Anthropic to `standard_only`. Receipts distinguish
planned ceilings, confirmed reservations and uncertain shared-budget calls.
These request-body changes have offline verification only. The earlier live
OpenAI success belongs to its recorded source and request, not this newer body.
Operator provider and uncertainty grants remain deployment-wide; separate
per-principal purchase grants are not implemented. None of these settings grants
new inference or spending authority.

The earlier native matrix also completed scoped work with OpenCode, Hermes,
nanoMuse and OpenClaw. Ten separate Pi processes and 100 logical protocol clients
are different scale tests. See [swarm readiness](swarm-readiness.md) for their
limits. Tessera's subsequent hosted recovery has separate release and smoke
evidence in the status report. The new Herma code remains undeployed.

## Training hardware and service boundaries

| Execution environment | Useful role | Observed or required boundary |
| --- | --- | --- |
| CPU worker | Deterministic data preparation and tiny adapter smoke | Actual local smoke completed; unsuitable evidence for a large-model training claim |
| RTX 3060 worker | Small CUDA specialist LoRA experiments | Completed tiny smoke plus pretrained Llama 3.2 1B and 3B continuous tuning rounds on synthetic unseen-family tool calls (`12.0% -> 50.7%` on 1B and `52.0% -> 72.7%` on 3B in bf16 LoRA within ~11.62 GiB VRAM); useful-task evaluation and admission remain unrun |
| Kaggle notebook | Bounded free 2x T4 GPU QLoRA training environment | Completed Muse Glimmer 30B 4-bit QLoRA specialist run across Kaggle's two free 16 GB T4 GPUs (`93.3% -> 99.3%` exact match on pre-registered 150-row synthetic fresh holdout); adapter stays private and unadmitted; availability and allowance must be checked for each run |
| H100 worker | Optional single-GPU Glimmer QLoRA environment | Official single-H100 recipe exists; unprovisioned and not needed after the free 2x T4 QLoRA run succeeded |
| Cloudflare Workers | Authorization, storage access, receipts and job coordination | The service runtime is not the optional PyTorch/CUDA trainer |
| Cloudflare Workers AI | Inference with supported base models and compatible adapters | Adapter compatibility must be checked; no Glimmer serving qualification |

Kaggle documents two T4 GPUs with 16 GB each. Their memories are separate, not
an automatic 32 GB pool. A multi-GPU recipe needs its own implementation and
measurement, as recorded in the [Muse Glimmer 30B 2xT4 QLoRA bundle](../evidence/glimmer-30b-2026-10-29/README.md). Account quota is not reserved capacity or permission to create a
permanent inference service. [Kaggle accelerator announcement](https://www.kaggle.com/discussions/product-announcements/735239).

Workers AI documents uploaded-adapter inference and an external notebook
training workflow. Check its current supported models, artifact format, size
and rank restrictions before proposing deployment. A generic fine-tune endpoint
does not establish arbitrary GPU training or compatibility with this adapter.
[Workers AI LoRA support](https://developers.cloudflare.com/workers-ai/features/fine-tunes/loras/),
[training tutorial](https://developers.cloudflare.com/workers-ai/guides/tutorials/fine-tune-models-with-autotrain/).

The [fine-tuning page](fine-tuning-pilot.md) links the October 29 CPU/GPU smoke, while [training/README.md](../training/README.md), [eval/README.md](../eval/README.md) and the [Glimmer 30B run record](../evidence/glimmer-30b-2026-10-29/README.md) record the completed synthetic LoRA and QLoRA specialist runs. Training, inference,
model access and artifact admission each need their own evidence and authority.

## OpenAI subscriber API-credit offer

OpenAI announced this benefit on October 28; the official guide was checked on
October 29. Eligible Pro tiers receive $100, $200 or $500 monthly API credits.
Business receives $20 per paid Standard seat or $100 per paid Premium seat,
subject to a $500 workspace monthly cap. Annual Business grants cover the annual
cycle. [Announcement](https://developers.openai.com/api/docs/changelog),
[official credit guide](https://developers.openai.com/api/docs/guides/chatgpt-api-credits).

Eligibility requires an active paid subscription at least seven days old,
ownership of the subscription/workspace and receiving API organization, matching
account email, and activation of the link. Unused credits expire with their
billing cycle. The benefit covers supported API usage such as Responses; it
does not cover API-key Codex use or increase signed-in ChatGPT/Codex limits.
[Eligibility and coverage](https://developers.openai.com/api/docs/guides/chatgpt-api-credits).

An offer, a valid key and a successful inference call establish different facts.
This guide makes no claim about anyone's activated balance or entitlement.
Credits do not authorize unrelated spending, GPU rental or broader data access.
Before a real run, establish its allowed data, model, payer and budget and measure
cost against the selected provider's current rates.
