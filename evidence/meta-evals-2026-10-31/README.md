# Synthetic Meta Open-Weights & Swarm Evaluation Records (Oct 30-31, 2026)

All evaluations below were run on deterministic synthetic templates with SHA-256 holdout digests pinned before scoring. Zero `api.meta.ai` completions and zero private user or nonprofit files were used for training.

## Artifacts & SHA-256 Digests

| File | Bytes | SHA-256 | Summary |
| --- | ---: | --- | --- |
| [lora_memory_eval_summary.json](lora_memory_eval_summary.json) | 11567 | `e6bcab77f447d3d7306e60586c224d43b24770077611e0b4862a3ae7e0cb847a` | Llama 3.2 1B & 3B Hybrid LoRA-as-Memory + 38.5-token Compact Pointer (`64.2% -> 91.7%` exact recall on 3B, `91.0%` fewer injected shim tokens, `8/8` reload determinism) |
| [router_eval_summary.json](router_eval_summary.json) | 3942 | `a2ac29c89051e69b8ede541cbf971ed677fac58a459051fdfba968bf5479cae4` | Llama 3.2 1B Herma Shim & Privacy-Tier Router LoRA (`26.7%` keyword / `10.0%` zero-shot -> `98.3%` full route exact match, `100.0%` contributor-tier private refusal recall, `0.0%` false refusal) |
| [multimodal-sam-asr-eval.json](multimodal-sam-asr-eval.json) | 20581 | `fc673710874a0b93c17d9e849c5858c659efd37ad38a7d44c2a9c942da03d57a` | Meta `facebook/sam-vit-base` UI mask segmentation (`0.928` mean IoU) + `wav2vec2-base-960h` speech-to-caption alignment (`0.016` mean CER) |
| [SCALABILITY_BENCHMARK.json](SCALABILITY_BENCHMARK.json) | 41666 | `839b22de7d7f5e7999c55b4763b9952fb4998c57df815610581cf31a1c0c661d` | 256 scoped OpenCode/MCP workers across 4 `workerd` cells (`76.87 tasks/s`, `25,620` MCP JSON-RPC calls, `0` lease collisions, `0` self-approvals) |
| [FAULT_INJECTION_EVIDENCE.json](FAULT_INJECTION_EVIDENCE.json) | 18606 | `53e8e7e2d70b5d0bf41c30316d2f3180fb8b2814bcc5db3be2892b2d8e1127bc` | `150/150` injected corrupt or stale drafts caught, tombstoned, and repaired by independent reviewers |
| [horizontal-scaling-256-workers.svg](horizontal-scaling-256-workers.svg) | 14800 | `214ef8ced977743553a920faf66b549a040944a7fabbb4550978972830e9bb9d` | Horizontal throughput & p50 latency scaling chart (`1 -> 256` workers) |
| [vertical-modular-architecture.svg](vertical-modular-architecture.svg) | 11321 | `78719a0f2dd46706541f68df65e9d93978d0a234231de5ecfb4e9d0ecafcac70` | Vertical modular PEFT LoRA Task Object & shim architecture diagram |
