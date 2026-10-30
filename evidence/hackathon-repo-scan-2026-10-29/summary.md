# Hackathon repositories as nouns and verbs

Descriptive counts from `hackscan` 1.2.0 over every repository in the Watt Mind directory of the Meta Global AI Hackathon 2026 (`raw/02-projects-json/projects.json`, sha256 `93b1c470eb2d9258`). Nothing here ranks, scores or judges any team. The directory's own scores and ranks are copied into each repo file for provenance only and are not used. Counts are of repositories unless a row says otherwise.

Method in one paragraph: each repository was cloned anonymously (shallow, blobs under 1 MiB, no checkout, no submodules, no LFS), its tree and small text blobs were read from the git object store, and fixed regular expressions and manifest parsers mapped files to noun categories and runnable entry points to verb categories. No repository content was executed and no model was called. Mentions are text matches, not proof of use. See `SCHEMA.md` and `scanner/README.md`.

## Scan

| item | value |
| --- | --- |
| directory rows | 740 |
| unique repositories | 739 |
| duplicate URLs in directory | 1 |
| scanned | 705 |
| failed | 34 |

Failures by reason (repository names are removed from this published copy):

| reason | repos | examples |
| --- | --- | --- |
| empty_repository | 24 | — |
| not_found_or_private | 5 | — |
| timeout | 5 | — |

## Basics

| item | repos | % of scanned |
| --- | --- | --- |
| tests present | 470 | 66.7 |
| evaluation or benchmark files | 184 | 26.1 |
| CI (any) | 152 | 21.6 |
| GitHub Actions workflows | 151 | 21.4 |
| Dockerfile | 154 | 21.8 |
| compose file | 49 | 7.0 |
| Dockerfile or compose | 159 | 22.6 |
| devcontainer | 4 | 0.6 |
| README found | 679 | 96.3 |
| agent instruction files (AGENTS.md, CLAUDE.md, .cursor/rules ...) | 201 | 28.5 |
| vendored or build output committed (node_modules, venv, dist ...) | 46 | 6.5 |

Tree totals across scanned repos: 120195 files (median 55 per repo), 17854442 text lines (median 5897), 10151410 code lines (median 4368). Lines exclude vendored paths, lockfiles, minified files, datasets, assets and blobs of 1 MiB or more.

### Licenses (from LICENSE/COPYING files at the root)

| license | repos |
| --- | --- |
| none found | 374 |
| MIT | 253 |
| Apache-2.0 | 51 |
| AGPL-3.0 | 10 |
| LicenseRef-proprietary | 5 |
| NOASSERTION | 3 |
| PolyForm-Noncommercial-1.0.0 | 2 |
| BSD-3-Clause | 1 |
| CC0-1.0 | 1 |
| GPL-3.0 | 1 |
| LGPL-2.1 | 1 |
| MULTIPLE(Apache-2.0,MIT) | 1 |
| MULTIPLE(LicenseRef-Meta-SAM-License,MIT) | 1 |
| PolyForm-Strict-1.0.0 | 1 |

### Primary language (most files by extension)

| language | repos |
| --- | --- |
| Python | 350 |
| TypeScript | 153 |
| (none) | 78 |
| JavaScript | 67 |
| HTML | 14 |
| C# | 9 |
| Kotlin | 6 |
| Rust | 6 |
| Dart | 5 |
| PHP | 4 |
| Jupyter Notebook | 3 |
| Swift | 3 |
| GDScript | 2 |
| Go | 2 |
| C++ | 1 |
| PowerShell | 1 |
| Shell | 1 |

### Languages present (repos containing at least one file)

