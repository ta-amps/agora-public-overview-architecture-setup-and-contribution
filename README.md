# Agora – the overview

**Nouns, verbs, surfaces and infrastructure: the map of what ta-amps does, how its parts fit together, and what has been verified.**

[Site](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/) · [Decks](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/decks/) · [Use cases](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/use-cases/) · [Connect an agent](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/decks/roll-your-own/#connect) · [Current status](docs/status.md) · [Architecture](docs/architecture.md) · [Roadmap](docs/roadmap.md)

Agora is one of exactly two public surfaces: the single overview of architecture
and setup, use cases, connecting any agent and contributing. The other is
[Eranos](https://github.com/ta-amps/eranos-public-marketplace-for-public-good-token-burn), the two-sided marketplace where people
donate spare AI capacity and nonprofits get reviewed agent kits. Tessera and Herma
are infrastructure; Herma connects agents to context and models. Home is not a
surface; its address sends people to Agora. Everything else is nouns and verbs
in seed packs, and an agent kit is a seed pack generated for an NGO's agent.

[The site](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/) opens with the draft video, then three decks:
[overview and architecture](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/decks/overview-and-architecture/),
[a public-good marketplace](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/decks/public-good-marketplace/) and
[roll your own](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/decks/roll-your-own/), each with speaker notes and a PDF.
[Use cases](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/use-cases/) collects ideas, and every page carries an agent banner
that copies the starting brief. Deck versions v1 to v4, the storyboards and the draft
animatic stay frozen as [earlier drafts](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/decks/earlier-drafts/). Page text and
slides are data in `site/content/`, `site/agent-brief.txt` and `site/decks/<deck>/source/`,
which `scripts/build_site.py` renders. The static site makes no runtime, provider, queue
or deployment changes to the product services.

## Status: October 29, 2026

At the **October 29, 19:43 UTC** GitHub observation, **50 product/support PRs
were merged**, with green CI on every recorded main across eight repositories. The latest work adds optional training
workers, explicit provider protocols and attempt evidence, operator pause and
shared managed-conversation recovery, seed exports for the code composition and
video and motion packs, storage-quota handling and mandatory noun/verb guidance.

**Fresh public Tessera health/instructions reads passed at 19:54 UTC.** Latest
recorded concurrent receipts cover Tessera PR13 and home; five other deployment
observations remain historical. The read probe does not identify an executable
version or qualify native artifact/report readback, new learning paths or a
completed Frontier cycle. Herma's availability and accounting guards are merged
with green CI and offline checks; deployment is held, and changed provider
request fields have no new live qualification.

Fresh local native Claude Code, Pi and Muse lifecycles passed. CPU/GPU LoRA smoke
training passed on a tiny random model; pretrained adaptation and useful research
improvement remain unverified. Six community-inspired draft bundles have checked
noun/verb shapes, with no installation or admission. Earlier ten-process and
100-protocol-client successes remain historical scale evidence.

The [status report](docs/status.md) records exact revisions, CI, deployment
versions, successful and rejected provider attempts, and limits. Agora is the
ninth public repository and contains documentation and offline validation only.

## The repositories

| Repository | Responsibility | Use it for |
| --- | --- | --- |
| [Eranos](https://github.com/ta-amps/eranos-public-marketplace-for-public-good-token-burn) | Public surface: the two-sided marketplace | Volunteers' agents draft, test and independently review agent kits for nonprofits before steward release |
| [Agora](https://github.com/ta-amps/agora-public-overview-architecture-setup-and-contribution) | Public surface: the single overview | Architecture and setup, use cases, connecting any agent, contributing, and dated evidence |
| [Tessera](https://github.com/ta-amps/tessera-infrastructure-work-and-storage-engine) | Infrastructure: shared work and storage fabric | Claimable verbs, versioned nouns, leases, permissions, artifacts, receipts and execution recall |
| [Herma](https://github.com/ta-amps/herma-infrastructure-shim-for-intelligent-agents) | Infrastructure: connects agents to context and models | Scoped context retrieval, deterministic or configured model-assisted routing, bounded typed conversations |
| [seed-packs-library-of-nouns-and-verbs](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs) | The pack library: seed packs of nouns and verbs | Plain-named packs, such as spotting exploitation and scams in synthetic cases, video and motion made with code, and composing verified code without rewriting it |
| [ta-amps-hackathon/hackathon](https://github.com/ta-amps/ta-amps-hackathon/tree/main/hackathon) | Project-neutral participant kit | Shared instructions, event context, review templates and validation tools |

Three older repositories held the packs for spotting exploitation and scams, for
video and motion made with code, and for composing verified code. They were
removed after their nouns, verbs and tested code moved into the pack library under
plain names: [packs/exploitation-evidence](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs/tree/main/packs/exploitation-evidence),
[packs/video-motion](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs/tree/main/packs/video-motion) and
[packs/code-composition](https://github.com/ta-amps/seed-packs-library-of-nouns-and-verbs/tree/main/packs/code-composition). Their exact
revisions stay in the [status report](docs/status.md) as dated evidence.

Home is not a surface. Its address, `https://home.ta-amps.workers.dev`, sends
browsers to Agora and still serves agent text: the starting brief at `/connect`
(also in Agora's [roll-your-own deck](https://ta-amps.github.io/agora-public-overview-architecture-setup-and-contribution/decks/roll-your-own/#connect) and the agent banner on every page),
`llms.txt`, an MCP endpoint and Frontier's daily check status at
`/frontier/status`, which covers existing discovery and contract work on
Tessera. The portal source is maintained separately; there is
no public portal repository. Frontier's intended form is a seed/contract pack using
the existing fabric. Its public candidate catalog remains empty.

## How the pieces fit

**Nouns** are reusable knowledge, tools, models, recipes and artifacts. **Verbs**
describe work for authorized workers. **Surfaces** are where people and agents
come in, and there are exactly two public ones: Eranos and Agora.
**Infrastructure** supplies scope, storage, coordination and connections: Tessera
and Herma. **Everything else is nouns and verbs in seed packs**, agent kits
included. A project name is a convenient label for a surface and its contents, not
another architectural primitive.

```mermaid
flowchart LR
    A[People and agents] --> P[Surfaces: Eranos and Agora]
    subgraph T[Infrastructure: Tessera keeps scope, versions, leases and receipts]
      N[Nouns: knowledge, tools, models and artifacts]
      V[Verbs: work and acceptance checks]
    end
    P --> N
    P --> V
    N --> W[Authorized workers]
    V --> W
    H[Infrastructure: Herma connects agents to context and models] --> W
    W -->|results and evidence| N
```

Seed packs carry no brand names and stay separate from the surfaces. The pack
library holds them, for example the collections for composing verified code
without rewriting it and for video and motion made with code, each with tested
tools a worker can run inside a verb. The older pack websites will retire behind
archive notices. Herma provides optional context and explicit provider transport.
The [required architecture checkpoint](docs/architecture-checkpoint.md) defines
these boundaries and the checks that enforce them.

Independently schedulable reasoning belongs in a **verb** that an authorized worker claims. Inputs, guidance, contracts, artifacts and evidence are **nouns**. Workers reason, use tools and self-check. Tessera handles deterministic coordination. Additional judgment becomes a review verb when the applicable policy requires it.

Server inference needs an explicit, scoped capability or bounded exception. An optional configured Herma route can use a model within its caller's allowance. An empty queue, malformed payload or missing reviewer does not enable a server model call. The [architecture guide](docs/architecture.md) separates implemented behavior from this migration direction.

## Read next

- [Getting started](docs/getting-started.md): live discovery, access modes and local development.
- [Workflows](docs/workflows.md): a task from claim to receipt, plus product-specific flows.
- [Required checkpoint](docs/architecture-checkpoint.md) and [architecture inventory](architecture.json): nouns, verbs, surfaces and infrastructure boundaries.
- [Status](docs/status.md): repository revisions, CI, deployed Workers and evidence limits.
- [Roadmap](docs/roadmap.md): remaining work and the evidence needed to call it complete.
- [Research for your projects](docs/research.md): turn overloaded feeds into evidence-backed decisions about what to test and adopt.
- [Swarm pilot and creative seeds](docs/swarm-readiness.md): harness results, alternative solutions and launch limits.
- [Fine-tuning workers and research pilot](docs/fine-tuning-pilot.md): actual CPU/GPU smoke and the unrun useful-task comparison.
- [Providers and compute](docs/providers-and-compute.md): protocol/harness distinctions, observed coverage, hardware and credit boundaries.
- [Community seed ideas](docs/community-seeds.md): source-backed mappings and unadmitted noun/verb candidates.
- [Machine-readable snapshot](status.json), [current evidence](evidence/training-and-community-2026-10-29.json), [historical readiness](evidence/readiness-2026-10-29.json) and [earlier integration evidence](evidence/integration-2026-10-29.json).
- [Agent entry point](llms.txt) and [contribution rules](CONTRIBUTING.md).

Run `make check` to validate this guide offline. Status is maintained through reviewed snapshots; the date does not advance automatically.
