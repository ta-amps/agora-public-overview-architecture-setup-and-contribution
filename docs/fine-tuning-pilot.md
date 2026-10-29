# Proposed fine-tuning pilot

A specialist could strengthen the submission if it measurably improves the
research-to-work workflow. Meta's event page includes open-weight models and
judges the indie track on creativity, technical ambition and a working result.
That supports a measured adaptation experiment; fine-tuning by itself is not
evidence of a better product. [Hackathon scope and criteria](https://dev.meta.ai/events/global-hackathon).

This is a proposal. No model has been downloaded or trained, no adapter exists,
and no GPU has been provisioned for this pilot.

## One useful specialist

Give the worker a permitted source and a versioned project profile. Ask it to
produce an evidence-grounded capability noun, a relevance judgment with explicit
unknowns, and a candidate verb worth doing next. This directly addresses the
[feed and newsletter research problem](research.md): convert announcements into
useful work for a particular architecture, hardware and set of interests.

Start by testing the unchanged model with a fixed prompt and output schema.
Only consider training when reviewed examples reveal a repeatable model failure.
Fix transport, schema and harness bugs in their owning code; do not train a model
to compensate for truncated responses or broken tool integration.

## Candidate model and method

Muse Glimmer is a 30B model released under Apache 2.0. It is a candidate base for
this experiment, not a selected deployment. [Official model card](https://huggingface.co/meta-models/Muse-Glimmer-30B).

Meta documents supervised fine-tuning with LoRA and QLoRA, including a QLoRA
recipe verified on one H100. That is a practical starting recipe to evaluate
once training hardware is available; it does not establish the memory, runtime
or result for this dataset. [Meta post-training guide](https://dev.meta.ai/docs/muse-glimmer/post-training).

No suitable GPU worker is confirmed here. Muse API and Ollama Cloud credentials
do not establish access to training hardware. Job cost and duration cannot be
estimated responsibly until the dataset, GPU and training configuration are
specified.

## Keep training in the noun/verb lifecycle

| Noun | What it records |
| --- | --- |
| Dataset manifest | Permitted sources, reviewed task inputs and final outputs, evidence references, hashes and splits |
| Base revision | Exact model/tokenizer versions and license reference |
| Training recipe | Framework versions, adapter configuration, hardware and run allowance |
| Adapter | Immutable output with lineage to the base, dataset and recipe |
| Evaluation report | Baseline and adapter results, failures, resource use and decision |

Verbs curate and split the examples, train the adapter, evaluate it, then review
and decide admission. An authorized GPU worker claims the training verb and
performs the compute. Tessera coordinates and records evidence; the server does
not perform ordinary model reasoning. No adapter is promoted automatically.

Use only reviewed task inputs, final outputs and supporting evidence with
permission for this use. Exclude raw session histories, credentials, private
material and hidden reasoning. A successful execution receipt alone does not
make an output a valid training example.

## The test that decides whether it helps

Hold out whole source and project families before training. Compare the adapter
with the unchanged prompted, schema-constrained base on the same held-out inputs
and compatible generation settings. Keep the test set out of training and
selection. Independent review should check factual grounding against the pinned
sources and whether the proposed work is useful and correctly decomposed.

Report unsupported claims, missed uncertainty, invalid outputs, failed tasks,
latency and resource use alongside any improvement. Retain the unchanged model
if the adapter does not improve the declared criteria. The showcase result would
be a reproducible before/after comparison and a reviewable adapter noun, not a
claim that fine-tuning solves research automatically.
