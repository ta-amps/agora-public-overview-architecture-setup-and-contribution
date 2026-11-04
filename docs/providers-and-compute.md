# Providers, harnesses and compute

Observed October 29, 2026. A harness runs the worker's tool loop; a provider
supplies model inference; a training worker updates model weights. Access to one
does not establish access to the others. The [status report](status.md) separates
merged source, deployed versions, local observations and remaining work.

## Protocols and responsibility

| Component | Role and supported direction | Boundary |
| --- | --- | --- |
| Other providers | The Teleion Fabric shim works with almost any model and LLM inference provider | Pin the model and provider. A provider's API key and allowance are separate from a signed-in subscription |
| Muse / Meta | Meta model provider and a separate native harness family | Record both harness and exact requested/reported model; do not silently substitute models |
| Jev / TypeSafe | Worker-side typed System One decision adapter | Typed state/questions, not a generative-chat fallback; no live qualification |
| Claude Code, OpenCode, Pi, Muse Code, nanoMuse, Hermes and OpenClaw | Native harnesses with distinct versions and tool integrations | A passing fixture does not qualify every provider, feature or workflow |

the Teleion Fabric shim's [provider and conversation contracts](https://github.com/ta-amps/herma-infrastructure-shim-for-intelligent-agents/blob/main/docs/conversations.md)
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

These observations use made-up inputs and specific fixtures. Local the Teleion Fabric shim
calling a real provider is different from a deployed the Teleion Fabric shim test or a native
harness completing a Teleion Fabric verb.

| October 29 observation | Result | Limit |
| --- | --- | --- |
| Native Claude Code and Pi on another model | Local actual-workerd lifecycle passed; six and seven provider calls | One workload and configuration each |
| Native Muse Code → Meta | Local actual-workerd lifecycle passed; twelve provider calls | One workload and configuration |
| Jev | Adapter and validation work only | No live call or inference qualification |

Read-only authentication probes are distinct from these inference observations.
Some provider routes are paused for credit and budget reasons. This is an operating decision, not an independently checked balance. Their adapters and configuration remain available.
The Teleion Fabric shim's managed conversations share limit state across callers under a stable
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
opaque stored prompts and unsupported pricing overrides; it fixes each provider to
its standard tier. Records distinguish
planned ceilings, checked reservations and uncertain shared-budget calls.
These request-body changes have offline verification only.
Operator provider and uncertainty grants remain deployment-wide; separate
per-principal purchase grants are not implemented. None of these settings grants
new inference or spending authority.

The earlier native matrix also completed scoped work with OpenCode, Hermes,
nanoMuse and OpenClaw. Ten separate Pi processes and 100 logical protocol clients
are different scale tests. See [swarm readiness](swarm-readiness.md) for their
limits. Teleion Fabric's subsequent hosted recovery has separate release and smoke
evidence in the status report. The new the Teleion Fabric shim code remains undeployed.

## Training hardware and service boundaries

| Execution environment | Useful role | Observed or required boundary |
| --- | --- | --- |
| CPU worker | Deterministic data preparation and tiny adapter smoke | Actual local smoke completed; unsuitable evidence for a large-model training claim |
| RTX 3060 worker | Small CUDA specialist LoRA experiments | Completed tiny smoke plus pretrained Meta's open-weight 1B and 3B models: continuous tuning rounds on made-up unseen-family tool calls (`12.0% -> 50.7%` on 1B and `52.0% -> 72.7%` on 3B in bf16 LoRA within ~11.62 GiB VRAM); useful-task evaluation and admission remain unrun |
| Kaggle notebook | Bounded free 2x T4 GPU QLoRA training environment | Completed Muse Glimmer 30B 4-bit QLoRA specialist run across Kaggle's two free 16 GB T4 GPUs (`93.3% -> 99.3%` exact match on pre-registered 150-row made-up fresh holdout); adapter stays private and unadmitted; availability and allowance must be checked for each run |
| H100 worker | Optional single-GPU Glimmer QLoRA environment | Official single-H100 recipe exists; unprovisioned and not needed after the free 2x T4 QLoRA run succeeded |
| Cloudflare Workers | Authorization, storage access, records and job coordination | The service runtime is not the optional PyTorch/CUDA trainer |
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

The [fine-tuning page](fine-tuning-pilot.md) links the October 29 CPU/GPU smoke, while [training/README.md](../training/README.md), [eval/README.md](../eval/README.md) and the [Glimmer 30B run record](../evidence/glimmer-30b-2026-10-29/README.md) record the completed made-up LoRA and QLoRA specialist runs. Training, inference,
model access and artifact admission each need their own evidence and authority.

Before a real run, establish its allowed data, model, payer and budget and measure
cost against the selected provider's current rates.
