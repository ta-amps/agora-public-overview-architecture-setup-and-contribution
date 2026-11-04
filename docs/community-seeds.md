# Community ideas as noun and verb packs

Reviewed October 29, 2026. Public hackathon projects offer useful patterns for
reusable packs. The core remains nouns and verbs, exposed through surfaces and
supported by narrow infrastructure. Seed packs contain nouns and verbs; they do
not introduce an autonomous runtime, separate scheduler or admission authority.

The review covered selected public source files in four repositories and README
snapshots in five more. It did not execute those projects or reproduce their
benchmarks. A described capability is an integration candidate, not proof that
the application runs unchanged on this fabric.

| Inspiration | Reusable noun roles | Worker verbs | First acceptance check |
| --- | --- | --- | --- |
| [Athos](https://github.com/athos-agent/athos) | Scoped procedure, preference, version and application evidence | Capture, apply, compare, revoke | Cross-harness procedure round-trip without cross-principal data leakage |
| [agent-cost-harness](https://github.com/IrwinJam/agent-cost-harness) | Fixed workload, tariff, cache policy and paired results | Measure baseline, test, compare quality and cost | Same model/settings; reject cost savings that fail declared quality criteria |
| [QorTime](https://github.com/ConWan30/qortime-ai) | Observation, rule, signature envelope and explanation | Verify, explain, challenge, review | A signed false claim passes integrity but remains unverified for correctness |
| [LUCID](https://github.com/shittuquoyum-ui/LUCID) | Commit diff, exact quote, concept, lesson and question | Explain, verify quotes, test behavior, evaluate learning | Correct quotation paired with a false explanation must fail semantic evaluation |
| [FrontierSight](https://github.com/tamzid2001/frontiersight-ai) | Scene tracks, calibration, assumptions and simulation evidence | Compute, simulate, compare, review | Missing calibration prevents metric claims |
| [ANKITA](https://github.com/akyourowngames/A.N.K.I.T.A) | Job, cancellation state, output and delivery record | Execute, cancel, verify, deliver, recover delivery | Failed delivery must not repeat a completed external effect |
| [Skillry video](https://skillry.dev/skills/output/video) and [SPIDER](https://github.com/M4SPIDER/spider-game-engine-open-source-) | Storyboard, scene recipe, asset and render | Compose, render, inspect, revise | Actual frame/audio checks and evidence for demo claims |
| [Carpathron](https://github.com/qubitpage/carpathron-muse) | Device profile, permitted command and telemetry | Simulate, dispatch, verify stop | Fake-device lease expiry, duplicate command and cancellation tests |
| [VeeVee](https://github.com/wayneherrington/veevee) | Preference, private memory, source and media reference | Retrieve, answer, update/delete memory | Scoped data and explicit no-key behavior |

These are original proposed mappings. Real-time rendering, audio and device
safety loops remain in appropriate executors; Teleion Fabric coordinates useful work
units and records evidence, rather than scheduling every frame or control tick.
Source text cannot change the worker's permissions. Upstream full-access or
no-sandbox modes are not adopted.

Six private draft bundles were authored: Community Scout, Working Practices,
Cost Trials, Checked Outcomes, Commit Tutor and Demo Workshop. Together they
contain 14 candidate nouns and 12 alternative verb proposals. Their request
shapes, registered category membership and local reference hashes were checked
against Teleion Fabric. No pack was imported, no task enqueued and no artifact admitted.
The [status evidence](status.md) records this limited authoring result.

The best initial combination addresses the [research problem](research.md):
discover a technique, compare it against a pinned architecture/hardware profile,
and retain a reviewed working procedure only when it improves the declared
outcome. Keep independent solutions and no-change results.

## Evidence and reuse boundaries

The cost-harness savings are upstream list-price estimates, not reproduced
savings for this system. Its published main cache trial did not establish the
stated quality non-inferiority margin. Test cache changes separately from model
reasoning/settings changes. [Upstream results](https://github.com/IrwinJam/agent-cost-harness/blob/576fe5e5dae738b53e84e37fea7532fda544501c/docs/RESULTS.md).

QorTime's inspected license is PolyForm Noncommercial; any code reuse needs
compatible permission. Referencing the integrity/correctness distinction does
not copy its implementation. [Pinned license](https://github.com/ConWan30/qortime-ai/blob/95b39609d1e282f1a10aee8b813308dc28bfed50/LICENSE).
Other licenses and media rights must be checked at the relevant revision.

A full discussion review needs an authorized channel export with timestamps,
message IDs and thread coverage. Discord's personal data package includes the
account's own sent messages, not everyone else's conversation.
[Discord data-package contents](https://support.discord.com/hc/en-us/articles/360004957991-Your-Discord-Data-Package).
Keep raw chat private; use public source facts and synthetic fixtures for shared
pack proposals. An export, link index or well-formed payload does not establish
source reliability, benchmark comparability or permission to execute its code.