| language | repos | files | lines |
| --- | --- | --- | --- |
| Python | 442 | 18983 | 3530208 |
| HTML | 341 | 1861 | 633129 |
| JavaScript | 334 | 3973 | 728001 |
| CSS | 305 | 597 | 189832 |
| TypeScript | 235 | 21813 | 3920350 |
| Shell | 155 | 389 | 34703 |
| Dockerfile | 154 | 207 | 5680 |
| SQL | 63 | 354 | 22442 |
| PowerShell | 41 | 121 | 12214 |
| Batchfile | 30 | 66 | 2625 |
| Makefile | 26 | 26 | 1393 |
| Jupyter Notebook | 23 | 55 | 56970 |
| Swift | 21 | 277 | 47891 |
| Kotlin | 18 | 357 | 54843 |
| Rust | 14 | 1109 | 336803 |
| C# | 11 | 529 | 103521 |
| Dart | 10 | 717 | 191662 |
| C++ | 7 | 25 | 3700 |
| Groovy | 7 | 24 | 498 |
| PHP | 7 | 605 | 94060 |
| C | 6 | 22 | 598 |
| Java | 6 | 22 | 4646 |
| CMake | 4 | 14 | 1028 |
| GDScript | 4 | 66 | 7490 |
| Svelte | 4 | 80 | 8596 |

## Nouns by category

Each file gets one category; `tool` counts distinct declared dependencies and `model` adds distinct model families mentioned to model files.

| category | repos with any | total items | median per repo |
| --- | --- | --- | --- |
| docs | 694 | 10781 | 5 |
| code | 626 | 37622 | 23 |
| tool (dependencies) | 531 | 9025 | 8 |
| model | 624 | 2524 | 3 |
| prompt | 178 | 1426 | 0 |
| dataset | 174 | 2272 | 0 |
| asset | 372 | 9488 | 1 |
| config | 641 | 14066 | 7 |
| test/evaluation | 488 | 21167 | 4 |

## Verbs

### By category

| category | repos with any | total items |
| --- | --- | --- |
| build | 409 | 1078 |
| run/serve | 583 | 11713 |
| test/check | 440 | 2702 |
| deploy | 99 | 192 |
| data processing | 178 | 579 |
| agent tool | 106 | 675 |
| scheduled | 32 | 67 |
| other (unclassified) | 50 | 153 |

### By kind

| kind | repos with any | total items |
| --- | --- | --- |
| script | 511 | 4965 |
| http_route | 343 | 6969 |
| npm_script | 288 | 2532 |
| container_build | 154 | 207 |
| ci_job | 151 | 408 |
| console_entry_point | 116 | 165 |
| agent_tool | 95 | 552 |
| cli_command | 80 | 650 |
| compose_service | 48 | 164 |
| scheduled | 32 | 67 |
| make_target | 26 | 314 |
| mcp_tool | 14 | 123 |
| precommit_hook | 9 | 30 |
| procfile_process | 1 | 1 |
| task_target | 1 | 12 |

Most common npm script names: `dev` (230), `build` (223), `test` (176), `start` (148), `lint` (116), `typecheck` (107), `preview` (86), `check` (23), `test:watch` (20), `test:e2e` (17), `db:migrate` (15), `deploy` (15), `format` (15), `eval` (14), `demo` (13).

Most common Makefile targets: `test` (23), `demo` (10), `check` (8), `dev` (8), `lint` (8), `setup` (8), `smoke` (6), `help` (5), `bench` (4), `clean` (4), `eval` (4), `install` (4), `audit` (3), `record` (3), `replay` (3).

## Dependencies (tool nouns)

539 repos have at least one parsed manifest (0 manifest parse errors recorded). Ecosystems: pypi 323, npm 281, maven 17, cargo 13, pub 8, nuget 6, swift 3, composer 2, go 2, gem 1.

87 repos have `pip install` lines in notebooks, Python files, Dockerfiles or shell scripts; 9 of them have no manifest at all. Those inline packages count toward the `tool` noun but not toward the table below.

### Top 30 dependencies (repos declaring each in a manifest, dev and optional included)

