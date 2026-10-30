# Required nouns, verbs, surfaces and infrastructure architecture

Owner direction, October 29, 2026. This is a requirement for new work and review,
not a claim that all historical code has completed migration.

**Only nouns, verbs, surfaces and narrow supporting infrastructure. Seed packs
contain nouns and verbs. Reusable things are nouns; independently schedulable
work is verbs. Authorized workers perform ordinary reasoning. Tessera owns the
shared work and artifact lifecycle.** Reject changes that introduce a competing task
authority, hide domain agents in server handlers or bypass artifact admission.

Tools, code, models, datasets, profiles, recipes, prompts, seeds, observations,
adapters and evaluations are versioned nouns. Researching, generating, executing,
training, comparing, remixing, rating and reviewing are verbs. Reuse the owning
contracts; these descriptions do not create new ontology categories or grant
permissions. A deterministic helper can run inside a verb without becoming a
separate task.

Surfaces are websites, apps, dashboards, CLI and HTTP/MCP interfaces that expose
nouns and verbs. There are exactly two public surfaces: Eranos, the two-sided
marketplace, and Agora, the single overview of architecture and setup, use cases,
connecting any agent and contributing. Tessera and Herma are infrastructure; Herma
connects agents to context and models. Home is not a surface; its address will
send people to Agora. Everything else is nouns and verbs in seed packs, and an
agent kit is a seed pack generated for an NGO's agent; a noun can hold an agent's
whole setup, including the harness, model and working-directory files.
Infrastructure handles the limited supporting responsibilities listed below.
Neither a surface nor a pack gets an independent work authority.
“Project” may name a surface and scoped collection; it is not an additional core
primitive or lifecycle. Store any needed description as an existing noun.
Seed packs are bundles of nouns and verb templates/seeds, not a separate entity
type. Copying a pack never copies authority, credentials or activation rights.

## Server exceptions have a boundary

Server-side work uses the same nouns and verbs. A server's provider configuration,
health observations and attempt records are scoped nouns; independently
schedulable management outcomes are private verbs. “Server-side” describes
placement and access, not a separate entity model. The exceptions below allow
appropriate execution placement and deterministic plumbing. They never waive
identity, scope or evidence requirements.

Authorization must cover discovery, claims, noun versions, blobs, execution
history, receipts and logs. A private label or project name grants no access.
Provider rotation is deterministic selection among explicitly permitted
provider/model pairs for that data and payer. Retain every attempted model,
outcome and usage, including unknown outcomes; do not report only the winner.
Deterministic actions record no model and reference their parent attempt when
one exists. Credential availability alone does not authorize use.

| Class | Permitted responsibility | Required boundary |
| --- | --- | --- |
| Deterministic infrastructure | Identity, authorization, storage, leases, CAS, receipts, validation, indexes and backpressure | Existing scope and transaction rules; zero autonomous model calls |
| Essential management | Credential lifecycle, accounting, authorized provisioning, scheduling, deployment and recovery | Named owner, declared effects and audit evidence; schedules enqueue only already-authorized work |
| Requested model transport | Forward a caller's explicit model request | Selected provider, destination, data scope and payer; preserve supported generation settings |
| Explicit server reasoning | An approved interactive capability or exceptional recovery needing inference | Purpose, principal, data scope, exact provider/model/destination, payer, allowance, deadline, retry policy and outcome |

Being private, urgent or called “management” does not authorize domain reasoning
on the server. Prefer a private or operator-owned worker when work can wait.
Missing workers, a malformed payload or an empty review queue must not trigger
an automatic model fallback. Moving inference to a server-owned worker changes
its location, not its cost, identity or permissions.

## Seed packs carry no names and are never surfaces

Seed packs live in one pack library, `ta-amps/pack-contributions`, named only for
what they do and kept separate from both surfaces. The collection of nouns and
verbs for composing verified code without rewriting it packages verified code
nodes, recipes, compiler/runtime tools and checks. The collection for video and
motion made with code packages motion and scene recipes, formulas, assets, caption
tools and checks. The collection for spotting exploitation and scams in synthetic
cases, never accusing anyone, packages harm areas, pattern rules, dated rule
cards, money-flow checks and routing rules. These are noun collections with verb
templates describing useful work. The three older repositories that held them are
being renamed or archived, their tested code keeps plain names, and their old
websites will retire behind archive notices. Packaging does not create another
scheduler or admission authority, and exporting a pack does not install or
activate it.

| Pack | Nouns | Claimed work |
| --- | --- | --- |
| Code composition | Node catalog, code, recipe, compiler, execution result, validation evidence | Compose, compile, execute and verify a recipe |
| Video and motion | Scene, motion formula, asset reference, captions, evaluator, frame/QA result | Generate, retarget, evaluate and review motion |
| Exploitation evidence | Synthetic case, harm area, pattern rule, rule card, money-flow check, evidence summary | Index evidence, extract indicators, recheck the money, write and review a summary; a person decides every hold and referral |
| Training | Dataset, base revision, recipe, adapter and evaluation | Curate, train, evaluate and decide admission |
| Research | Source, observation, project profile, collector and comparison | Discover feeds, scan, extract, benchmark, compare and propose adoption |

Keep multiple independent solutions to a brief. Give each its own attempt verb,
lease, artifact references and receipt. Comparison and remixing are later verbs.
An artifact hash proves byte identity; successful execution proves neither
usefulness nor admission.

## Checks that enforce the direction

The [architecture inventory](../architecture.json) is a documentation index,
not a new runtime policy registry. Agora's `make check` rejects missing repository
classifications, any surface other than Eranos and Agora, infrastructure other
than Tessera and Herma, a repository under a retired pack name that is not a seed
pack, retired pack names on the public site, domain packs presented as work
authorities, unexplained server
exceptions and architecture claims without declared checks. Owning repositories
must test runtime behavior: no implicit model fallback, scoped effects, valid
payloads, deterministic pack exports and preserved existing interfaces.

Every change must name its nouns, verbs, contract owner and any server exception.
Do not use prose, a schema-valid fixture or a green unrelated suite as a substitute
for behavioral evidence. The [status report](status.md) records what is merged,
deployed, observed and still incomplete. This checkpoint does not certify
universal runtime coverage.
