# Fine-tuning workers and the research pilot

Updated October 29, 2026. Teleion Fabric now includes an optional training-worker
example, and real CPU and GPU adapter smoke runs passed. The useful research
specialist remains a proposed experiment: no pretrained Meta model was adapted,
and no improvement in research quality has been demonstrated.

The implementation merged in [Teleion Fabric PR 9](https://github.com/ta-amps/teleion-fabric-infrastructure-work-and-storage-engine/pull/9).
Read the [worker guide at the merged revision](https://github.com/ta-amps/teleion-fabric-infrastructure-work-and-storage-engine/blob/36526860b0048df2dec675051ec6681023bda3d9/docs/fine-tuning-workers.md)
for runnable commands and the [dated smoke evidence](https://github.com/ta-amps/teleion-fabric-infrastructure-work-and-storage-engine/blob/36526860b0048df2dec675051ec6681023bda3d9/examples/finetuning/evidence/smoke-2026-10-29.json)
for versions, hardware, losses, artifact hashes and implementation fingerprints.

## What actually ran

| Observation | Result | Limit |
| --- | --- | --- |
| Training data | 20 owned made-up examples, split 12/4/4 with disjoint source and project families | Template examples test the pipeline; they are not a research benchmark |
| Model and update | Tiny random-initialized model using the architecture of Meta's open-weight models, 110,784 total parameters including 3,584 trainable LoRA parameters; 12 optimizer steps | No pretrained weights: not Meta's open-weight 1B or 3B models, and not Muse Glimmer 30B |
| CPU and GPU | Both completed; the GPU was an RTX 3060 with about 11.62 GiB available VRAM | This does not establish memory fit for a 1B, 3B or 30B model |
| Made-up test loss | Approximately 5.586128 to 5.396280 on each device | Diagnostic loss only; factual grounding and useful task quality remain unmeasured |
| Save/reload | Frozen base unchanged; adapter changed; fresh base plus saved adapter reproduced probe logits with zero measured difference | Verifies saved training artifacts, not their usefulness |
| Private fabric lifecycle | Curate/train claims, heartbeats, six saved base/adapter blobs per run, execution capture and readback; cross-principal record/blob/execution reads denied | Real in-process Store coverage, not a native-harness or hosted training lifecycle |

Data preparation, source and contract authoring are independent of the ML
framework. The PEFT backend and its dependencies live in a separate worker
environment. Teleion Fabric server does not acquire torch or a GPU trainer, and
the example adds no scheduler.
Full sequences must fit the explicit memory recipe; over-length examples are
rejected with their identity and length. There is no silent truncation, padding
target or added inference-output ceiling.

## One useful specialist

Give a worker a permitted source and a versioned project profile: architecture,
hardware, costs, interests, constraints and evaluation goals. Ask it to produce
an evidence-grounded capability noun, a relevance judgment with explicit
unknowns, and a candidate verb worth doing next. This addresses the
[feed and newsletter research problem](research.md): turn incompatible
announcements and benchmark claims into useful work for a particular project.

Start with the unchanged model, a fixed prompt and an output schema. Only
consider training when reviewed examples reveal a repeatable model failure.
Fix transport, schema and harness bugs in their owning code; do not train around
truncated responses or broken tool integration. A defensible no-action or
no-improvement result is useful evidence.

## Nouns, verbs and admission

Reusable training assets must be nouns and independently schedulable work must
be verbs. A training seed pack bundles them; a project name groups a purpose or
surface and does not introduce another primitive or authority.

| Noun | Existing category | What it records |
| --- | --- | --- |
| Dataset and split manifest | `noun.benchmark_suite` | Permitted inputs, reviewed targets, evidence, fingerprints and family splits |
| Base and candidate adapter | `noun.model_spec` | Exact base/tokenizer revision, license, adapter digest and lineage |
| Training recipe | `noun.code_node` | Implementation, dependency versions, device, adapter settings and run allowance |
| Evaluation and execution evidence | `noun.eval_run` and existing execution records | Baseline, adapter, failures, resource use, records and admission decision |

The example authors curate/split and train as `verb.solve_draft`, evaluation as
`verb.benchmark_harness`, and review as `verb.verify_gate`. These are existing
contracts, not new ontology types. An authorized worker executes the training
verb; Teleion Fabric retains scope, version, lease, CAS, blob and record authority.
Server-side management also uses scoped nouns and verbs under the
[architecture checkpoint](architecture-checkpoint.md).

The local example completed curation and training. Its evaluation/admission
task templates do not mean those later stages ran. Offline payload previews do
not enqueue work, validate predicted record versions or admit an adapter.
No artifact is promoted automatically.

Use only reviewed, permitted task inputs, final outputs and supporting evidence.
Exclude raw session histories, credentials, private material without permission,
and hidden reasoning. A successful record alone does not make an output a
valid training example.

## Pretrained recipes remain unrun

Pinned QLoRA recipes for Meta's open-weight 1B and 3B models are available for a small pilot
on one 12 GB RTX 3060 or 16 GB T4. Actual fit and throughput still need measurement.
The runner uses an existing cache by default; downloads require explicit
authorization and existing model access. It does not accept a license. A Kaggle
wrapper runs inside an already authorized notebook; it creates no notebook or
GPU allocation. See [providers and compute](providers-and-compute.md).

Muse Glimmer is a 30B model under Apache 2.0. Its official post-training guide
includes LoRA and QLoRA, with QLoRA checked on one H100. Teleion Fabric's optional
bridge prepares a pinned official configuration and checks complete example
lengths; it has not run Glimmer training. The H100 recipe is not evidence that
30B training fits the smaller GPUs. [Official model card](https://huggingface.co/meta-models/Muse-Glimmer-30B),
[Meta post-training guide](https://dev.meta.ai/docs/muse-glimmer/post-training).

No pretrained model download, Kaggle training job, paid GPU rental or Glimmer
training run was performed for this pilot. Muse and other hosted inference credentials
do not supply training weights or hardware. Estimate time and cost only after
the dataset, permitted base, device and recipe are selected and a measured
training/reload/evaluation slice establishes their behavior.

## The comparison that decides whether it helps

Hold out whole source and project families before training. Compare the adapter
with the unchanged prompted, schema-constrained base on the same held-out inputs
and compatible generation settings. For QLoRA, compare against the same quantized
base. Keep the test set out of training and model selection.

Independent review should check factual grounding against pinned sources,
relevance to the project, useful task decomposition, valid noun references and
acceptance checks. Report unsupported claims, missed uncertainty, invalid
outputs, failed tasks, latency and resource use alongside any improvement.
Retain the baseline when the adapter does not improve the declared criteria.
The showcase should be a reproducible comparison and a reviewable adapter noun.