| # | dependency | repos |
| --- | --- | --- |
| 1 | npm:typescript | 218 |
| 2 | pypi:pytest | 206 |
| 3 | npm:react | 201 |
| 4 | npm:react-dom | 195 |
| 5 | npm:@types/react | 185 |
| 6 | pypi:fastapi | 184 |
| 7 | pypi:uvicorn | 181 |
| 8 | npm:@types/node | 173 |
| 9 | npm:@types/react-dom | 172 |
| 10 | pypi:openai | 148 |
| 11 | pypi:pydantic | 148 |
| 12 | pypi:httpx | 142 |
| 13 | pypi:pillow | 121 |
| 14 | npm:tailwindcss | 115 |
| 15 | npm:vite | 108 |
| 16 | pypi:numpy | 105 |
| 17 | pypi:python-dotenv | 103 |
| 18 | npm:next | 96 |
| 19 | npm:@vitejs/plugin-react | 93 |
| 20 | npm:eslint | 91 |
| 21 | npm:vitest | 90 |
| 22 | pypi:python-multipart | 77 |
| 23 | pypi:requests | 72 |
| 24 | npm:zod | 65 |
| 25 | npm:eslint-config-next | 60 |
| 26 | npm:tsx | 55 |
| 27 | pypi:ruff | 55 |
| 28 | npm:lucide-react | 50 |
| 29 | npm:@meta-sam/parser | 49 |
| 30 | pypi:pyyaml | 49 |

## Meta models and the Meta Model API

Repos with any Meta model pattern: 568. Repos with a specific Meta signal (API base URL or SDK, a Muse id, SAM 3, Code Llama, MobileMoE, Muse Glimmer, or a Llama model id such as `llama-3.2` or `meta-llama/`): 563. Repos mentioning any Muse model: 507.

| pattern | repos | mentions |
| --- | --- | --- |
| llama | 186 | 6102 |
| muse-spark | 499 | 55306 |
| muse-wonder | 209 | 10862 |
| muse-image | 232 | 7022 |
| muse-voice | 238 | 4168 |
| glimmer | 148 | 12297 |
| sam-3 | 320 | 13026 |
| segment-anything | 27 | 90 |
| mobilemoe | 1 | 48 |
| codellama | 0 | 0 |

Narrower views of the broad patterns, and Meta models outside the requested list (marked extra):

| view | repos | mentions |
| --- | --- | --- |
| audiocraft/musicgen (extra) | 4 | 61 |
| detectron2 (extra) | 1 | 1 |
| dinov2/dinov3 (extra) | 8 | 280 |
| glimmer:muse-glimmer | 133 | 4949 |
| llama:guard | 9 | 504 |
| llama:llama-stack | 2 | 72 |
| llama:llama.cpp | 43 | 591 |
| llama:llamaindex | 2 | 2 |
| llama:model-id | 99 | 1612 |
| sam-2 (extra) | 17 | 416 |
| seamless (extra) | 6 | 44 |
| v-jepa (extra) | 3 | 30 |

Meta Model API signals (420 repos with a base URL or SDK signal):

| signal | repos |
| --- | --- |
| api.meta.ai | 415 |
| dev.meta.ai (docs link) | 252 |
| META_API_KEY or LLAMA_API_KEY | 186 |
| api.llama.com | 11 |
| llama-api-client | 1 |

Other Meta tools mentioned:

| tool | repos | mentions |
| --- | --- | --- |
| executorch | 12 | 191 |
| faiss | 5 | 212 |
| llama-guard | 3 | 4 |
| llamafirewall | 1 | 11 |
| muse-code | 176 | 6256 |
| prompt-guard | 6 | 343 |
| synthetic-data-kit | 1 | 6 |

## Other models and providers

| pattern | repos | mentions |
| --- | --- | --- |
| gpt- | 91 | 1303 |
| claude | 245 | 10311 |
| gemini | 89 | 4087 |
| mistral | 21 | 226 |
| qwen | 64 | 1663 |
| deepseek | 36 | 1158 |
| whisper | 62 | 762 |
| stable-diffusion | 7 | 22 |
| flux | 32 | 637 |

Stricter model-id views: claude:model-id 38 repos, flux:model-id 7 repos, gemini:model-id 32 repos.

Providers, from SDK dependencies or base URLs in text:

