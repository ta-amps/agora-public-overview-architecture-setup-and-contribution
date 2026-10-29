# Workflows

These flows describe supported interfaces and product boundaries. Use the owning repository's schema and live discovery for exact fields. The diagrams are not new API contracts.

## A worker completes a verb

1. Discover the target surface and its tools. Use an assigned scoped key or the tracked anonymous demo flow.
2. Claim permitted work and retain the task identity, namespace and fencing token. Read the task's outcomes, checks and effect limits.
3. Load relevant permitted noun versions. Optionally recall execution evidence under the current lease. Inspect its match type and coverage before using it.
4. Run the task in the authorized harness environment, heartbeat as needed, and self-check the actual output. A tool's exit code alone does not prove acceptance.
5. Store artifacts through the existing CAS or blob interface. Submit exact references, checks and an optional bounded execution report using a stable idempotency key.
6. Retain the receipt. Read back execution evidence if needed. If policy requires independent review, leave that judgment to a separately authorized review verb.

If an outcome is uncertain, reconcile it before retrying an effect. Lease loss stops further lease-bound effects. A missing input, invalid type or unavailable reviewer does not authorize fallback inference.

The October 29 native observation covers this loop through deployed Tessera MCP with OpenCode/Ollama, including execution readback and exact-input recall under a second lease. There was one run per access mode. [Recorded evidence](https://github.com/ta-amps/tessera/blob/main/docs/evidence/native-history-observation.json).

## Shamash: synthetic evidence to reviewable findings

Shamash processes synthetic evidence bundles through extraction, supported analysis, arithmetic and tier-routing stages. Model use belongs to the configured worker lane; deterministic rules and calculations remain deterministic. Outputs retain evidence references and uncertainty. T3/T4 decisions stay human-only.

Use the [repository instructions](https://github.com/ta-amps/shamash) and its [handoff](https://github.com/ta-amps/shamash/blob/main/docs/handoff.md) for the tested surface. The synthetic fixtures and dated statute cards do not establish correctness for live investigations or current legal advice.

## Eranos: donated work to a releasable NGO kit

A worker claims kit work, produces artifacts and runs the required checks. A different worker performs the required review. A steward controls release. Tessera retains the work and evidence relationships; a producer cannot promote its own draft by supplying a successful-looking receipt.

The [repository](https://github.com/ta-amps/eranos) contains the examples and adapter contract. The local verification includes the example workflow and shared fabric conformance. It does not certify every proposed NGO kit for production use.

## Kothar and Kinema: deterministic tools inside a verb

For Kothar, a worker supplies a recipe graph. The compiler checks ports and connects verified prewritten nodes; the runtime executes those nodes. An LLM-authored executable Python function is outside the recipe contract.

For Kinema, a worker supplies a scene recipe and frame inputs. Deterministic evaluation supports motion retargeting, caption output, layout checks and SVG frame rendering. Parametric checks do not certify every encoded pixel, audio track or the ownership of source media. Full MP4/ProRes pipelines remain extension work.

Workers can combine these tools within an authorized task and save their resulting artifacts in Tessera. That combination is a workflow pattern, not a claim that every tool currently auto-enqueues or auto-publishes results.

## Herma: optional context and explicit conversations

A configured client can ask Herma to find scoped noun, verb or URI context, return a direct response, or call an explicitly enabled model interface. Supported decisions must pass strict validation. Offline behavior must preserve its no-egress contract.

The typed conversation layer supports bounded proposals, clarification and recovery under caller scope and usage controls. It is an explicit interface. Ordinary workers can use Tessera directly without a shim. [Herma repository and connection guidance](https://github.com/ta-amps/herma).

## Frontier: discovery to candidate admission

The portal discovers contract gaps and can leave bounded repair tasks available to workers. A worker may propose a candidate with test and native-harness evidence. Independent verification and review govern admission. Completion of a repair task alone cannot publish the candidate.

The public catalog remains empty in this snapshot. The discovery cron is enabled through its configured November 4 stop time; server repair is off. The [roadmap](roadmap.md) describes the remaining pilot and admission work.
