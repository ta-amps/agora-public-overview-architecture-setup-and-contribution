# Current status

Snapshot observed **2026-10-29T13:05:06.584713+00:00**. This page describes the reviewed October 29 integration. Later pushes, configuration changes or deployments require a new observation.

## Integration

All **22 reviewed PRs** are merged across the eight existing repositories. There are no open PRs in this snapshot, and all eight exact main revisions below have successful CI. The integration reconciled local work in isolated checkouts and preserved the original dirty development checkouts. Dependency updates pin Shamash, Eranos and Herma to merged Tessera revision `b1b470475c3ff03db0963bbcf6b271911d79f73e`; later Tessera changes in this snapshot are documentation and evidence.

Agora is the ninth public repository, with documentation and offline checks. The [JSON snapshot](../status.json) separates this guide from the eight product/support repositories. [Integration evidence](../evidence/integration-2026-10-29.json) lists every merged PR and bounded verification result.

| Repository | Main revision | CI at that revision |
| --- | --- | --- |
| [tessera](https://github.com/ta-amps/tessera) | [`775f7647`](https://github.com/ta-amps/tessera/commit/775f7647c0b6f858bc95bf08f52c7fa27ebd5d93) | [pass 40875723274](https://github.com/ta-amps/tessera/actions/runs/40875723274) |
| [shamash](https://github.com/ta-amps/shamash) | [`a6026225`](https://github.com/ta-amps/shamash/commit/a6026225b74449539855fae3c0cbbe9c2decdbab) | [pass 40875709744](https://github.com/ta-amps/shamash/actions/runs/40875709744) |
| [eranos](https://github.com/ta-amps/eranos) | [`8a6cabf8`](https://github.com/ta-amps/eranos/commit/8a6cabf83aa26df347201f943adf551ae4907394) | [pass 40875641519](https://github.com/ta-amps/eranos/actions/runs/40875641519) |
| [herma](https://github.com/ta-amps/herma) | [`492ced92`](https://github.com/ta-amps/herma/commit/492ced92dcab2dd73a719b874ce85d0572975bd4) | [pass 40875666486](https://github.com/ta-amps/herma/actions/runs/40875666486) |
| [kothar](https://github.com/ta-amps/kothar) | [`1f30c303`](https://github.com/ta-amps/kothar/commit/1f30c30357c62ebf56d0bb3d5d462332e84b2562) | [pass 40875693603](https://github.com/ta-amps/kothar/actions/runs/40875693603) |
| [kinema](https://github.com/ta-amps/kinema) | [`93abaae9`](https://github.com/ta-amps/kinema/commit/93abaae9b235258a8c9937fdbe8dc85451c46305) | [pass 40875681634](https://github.com/ta-amps/kinema/actions/runs/40875681634) |
| [hackathon-context](https://github.com/ta-amps/hackathon-context) | [`5ccebd6f`](https://github.com/ta-amps/hackathon-context/commit/5ccebd6f5c06fc581a06f48721fd1029b63a3bb2) | [pass 40872745512](https://github.com/ta-amps/hackathon-context/actions/runs/40872745512) |
| [pack-contributions](https://github.com/ta-amps/pack-contributions) | [`c0e3e27f`](https://github.com/ta-amps/pack-contributions/commit/c0e3e27fd3472b88be1acee6db8c6911d7aaf1a8) | [pass 40878259551](https://github.com/ta-amps/pack-contributions/actions/runs/40878259551) |

## Functionality

| Area | Implemented and observed | Boundary |
| --- | --- | --- |
| Tessera | Scoped nouns and verbs, claims/leases, CAS, blobs/buckets, receipts, execution reporting and bounded recall | Recall does not authorize replay or certify correctness; general category/profile resolution is proposed |
| Shamash | Synthetic evidence workflows, arithmetic, tier routing, model-worker lane and live discovery | Synthetic coverage; T3/T4 remain human-only |
| Eranos | Kit work, artifact/test flow, distinct reviewer and steward release boundary | Example coverage does not certify arbitrary NGO deployments |
| Herma | Scoped context, strict routing decisions, offline controls and explicit typed conversations | Optional configured inference; no mandatory server reviewer or general rule lifecycle claim |
| Kothar | Typed recipes, verified prewritten nodes and deterministic execution | Arbitrary generated executable code is outside the contract |
| Kinema | Frame evaluation, motion retargeting, captions, SVG output and metadata/layout QA | Complete encoding pipelines and all rendered-media checks remain extension work |
| Home / Frontier | Discovery, connection guidance and contract work on Tessera | Public candidate catalog empty; server repair off; independent admission pending |
| Contribution packs | Instructions, 10 meta-pack blueprints and the capability research proposal | No generic importer, active learning packs or feed/inbox research service |

## Hosted surfaces

Fresh executable builds matched all seven deployed Worker bundles byte for byte on October 29. This cycle did not redeploy them. Later integration commits changed documentation and source history, leaving those executable sources unchanged. Module digests and the comparison source revisions are in [status.json](../status.json).

| Surface | Deployed version | Discovered MCP tools |
| --- | --- | --- |
| [tessera](https://tessera.ta-amps.workers.dev) | `42d8bf93-0d37-47e6-8937-1070df117c27` | 37 |
| [shamash](https://shamash.ta-amps.workers.dev) | `b0228f52-6280-4cb7-9512-40f3ed6d9469` | 6 |
| [eranos](https://eranos.ta-amps.workers.dev) | `349325ae-b8f7-41e8-912e-eb6b71f7aad1` | 4 |
| [herma](https://herma.ta-amps.workers.dev) | `e7cf3607-d626-40e7-ae46-187e4fe536a8` | 3 |
| [kothar](https://kothar.ta-amps.workers.dev) | `a23638b2-8f1e-462b-bc5e-07240decda28` | 4 |
| [kinema](https://kinema.ta-amps.workers.dev) | `4237faa4-6bd8-414e-be5d-548e13db9f60` | 4 |
| [home](https://home.ta-amps.workers.dev) | `cddb9894-f4cf-4253-8d3e-c9de31d4d367` | 5 |

The comparison covers executable modules. It is not a complete configuration, asset, load or long-running operational certification. The separately maintained home portal has no public source repository.

Frontier discovery is enabled every 15 minutes, with a configured stop at **November 4, 2026, 17:00 UTC (noon ET)**. `server_repair_mode` is `off`; the observed cycle left repair work available to external workers. That schedule does not guarantee continuous repository development or automatic publication.

## Verification

Every existing repository passed `make check`; the relevant additional checks are below. Counts can include overlapping contract fixtures and should not be summed into an independent-case total.

| Repository | Fresh local result |
| --- | --- |
| tessera | 262 Python tests passed, 6 skipped; 5 actual workerd cases; local HTTP conformance 32 passed, 4 skipped; empty-backend negative control passed. |
| shamash | 259 tests passed; synthetic development cases, adapter conformance (30 passed, 6 skipped), TypeScript and frontend build passed. |
| eranos | 56 tests passed; example verification, adapter conformance (30 passed, 6 skipped), TypeScript and frontend build passed. |
| herma | 85 Python tests and 49 actual Worker checks passed, including strict decisions and offline no-egress controls. |
| kothar | 39 tests and the deterministic demo passed; demo uses 18 verified nodes. |
| kinema | 38 tests and the deterministic demo passed. |
| hackathon-context | Two unittest groups passed: 12 and 13 tests; offline document and example checks passed. |
| pack-contributions | 10 tests, 12 JSON examples, local documentation links and public hygiene passed. |

The home portal passed 33 Node checks and 20 actual Worker/SQLite checks. Deployed execution-history smoke passed **112/112**, with anonymous MCP and scoped keyed HTTP loops, exact recall, malformed/stale/replay controls and access isolation. The fresh public suite passed **24/24**, covering discovery, tool-card agreement, public projection and invalid payloads. The separate seven-surface metadata discovery passed **35/35**.

Native **OpenCode 2.1.2 / Ollama Cloud / kimi-k2.7-code** completed one synthetic execution-report and recall run per principal, anonymous and keyed. Each run recorded 13 actual tool calls, exact-input recall under a second lease and independent HTTP readback. The fresh keyed credential was revoked. These runs used 30 worker inference requests in total and zero deployed-server model requests. This is measured test usage, not a lifetime accounting claim. [Canonical native evidence](https://github.com/ta-amps/tessera/blob/775f7647c0b6f858bc95bf08f52c7fa27ebd5d93/docs/evidence/native-history-observation.json).

Two setup failures before inference remain recorded: a driver module-name collision and an unsupported enqueue route. Both were corrected before the successful attempts; neither was counted as a native pass. Unknown monetary cost remains unknown.

## Limits and next work

No fresh rendered-browser verification was available in this cycle. One native run per access mode does not establish repeat reliability or compatibility across other harnesses and models. Source and test review also cannot reconstruct inaccessible session history.

The general category/profile resolver, general shim admission/activation/rollback, independent Frontier candidate admission, broader native matrix and longer operational qualification remain open. Capability research is a proposed seed workflow; it has no active feed/inbox collection or adoption service. See the [roadmap](roadmap.md), [research use case](research.md) and [architecture policy](architecture.md).

Ordinary reasoning belongs to authorized workers. Servers coordinate deterministically; explicitly configured model interfaces and bounded server exceptions retain their own scope and allowance. The observed tests support their stated flows, not a measured claim that every ecosystem action already follows this policy.