| provider | repos | by signal |
| --- | --- | --- |
| meta-model-api | 415 | base url 415 |
| openai | 201 | base url 37, sdk dependency 188 |
| baseten | 139 | base url 139 |
| huggingface-inference | 52 | base url 34, sdk dependency 21 |
| modal | 45 | base url 33, sdk dependency 23 |
| ollama-local | 37 | base url 35, sdk dependency 4 |
| fireworks | 30 | base url 30 |
| google-gemini | 27 | base url 20, sdk dependency 9 |
| openrouter | 20 | base url 20 |
| anthropic | 19 | base url 9, sdk dependency 13 |
| elevenlabs | 18 | base url 18 |
| groq | 16 | base url 11, sdk dependency 5 |
| meta-llama-api | 11 | base url 11 |
| nvidia-nim | 5 | base url 5 |
| together | 5 | base url 5 |
| deepseek | 3 | base url 3 |
| google-vertex | 2 | base url 2 |
| xai | 2 | base url 2 |
| aws-bedrock | 1 | base url 1 |
| mistral | 1 | base url 1 |
| replicate | 1 | base url 1 |

The Meta Model API docs recommend the OpenAI SDK with a Meta `base_url`: 188 repos declare the OpenAI SDK, and 130 of them also reference `api.meta.ai`.

Local runtimes declared: transformers 37, pytorch 35, peft 14, unsloth 9, onnxruntime 8, mlx 2, vllm 2, tensorflow 1.

Agent and app frameworks declared: streamlit 14, gradio 13, langgraph 7, vercel-ai-sdk 5, langchain 3, haystack 1, livekit-agents 1, pipecat 1.

Repos with committed model weight or model config files: 11.

## MCP

| item | repos |
| --- | --- |
| any MCP signal | 30 (4.3%) |
| MCP SDK dependency | 23 |
| MCP server code (SDK import in a source file) | 24 |
| MCP tool definitions found | 14 repos, 123 tools |
| MCP client config file (.mcp.json and similar) | 5 |

## Prompts, datasets, assets, deployment

| item | repos |
| --- | --- |
| prompt files or prompts/ directories | 73 |
| system-prompt mentions in text | 382 |
| long (200+ character) system-prompt strings in code | 120 |
| dataset files | 174 |
| asset files | 372 |
| .env templates (paths only, never opened) | 339 |

Deployment config files: huggingface-spaces (README front matter) 47, vercel 32, cloudflare-workers 20, render 15, app.json (heroku/expo) 13, firebase 11, expo-eas 5, supabase 5, fly.io 3, aws-sam (template.yaml) 2, browser-extension (manifest.json) 2, netlify 2, railway 2, google-cloud-build 1, procfile (heroku-style) 1, sst 1.

## Directory metadata (copied from the directory, all repos)

| track | repos |
| --- | --- |
| Build for Your World | 583 |
| Push the Frontier | 108 |
| Track 1: Build for Your World | 45 |
| Track 2: Push the Frontier | 3 |

| domain | repos |
| --- | --- |
| General & Emerging Applications | 178 |
| Multimodal Vision & Video (SAM / Vision) | 123 |
| Autonomous Agents & Workflow Automation | 59 |
| Developer Tooling, Infra & Security | 58 |
| Gaming, Entertainment & Creative Media | 57 |
| Healthcare, Civic Tech & Sustainability | 56 |
| Voice, Speech & Audio AI | 44 |
| Education & Knowledge Systems | 43 |
| Business, Sales & Commerce | 41 |
| Developer Tooling & Infrastructure | 27 |
| Consumer & Productivity | 21 |
| Robotics, IoT & Manufacturing | 14 |
| Finance, Crypto & Web3 | 12 |
| Legal & Compliance | 6 |

### Directory flags compared with this scan (scanned repos)

The directory publishes its own yes/no fields. This only counts how often they match this scanner's evidence.

| comparison | both yes | directory yes, scan no | directory no, scan yes | both no | agreement % |
| --- | --- | --- | --- | --- | --- |
| has_tests vs tests.present | 322 | 6 | 148 | 229 | 78.2 |
| has_ci vs ci.present | 145 | 5 | 7 | 548 | 98.3 |
| has_docker vs dockerfile or compose | 119 | 0 | 40 | 546 | 94.3 |
| meta_api_verified vs meta_api.present | 267 | 39 | 153 | 246 | 72.8 |
