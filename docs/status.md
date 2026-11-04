# Current status

> Note, October 29, 2026, evening: this dated snapshot predates the current model, in which Eranos and Agora are the only public surfaces, Teleion Fabric and the Teleion Fabric shim are infrastructure, Home is not a surface, and everything else is nouns and verbs in seed packs; rows for the three older pack repositories now use plain descriptions, and their URLs stay as source until those repositories are renamed or archived into the [pack library](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs).

> Note, October 30, 2026: the repositories were renamed. Links on this page use their current names, while the table keeps the names observed for this snapshot. The hackathon-context repository and the three older pack repositories were removed after their contents moved, so their rows link to where that content lives now; their commit and CI links stay only as dated source.

> Note, October 30, 2026, 07:09 UTC: after this snapshot, Teleion Fabric was redeployed at 06:53 UTC from [pull request 21](https://github.com/ta-amps/tessera-infrastructure-work-and-storage-engine/pull/21) (merge `edab4d79`, recorded version `63e3b75e`), and Eranos at 06:55 UTC from [pull request 11](https://github.com/ta-amps/eranos-public-marketplace-for-public-good-token-burn/pull/11) (merge `8fe602e9`, recorded version `e34558b8`). Public read-only GETs at 07:09 UTC observed open verbs and self-serve requester keys in Teleion Fabric's access contract, a Teleion Fabric `llms.txt` that names all 37 tools, Eranos's one-box request page, and 14 example kits run on a desktop computer, 5 of them in the hosted catalog. No worker sorts requests on the hosted queues yet, Eranos's page text comes from its build snapshot, and no public end-to-end run is recorded. The tables below are unchanged; the [decks](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/decks/) carry the dated status.

Snapshot reconciled **2026-10-29T19:59:57.770230+00:00**. Exact main and CI were read at
**2026-10-29T19:43:24.521020+00:00**. Other evidence retains its own date and scope.

**Fresh public Teleion Fabric reads passed at 19:54 UTC:** health and instructions
returned HTTP 200, with health `ok:true` and `db_ok:true`. These checks are
separate from the latest recorded concurrent release records for Teleion Fabric PR13
and home. They do not independently identify the executable version or qualify
native artifact/report readback, new learning paths or a completed Frontier cycle.
The earlier quota incident remains historical; the Teleion Fabric shim's new source is undeployed.

## Integrated source

At the dated GitHub observation above, **50 product/support PRs were merged**
across eight repositories, with **zero open PRs** and successful CI at every
exact main revision below. Concurrent work may change this after the observation.
This adds sixteen PRs to the earlier 34: Teleion Fabric 9–13, the Teleion Fabric shim 8–11, Eranos 5,
the older code composition repository 4–5, the older video and motion repository 4
and hackathon-context 2–4. Agora is the ninth repository and provides documentation
and offline validation, with no application runtime.

The [current evidence](../evidence/training-and-community-2026-10-29.json) lists all 50 PR URLs and the new merge
records. [Earlier readiness](../evidence/readiness-2026-10-29.json) and
[integration evidence](../evidence/integration-2026-10-29.json) remain unchanged.
Original dirty development checkouts were preserved. The latest concurrent
Teleion Fabric 12–13, Eranos 5 and hackathon-context 4 merges were observed through
GitHub metadata and CI. Separate concurrent Teleion Fabric 12/13 release packets are
now inspected; their local execution remains attributed reported evidence. The Teleion Fabric shim 11 has the owning and independent source checks
described below. This is a dated cutoff, not continuous monitoring.

| Repository | Main revision | CI at that revision |
| --- | --- | --- |
| [tessera](https://github.com/ta-amps/tessera-infrastructure-work-and-storage-engine) | [`182bcaee`](https://github.com/ta-amps/tessera-infrastructure-work-and-storage-engine/commit/182bcaeec9b0112739360f8778fe855401a16390) | [pass 40940844592](https://github.com/ta-amps/tessera-infrastructure-work-and-storage-engine/actions/runs/40940844592) |
| [exploitation and scam pack, older repository](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs/tree/main/packs/exploitation-evidence) | [`b9f3b409`](https://github.com/ta-amps/shamash/commit/b9f3b409b0b9345ca0f3de3923296f11b65ebc7c) | [pass 40890070406](https://github.com/ta-amps/shamash/actions/runs/40890070406) |
| [eranos](https://github.com/ta-amps/eranos-public-marketplace-for-public-good-token-burn) | [`cea0ee69`](https://github.com/ta-amps/eranos-public-marketplace-for-public-good-token-burn/commit/cea0ee69ef82fc307c4b4e6827c49c91579b3a31) | [pass 40936822893](https://github.com/ta-amps/eranos-public-marketplace-for-public-good-token-burn/actions/runs/40936822893) |
| [herma](https://github.com/ta-amps/herma-infrastructure-shim-for-intelligent-agents) | [`03429c1b`](https://github.com/ta-amps/herma-infrastructure-shim-for-intelligent-agents/commit/03429c1b4c25aa649969ecd56ab0f6856dc8b34f) | [pass 40940519144](https://github.com/ta-amps/herma-infrastructure-shim-for-intelligent-agents/actions/runs/40940519144) |
| [code composition pack, older repository](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs/tree/main/packs/code-composition) | [`6bfee07f`](https://github.com/ta-amps/kothar/commit/6bfee07feb7ed3c7ba9111b0a0678bff5cbf2078) | [pass 40935132204](https://github.com/ta-amps/kothar/actions/runs/40935132204); [pass 40935119870](https://github.com/ta-amps/kothar/actions/runs/40935119870) |
| [video and motion pack, older repository](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs/tree/main/packs/video-motion) | [`9e31c68c`](https://github.com/ta-amps/kinema/commit/9e31c68c321b2acb1f910b9cf5d013b71b38d40d) | [pass 40917939711](https://github.com/ta-amps/kinema/actions/runs/40917939711) |
| [hackathon-context](https://github.com/ta-amps/teleionlabs-teleion-fabric/tree/main/hackathon) | [`7b02420d`](https://github.com/ta-amps/hackathon-context/commit/7b02420d610ea7b174b04d0c6a5014ffd6a05e20) | [pass 40937626114](https://github.com/ta-amps/hackathon-context/actions/runs/40937626114) |
| [pack-contributions](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs) | [`1d01d34d`](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs/commit/1d01d34d39de64b912c43365c9e4b72c5287f93d) | [pass 40899915665](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs/actions/runs/40899915665) |

## Functionality and limits

| Area | Implemented or observed | Remaining boundary |
| --- | --- | --- |
| Teleion Fabric fabric | Scoped nouns/verbs, adaptive claims, leases, CAS, blobs, records, execution reports and recall; uploaded-byte identity fix deployed by a concurrent maintainer | Narrow hosted recovery observed; fresh native artifact/report readback and general category/profile resolution remain open |
| Quota handling | 503/reset guidance and observational timestamp coalescing included in the observed Teleion Fabric release; authorization and per-action audit preserved in local tests | No claim that the code replenished provider capacity or that the live quota failure was reinjected |
| the Teleion Fabric shim | Scoped context, explicit provider protocols/plans, attempt evidence, operator pause and shared managed-conversation recovery; typed worker-side Jev adapter | Accounting guards merged with exact-head/main CI; new source not deployed; changed request fields lack new live qualification; legacy attribution and general shim lifecycle incomplete |
| Execution learning | PR13 reports fingerprints, observation summaries and swappable worker learner specs | Worker observation read is not HTTP-routed; current learners use Python; advisory matching/weights have no demonstrated real-work improvement |
| Training workers | Optional framework-independent data/contract modules and PEFT backend; actual CPU/GPU tiny random-model runs | No pretrained adaptation or demonstrated research-quality improvement |
| Code composition and video and motion packs | Exported 22/8 candidate nouns and three verb seeds each; six real local deterministic executions | No general importer or public admission; test-process worker code is not a native harness |
| Community packs | Six private bundles with 14 noun and 12 verb candidate shapes checked | No installation, import, enqueue, execution or admission; nine external repositories reviewed statically at different depths |
| Research and Opportunity Lab | Pinned research authoring; eleven themes, 21 seed nouns, 22 initial alternative attempts and seven procedure nouns | No mailbox, active feed collector, recurring research scheduler or checked novelty |
| Agent onboarding | Seven recorded copyable starting briefs; 16 historical rendered Firefox cases | Copy grants no credentials; OS clipboard and fresh onboarding against the recovered fabric remain unqualified |
| Exploitation and scam pack / Eranos | Made-up evidence and donated-worker workflows with their existing review boundaries | Made-up coverage; the pack's holds and referrals remain human-only and Eranos requires independent review/steward release |
| Home / Frontier | Recorded home release configures hourly due checks for a 24-hour cycle anchored 13:00 UTC, plus manual runs | Server repair off; 10-minute manual cooldown; no completed hosted daily/manual cycle or fresh home smoke demonstrated |

Follow the [mandatory architecture checkpoint](architecture-checkpoint.md):
only nouns, verbs, surfaces and narrow infrastructure. Eranos and Agora are the
only public surfaces, Teleion Fabric and the Teleion Fabric shim are the infrastructure, and seed packs
bundle everything else as nouns and verbs; projects are labels, not another primitive. Ordinary reasoning belongs
to authorized workers. Documentation guards do not establish universal runtime
migration or grant an effect, provider or spending permission.

## Deployments and the storage incident

The latest recorded concurrent records identify Teleion Fabric PR13 as version
`d9c3326a-9226-40e6-a2dd-2ec74a7ebc0e`, source `182bcaeec9b0112739360f8778fe855401a16390`,
and home as `3a52ee50-34ed-4f21-b213-e78a41f4988b`. Teleion Fabric's recorded `worker.js`
digest is `a4ac49a11f7ea231fb2b7a0ab13f4d29d7477bfb95eff746982962ea32cc1ad2`
(738,785 bytes); home's is `5b08394b9546d7e6908d3c5aa7c9f37ba96f2ca13e385c4b4c936eefae1e0479`
(252,989 bytes). Record/log versions and sizes agree. This review did not rebuild
or download those executables or independently retrieve deployment-created times.
The table records record observations. Five other versions retain historical
parity evidence, and the Teleion Fabric shim's new source is undeployed.

| Worker | Recorded version | Record/parity observation |
| --- | --- | --- |
| [tessera](https://fabric.teleionlabs.com) | `d9c3326a-9226-40e6-a2dd-2ec74a7ebc0e` | 2026-10-29T19:33:16.805970+00:00 |
| [herma](https://shim.teleionlabs.com) | `d711cea9-c465-44d9-aba7-410cd4ae7cb5` | 2026-10-29T15:16:21.739921+00:00 |
| [older exploitation and scam site](https://shamash.ta-amps.workers.dev) | `0e56a982-81e2-419a-b8ea-c8d8b85dbb63` | 2026-10-29T15:16:22.464008+00:00 |
| [eranos](https://eranosforgood.org) | `6fd1e64e-aa4a-481a-8b93-ecbff463eec7` | 2026-10-29T15:16:23.702645+00:00 |
| [older code composition site](https://kothar.ta-amps.workers.dev) | `a768492b-52c9-4b06-b077-d925acde8195` | 2026-10-29T15:16:24.997967+00:00 |
| [older video and motion site](https://kinema.ta-amps.workers.dev) | `b7b784a3-4b46-4792-a3f6-e277602c87e5` | 2026-10-29T15:16:26.061231+00:00 |
| [home](https://teleionlabs.com) | `3a52ee50-34ed-4f21-b213-e78a41f4988b` | 2026-10-29T19:30:40.280249+00:00 |

Teleion Fabric tail recorded `Exceeded allowed rows written in Durable Objects free
tier.` during coordinator initialization on version `7785ff2f-9b47-4fd6-a1e4-fa962f29f11a`.
Discovery/count/admin paths returned HTTP 500 in that historical observation.
The later release includes the mitigation that maps this error to 503 with
retry guidance. Cloudflare's documented daily reset is **00:00 UTC**, but the
subsequent recovery was observed before that next reset. The observation does
not establish that code restored allowance or independently verify billing state.
[Provider allowance/reset documentation](https://developers.cloudflare.com/durable-objects/platform/pricing/).

PR11 and PR12 each have separate **8/8** reported smoke packets: health, agent
card, unauthenticated upload refusal, anonymous session, claimed-hash refusal,
claim, heartbeat and submit. The earlier submission contained no artifact.
PR13 has no distinct postdeployment smoke file, and home has no completed hosted
daily/manual-cycle record. Earlier smoke does not qualify those later versions.

The independent **18:54 UTC** public probe remains historical PR11-era evidence.
A fresh **2026-10-29T19:54:42.222297+00:00** public read observation returned
HTTP 200 from `/v1/health` and `/llms.txt`, with `ok:true`, `db_ok:true` and API
version `0.2.0`. The probe used no authentication, provider call or mutation and
does not independently identify the deployed executable. Fresh native artifact/
execution-report readback, new learning paths and broader operation still need
qualification. No new spending or Contributor-policy authority follows.

The quota fix's local SQLite comparison measured five warm reads: **15** prior
profile timestamp updates versus **0** coalesced updates, with all **five** audit
events retained. Authorization still checks expiry, scope and revocation,
including after claim waiting. These are local logical row counts, not production
usage or billing measurements.

The concurrent PR12 report retains a blob-governance limit: identical bytes within
one namespace still use first-uploader visibility. Per-uploader governance needs
its own migration and scoped tests. This is a reported limitation; the release
implementation was not independently reviewed by this documentation pass.

## Recorded checks

Local counts overlap and must not be summed into an independent-case total.
Earlier local results retain their tested-source scope, including where later
concurrent merges were observed. Exact-main CI was read separately. The table
does not extend earlier local results to those newer commits.

| Repository | Recorded result |
| --- | --- |
| tessera | Concurrent PR13 reports 327 Python passed/6 skipped and 38 workerd tests. Python totals were found in the inspected log;38 is from the PR body. PR12 reports 313/6 and 34 workerd plus32/4 HTTP; earlier counts remain historical. |
| exploitation and scam pack, older repository | 259 tests passed; made-up development cases, adapter conformance (30 passed, 6 skipped), TypeScript and frontend build passed. |
| eranos | 56 tests passed; example verification, adapter conformance (30 passed, 6 skipped), TypeScript and frontend build passed. |
| herma | Accounting source passed 197 Python and 150 Worker checks plus an offline demo/index check; independent review passed 132 Python and 115 Worker checks across 36 unchanged source fingerprints. Counts overlap; exact-head and merged-main CI passed. |
| code composition pack, older repository | Prior source: 42 owning tests plus a local three-task Teleion Fabric integration passed. Concurrent PR5 has independently observed green exact-head/main CI; this reviewer did not rerun its local checks. |
| video and motion pack, older repository | 41 owning tests passed; optional local Teleion Fabric integration separately passed, completing three deterministic worker tasks. |
| hackathon-context | 12 transcription and 13 script tests passed, with public scan, JSON/links and index freshness. Documentation policy is not universal runtime enforcement. |
| pack-contributions | 10 tests, 12 JSON examples, local documentation links and public hygiene passed. |

Teleion Fabric's prior 14 Worker-suite cases include a pure reset-classifier test plus
actual-workerd HTTP/MCP, storage, queued-revocation and authorization cases at
`1276c2bd`. The concurrent release reports 308/6 Python and 17 Worker results
at `49d6e28c`. Later PR12 reports 313/6 and 34 workerd; PR13 reports 327/6 and 38
workerd. Their inspected Python logs support the totals; the PR13 workerd count
comes from its PR body. Main/head CI was read separately. No tests were rerun
by this release review, and no real-work learning improvement was established.
The Teleion Fabric shim's latest offline checks and independent review describe frozen source
`ef704aa1b355bec480203cab87c3010f2d4d3c57`, merged as `03429c1b` with green
exact-head and matching-main CI.
Its 197/150 full and 132/115 focused counts overlap. Prior shared-health checks
were 160/114 at `a3139b42`, with runtime review 94/79 at `10f896ad`; the intervening
change only fixed index portability. Those and the earlier 143/90 and 75/55
observations remain in evidence history.

The Teleion Fabric shim's [earlier CI failure](https://github.com/ta-amps/herma-infrastructure-shim-for-intelligent-agents/actions/runs/40931540528)
was a checkout-name-dependent generated-index mismatch after all runtime tests
passed. The corrected head passed the full suite, an offline deterministic demo
and index checks in a renamed actual checkout. No provider call was made by
that follow-up.

## Native harnesses and real-provider observations

Fresh **local actual-workerd** lifecycles passed with Claude Code with a hosted open-model service,
Pi with that service and Muse Code/Meta, recording **6, 7 and 12** provider calls respectively.
Each performed scoped work, independent artifact/report readback and test-key
revocation. These are real separate harness processes, but do not prove hosted
recovery or native Anthropic subscription availability.

The earlier six-harness matrix covers OpenCode, Pi, Hermes, Muse Code, nanoMuse
and OpenClaw. Adding Claude Code gives seven distinct harnesses with a narrow
completed lifecycle across those observations. OpenMuse TypeScript still has
no checked connector. Full feature/version/provider reliability remains unmeasured.

Local the Teleion Fabric shim called real providers in two bounded waves. The initial three calls
used source [`bd4d9ff7`](https://github.com/ta-amps/herma-infrastructure-shim-for-intelligent-agents/commit/bd4d9ff7981b08231eced14b70c52de8dc206f0a);
OpenAI `gpt-6-luna` completed that typed proposal check. The initial Anthropic HTTP 400 and OpenRouter
HTTP 404 remained unexplained in their original records. A later two-call wave
at [`b3715816`](https://github.com/ta-amps/herma-infrastructure-shim-for-intelligent-agents/commit/b3715816f18a6be468cab62131ac2a2f3d7f4337)
captured provider-reported categories: Anthropic reported credit/quota exhaustion
(`invalid_request_error`); OpenRouter reported no eligible provider endpoint
(code 404), with the specific routing constraint still unknown. Both attempts
were rejected, usage remained unknown and reservations were retained. There were
**five provider calls total**, no retries or provider fallback, and no Jev call.
These observations are not account-balance verification or provider invoices.
Anthropic and OpenRouter remain temporarily paused by owner direction. Their
adapters remain. The Teleion Fabric shim PR 10 implements and locally tests the manual pause,
shared operator-account health and one authorized recovery request after an
observed cooldown. Provider retry/reset guidance takes priority; fallback
backoff follows failures and does not cap healthy throughput. Unknown outcomes
retain reservations, late results cannot clear newer limits or steal a probe
lease, and no background probe or failed-turn replay runs.

The manual pause covers managed conversations and recognized-origin native
proxy routes selecting an operator fallback key. Explicit caller-owned proxy
credentials retain their existing authorization and settings. Automatic health
and recovery apply only to managed conversations; the proxy gains no automatic
retry or rotation. Twenty-way local Python/Worker fixtures admit one recovery
dispatch per limited-resource race. These are made-up local tests.

The pause is present in local operator configuration and source rollout settings.
No the Teleion Fabric shim deployment or live provider call occurred in its availability follow-up;
hosted enforcement is unverified. Shared-health PR 10 is complete at the recorded
scope. Merged source `ef704aa1` completes the bounded accounting follow-up:
selected-key readiness precedes reservation; accepted/nonterminal responses
remain unknown with reservations held; managed generation rejects unpriced
options and explicitly selects standard service tiers; known denials and
uncertain coordinator admission retain distinct reservation evidence. These
checks passed offline, and exact-head/main CI passed after merge. Deployment
remains held. Native proxy generation is unchanged. The earlier live OpenAI pass
does not verify the newly emitted standard-tier request fields. Separate deployments do not synchronize health
automatically, and legacy inference paths still need migration evidence.
Rollback must preserve expanded state and use a roll-forward disable, without
ledger or namespace resets. The owner pause does not change the observed
OpenRouter diagnosis into a credit-exhaustion finding. See
[providers and compute](providers-and-compute.md).

## Training, seeds and community research

The [optional training example](fine-tuning-pilot.md) completed real CPU and RTX
3060 LoRA updates on a tiny random-initialized Meta open model. It uses 20 owned made-up
examples split 12/4/4 by source and project family, 3,584 trainable parameters and
12 optimizer steps. Made-up test loss changed about 5.586128→5.396280; loading
the saved adapter onto a fresh base reproduced probe logits exactly. Private
Store tests saved six blobs per run and denied another principal record/blob/
execution reads. This is training plumbing and access evidence, not pretrained
Meta adaptation, a native/network training lifecycle or useful research gains.
Pretrained 1B/3B, Glimmer, Kaggle and paid GPU pilots remain unrun.

The code composition and video and motion packs use existing noun and TaskSpec
contracts. Their local HTTP
lifecycles validate pinned inputs, actual deterministic execution, private writes,
fenced submit/CAS and cross-principal/namespace denial. The worker implementation
runs in the test process through FastAPI TestClient. The video and motion pack's
media attribution digests remain made-up examples.

[Community seed ideas](community-seeds.md) came from four selected source/test
reviews and five README reviews. Six private draft bundles contain 14 noun and
12 verb candidates, checked for request shape, category membership and local
reference hashes only. No external runtime was installed, executed or admitted,
and upstream benchmark claims were not reproduced. Preserve license uncertainty
and reject upstream no-sandbox/full-access defaults.

## Historical scale and UI evidence

Before the storage incident, a corrected ten-process Pi wave completed **10/10**,
producing twenty private proposals and overlapping native tool activity for
**35.52 seconds**. Earlier 7/10 and 3/3 waves remain recorded, along with a
corrected rejected submission and a provider disconnect with unknown usage.
The removed arbitrary 2,048-token transport ceiling must not return.

The separate protocol waves completed 10/25/50/100 clients, with 100/100 in
**25.663 seconds** and no HTTP 429. All observed claim waits were zero and the
window was 32, so that live test did not trigger pressure adaptation. Actual
workerd injected-pressure tests cover pacing and heartbeat/submit availability
separately. Sustained native load and separate-account scale remain unverified.

The 16 rendered Firefox desktop/mobile banner checks used a stubbed clipboard
API. Earlier 112/112 execution-history and 24/24 public checks, portal checks
and seven-bundle parity remain historical evidence, not fresh recovery checks.

## Next evidence required

Use the [roadmap](roadmap.md) for broader hosted qualification, provider fixes, a useful
research loop, resolver/shim lifecycle, pack admission and wider native testing.
The latest home deployment log configures an hourly tick (`0 * * * *`) for a
24-hour cycle anchored at 13:00 UTC, a 10-minute manual cooldown, and stop time
November 4, 2026 at 17:00 UTC. Server repair mode remains off; the separate reasoning
flag does not enable it. This is configuration evidence, without a completed
hosted daily/manual cycle. Prior local portal checks and mock-DOM UI checks do
not establish hosted execution or fresh rendered-browser behavior.
