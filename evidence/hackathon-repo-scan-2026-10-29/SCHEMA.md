# Schema: `repos/<owner>__<name>.json` (hackscan.repo/1)

One file per unique repository in the Watt Mind directory of the Meta Global AI Hackathon 2026
(`raw/02-projects-json/projects.json`). The file is a pure function of three inputs: the repository tree at the
pinned commit, the directory row(s) for that URL, and the scanner version. Re-running the scanner on the same
commit and the same directory snapshot gives a byte-identical file.

Everything was read as untrusted data. Nothing in any repository was executed, installed or opened in a browser,
and no model was called. Every list of paths is sorted before it is capped, so caps are deterministic, and every
capped list sits next to an uncapped `count`.

Vocabulary follows the workspace rule in `MUST-FOLLOW.md`: **nouns** are reusable things (docs, code, tools and
dependencies, models, prompts, datasets, assets, config, tests and evaluations); **verbs** are independently
schedulable work (scripts, CLI commands, HTTP routes, MCP and agent tools, CI jobs, Makefile targets, scheduled
jobs). Everything here is a *candidate* noun or verb found by fixed patterns, not a reviewed or admitted one.

## Top level

| Field | Type | Meaning |
| --- | --- | --- |
| `schema` | string | `hackscan.repo/1` |
| `scanner` | object | `{name, version}` of the scanner that wrote the file |
| `key` | string | `<owner>__<name>`, spelled as in the directory URL |
| `status` | `ok` or `failed` | Failed repos keep `identity` and `failure` only |
| `identity` | object | See below |
| `failure` | object or null | `{reason, detail}` when `status` is `failed` |
| `basics`, `docs`, `dependencies`, `models`, `providers`, `prompts`, `datasets`, `assets`, `config`, `mcp`, `verbs`, `classification` | objects | Present when `status` is `ok` |

### `failure.reason` values

| Reason | Meaning |
| --- | --- |
| `not_found_or_private` | GitHub refused anonymous HTTPS: the repository is deleted, renamed away or private. These cannot be told apart without credentials, and none are used |
| `empty_repository` | Clone succeeded but there is no commit |
| `timeout` | `git clone` exceeded 120 seconds (after the retry pass, if any) |
| `network_error` | DNS, TLS, HTTP 5xx or 429, or a dropped connection, after two in-run retries with backoff |
| `unavailable` | Disabled by GitHub (for example a DMCA takedown) |
| `clone_error` | Any other git error; `detail` has git's last line |
| `scanner_error`, `scanner_timeout` | The scanner failed on this repo; recorded rather than dropped |
| `invalid_url` | The directory row is not a plain `https://github.com/<owner>/<name>` URL |

## `identity`

| Field | Meaning |
| --- | --- |
| `url`, `owner`, `name` | From the directory's `html_url`, validated against a strict pattern |
| `directory_entries` | Every directory row with this URL, **copied as given** (all fields, including Watt Mind's own `track`, `domain`, `summary`, flags, scores and ranks). Usually one row; `Vaibhav-CD/SmartINK` has two. The scanner never reads the scores or ranks, and the summaries never aggregate them |
| `head_sha` | Commit the extraction is pinned to (HEAD of the default branch at clone time) |
| `default_branch` | Branch the remote HEAD pointed to |
| `head_committed_at` | Committer date of `head_sha` (ISO 8601, from the commit object) |
| `clone.method` | The exact clone procedure |
| `clone.clone_time_recorded_in` | `runs/clone-log.json`. Clone time is kept there, not in this file, because a wall-clock time would make the same commit produce a different file on every run |

## `basics`

`tree` totals:

| Field | Meaning |
| --- | --- |
| `files_total` | Blob and symlink entries in the tree (submodule links are listed separately) |
| `files_vendored`, `vendored_dirs` | Files under vendored or build-output directories (`node_modules`, `.venv`, `venv`, `site-packages`, `vendor`, `dist`, `build`, `target`, `.next`, `__pycache__` and similar; full list in `scanner/hs_patterns.py`). They are counted and never read |
| `files_considered` | `files_total - files_vendored`. All other counts use these files |
| `files_large_unfetched` | Blobs of 1 MiB or more. The clone filter left them out; they count by path only |
| `files_text_scanned`, `files_binary_by_content`, `text_bytes_scanned` | Blobs actually read and treated as text (no NUL byte in the first 8,000 bytes) |
| `lines_total` | Lines in scanned text files, excluding lockfiles and minified or generated files. Assets, datasets, model files, env files and possible credential files are not read, so their lines are not counted |
| `code_lines` | Lines in scanned files whose category is `code` or `test_evaluation` and whose language is a programming or markup language |
| `symlinks`, `submodules` | Symlinks are never followed. Submodules are never fetched; their paths are listed |
| `text_budget_exhausted` | True if a repo exceeded 256 MiB of text, after which remaining files count by path only |

`license`:

| Field | Meaning |
| --- | --- |
| `id` | SPDX-like id recognised from root `LICENSE*`, `LICENCE*`, `COPYING*` or `UNLICENSE` text (Unity `*.meta` sidecar files excluded); `none found` if there is no such file; `NOASSERTION` if the text is not recognised; `MULTIPLE(a,b)` if root files disagree. An `SPDX-License-Identifier:` line wins. Non-SPDX results: `LicenseRef-Llama-<version>-Community`, `LicenseRef-Meta-SAM-License` (Meta's SAM License), `LicenseRef-proprietary` ("All rights reserved" with no grant of permission), `LicenseRef-PolyForm` (unrecognised PolyForm variant) |
| `files` | Each root licence file and the id its text matched |
| `declared_in_manifests` | `license` fields from `package.json`, `pyproject.toml`, `Cargo.toml` and `composer.json`, reported separately and never used for `id` |

`languages`: `by_files` counts files by extension (and by name for `Dockerfile`, `Makefile`, `CMakeLists.txt`) for
programming and markup languages, vendored and generated files excluded; `by_lines` counts lines of scanned files;
`primary_by_files` is the language with the most files (ties broken by lines, then name); `extensions_top` is the 30
most common extensions across all considered files.

`tests`: `present` is true when at least one test file exists. Test files match `test_*.py`, `*_test.py`,
`*.test.ts`, `*.spec.js`, `*_test.go`, `*Test.java`, `*_spec.rb`, `conftest.py` and similar, or are code files under
`test/`, `tests/`, `__tests__/`, `spec/`, `e2e/`, `cypress/`, `playwright/`; Rust files with `#[test]` also count.
`test_config_files` (pytest.ini, jest/vitest/playwright configs ...) and `evaluation_files` (files under `eval/`,
`evals/`, `evaluation/`, `benchmarks/` ..., or named `eval_*`, `evaluate*`, `benchmark*`) are listed separately.
`frameworks` comes from declared dependencies.

`ci`: `github_actions` lists each `.github/workflows/*.yml` with its `name`, `triggers` (keys under `on:`), `jobs`
(`id` and display `name`) and cron `schedules`, read by a small indentation-based reader, not a YAML library.
`other` lists other CI systems by file (GitLab, CircleCI, Azure Pipelines, Travis, Jenkins, Bitbucket, Buildkite,
Drone or Woodpecker, Cloud Build).

`docker`: Dockerfiles (`Dockerfile`, `Dockerfile.*`, `*.dockerfile`), compose files with their service names, and
devcontainer files.

## `docs`

| Field | Meaning |
| --- | --- |
| `readme.path` | Shallowest `README`, `README.md`, `.rst`, `.txt` and so on; Markdown wins a tie |
| `readme.title` | First level-1 heading (Markdown, setext, reStructuredText or HTML `<h1>`), else the first heading, else front-matter `title` |
| `readme.first_paragraph` | First prose block of 5+ words and 30+ characters, skipping headings, badges, images, tables, code, lists and HTML-only lines, with Markdown stripped and possible credentials redacted. At most 400 characters; `first_paragraph_truncated` says if it was cut |
| `readme.huggingface_space_front_matter` | README starts with front matter containing `sdk:` |
| `doc_files` | Files in the `docs` category (Markdown, reStructuredText, text, PDF, LICENSE, CHANGELOG ...) |
| `agent_instruction_files` | `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `copilot-instructions.md`, `llms.txt`, and Markdown or text files under `.cursor/rules/`, `.claude/`, `.agents/`, `.github/instructions/`, `.windsurf/rules/`, `.clinerules/`, `.muse/`. Code under those folders (hooks, workflow scripts) is classified as code |

## `dependencies` (tool nouns)

`manifests` lists each parsed manifest: `path`, `ecosystem` (`npm`, `pypi`, `go`, `cargo`, `gem`, `composer`,
`maven`, `conda`, `pub`, `nuget`, `swift`, `deno`), `dependencies`, `dev_dependencies` and
`optional_dependencies` (peer, optional, extras, Go `// indirect`, conda `pip:` entries), each a map of name to
version spec, plus `parse_error`. Sources: `package.json`; `pyproject.toml` (PEP 621, Poetry, PEP 735 groups, uv);
`requirements*.txt` and `requirements/*.txt`; `setup.py` and `setup.cfg`; `Pipfile`; `environment.yml`;
`go.mod`; `Cargo.toml`; `Gemfile`; `composer.json`; `pom.xml`; `build.gradle(.kts)` and
`gradle/libs.versions.toml`; `pubspec.yaml`; `*.csproj`; `Package.swift`; `deno.json`. Python names are
normalised (PEP 503). Up to 300 manifests per repo, shallowest first. `distinct` is the sorted set of
`ecosystem:name` across all manifests; `distinct_count` is its size.

`inline_pip_installs` lists `pip install ...` commands found in Python files, notebook code cells, Dockerfiles and
shell scripts, as `{path, packages}` (`inline_pip_install_files` is the uncapped file count). Options, paths, URLs
and `-r` files are skipped. `inline_only_packages` are those not already in `distinct`. The `tool` noun count is
`distinct_count` plus `inline_only_packages`. Import statements are not parsed.

## `models`

Mentions are case-insensitive regular-expression matches over scanned text files (code, docs, config, prompts,
tests). Each entry is `{mentions, files, examples}` where `examples` are the first five paths in path order.
A mention is text, not proof that a model is called.

| Block | Patterns |
| --- | --- |
| `meta` | `llama`, `muse-spark`, `muse-wonder`, `muse-image`, `muse-voice`, `glimmer`, `sam-3` (also `sam3`, `SAM 3.1`, `sam-3-1`), `segment-anything`, `mobilemoe`, `codellama` |
| `meta_detail` | Narrower views: `llama:model-id` (`llama-3.2`, `llama4`, `meta-llama/`), `llama:llamaindex`, `llama:llama.cpp`, `llama:llama-stack`, `llama:guard`, `glimmer:muse-glimmer`; and Meta models outside the requested list, marked `(extra)`: `sam-2`, `v-jepa`, `dinov2/dinov3`, `imagebind`, `seamless`, `audiocraft/musicgen`, `nllb`, `cotracker`, `detectron2`. Extras do not count toward the `model` noun |
| `meta_api` | `present` is true for `api.meta.ai` (the Meta Model API base URL), `api.llama.com` (Llama API) or `llama-api-client`. `signals` also counts `META_API_KEY`/`LLAMA_API_KEY` and `dev.meta.ai` doc links, which do not set `present` |
| `meta_tools` | `muse-code`, `llamafirewall`, `prompt-guard`, `llama-guard`, `synthetic-data-kit`, `faiss`, `executorch` |
| `other` | `gpt-`, `claude`, `gemini`, `mistral`, `qwen`, `deepseek`, `whisper`, `stable-diffusion` (or `sdxl`), `flux` |
| `other_detail` | Stricter ids: `claude:model-id`, `gemini:model-id`, `flux:model-id` |
| `model_files` | Files in the `model` category: weights (`.safetensors`, `.gguf`, `.onnx`, `.pt`, `.pth`, `.ckpt`, `.tflite` ...), `Modelfile`, adapter configs, and `.bin`/`.h5`/`.pkl` under `models/`, `weights/`, `checkpoints/` |
| `local_runtimes`, `frameworks` | Derived from declared dependencies and inline `pip install` packages (for example `transformers`, `vllm`, `torch`; `langchain`, `crewai`, `streamlit`), each `{name, evidence}` |

## `providers`

Hosted model providers, each with `signals` (`sdk dependency`, `base url`) and up to five `evidence` items
(manifest path and package, or file path). `base url` means an API host appears in a scanned text file (code or
docs): `api.meta.ai`, `api.llama.com`, `api.openai.com`, `api.anthropic.com`, `generativelanguage.googleapis.com`,
`api.groq.com`, `openrouter.ai/api`, `api.fireworks.ai`, `inference.baseten.co` and `*.api.baseten.co`, Hugging
Face inference hosts, `*.modal.run`, local Ollama (`:11434`) and others in `scanner/hs_patterns.py`. Marketing
domains alone (`baseten.co`, `openrouter.ai`) do not count. An OpenAI SDK dependency is reported as `openai` even
when it is pointed at another base URL; the Meta Model API docs recommend exactly that.

## `prompts`, `datasets`, `assets`, `config`

| Block | Contents |
| --- | --- |
| `prompts.prompt_files` | Files under `prompts/`-style directories, `*.prompt`, `*.prompty`, `*.prompt.md`, and text/YAML/JSON/Jinja files with `prompt` in the name |
| `prompts.system_prompt_mentions` | Matches for `system_prompt`, `systemPrompt`, `system_instruction`, `"role": "system"` |
| `prompts.long_system_prompt_strings` | Code strings of 200+ characters assigned to a `system...prompt/message/instruction` name, or `"role": "system", "content": "..."` |
| `datasets` | Files in the `dataset` category (`.csv`, `.tsv`, `.jsonl`, `.parquet`, `.npy`, `.sqlite`, `.xlsx` ..., and JSON/text/YAML under `data/`, `datasets/`, `corpus/`), with counts by extension. Never read |
| `assets` | Images, audio, video, fonts, 3D and animation files, with counts by kind. Never read |
| `config.files` | Files in the `config` category: manifests, lockfiles, CI, Docker, deploy files, JSON/YAML/TOML/INI and dotfiles |
| `config.env_templates_unread` | Paths of `.env.example`-style templates. Never opened |
| `config.sensitive_named_files_unread` | Count only, no paths, of other `.env*`, `*.local.json`, key, certificate and credential-named files. Never opened |
| `config.deploy_hints` | Deployment config by file: `wrangler.*`, `vercel.json`, `netlify.toml`, `fly.toml`, `render.yaml`, `railway.*`, `Procfile`, `firebase.json`, `app.yaml` and others, plus Hugging Face Spaces front matter and browser-extension `manifest.json` (with `manifest_version`) |
| `config.cloudflare_worker_entries` | `main` entry of each wrangler config |

## `mcp`

`sdk_dependencies` (for example `npm:@modelcontextprotocol/sdk`, `pypi:mcp`, `pypi:fastmcp`),
`server_code_files` (source files importing an MCP SDK), `tool_definitions` and `tool_names` (from
`server.tool("x")`, `registerTool("x")`, `@mcp.tool` with the decorated function name, `Tool(name="x")`, and
`{name, description, inputSchema}` tool lists), `client_config_files` (`.mcp.json`, `mcp.json`,
`claude_desktop_config.json`, `.cursor/mcp.json`, `.vscode/mcp.json`, `smithery.yaml`), `schema_mentions`
(`inputSchema`, `input_schema`, `"type": "function"`), and `adopted` (any of the above).

## `verbs`

`items` is a list of candidate verbs sorted by `(kind, evidence, name, detail)`, at most 100 per kind (see
`items_truncated_kinds`); `count`, `by_kind` and `by_category` are uncapped. Each item:

```json
{"kind": "http_route", "name": "POST /api/assign", "category": "run_serve", "evidence": ["src/app.py"], "detail": "fastapi"}
```

| Kind | Source |
| --- | --- |
| `npm_script` | `package.json` `scripts`; `detail` is the command (credentials redacted, 200 characters at most) |
| `console_entry_point` | `package.json` `bin`, `[project.scripts]`, `[tool.poetry.scripts]`, `setup.py`/`setup.cfg` `console_scripts`, Cargo `[[bin]]`, Go `package main` with `func main()` |
| `make_target` | Makefile and `*.mk` rule targets (not `.PHONY`, pattern or variable targets); `justfile` recipes (`detail: just`) |
| `task_target` | `Taskfile.yml` tasks |
| `http_route` | `name` is `METHOD /path` (`*` when the method is not cheaply known). FastAPI, Flask, Quart, Sanic, Starlette and aiohttp decorators or route calls; Django `urls.py`; Express, Hono, Fastify, Koa, itty-router and Elysia `x.get('/path', ...)` in files that import them; NestJS decorators; Next.js `app/**/route.ts` (exported methods) and `pages/api/**`; SvelteKit `+server.ts`; Nuxt `server/api`; Netlify, Supabase, Vercel `api/`, Firebase and Cloudflare Pages functions; Cloudflare Worker `fetch` handlers and their `pathname` checks; Deno and Bun servers; Go `net/http`, gin, echo, chi; Rust axum and actix; Spring; Laravel; Sinatra/Rails. `detail` names the framework |
| `mcp_tool` | MCP tool definitions (see `mcp`) |
| `agent_tool` | Function-calling tool schemas: `"type": "function"` with a `name`, or `{name, description, parameters: {type: "object"}}` objects in Python, JavaScript/TypeScript or JSON (JSON only for config, prompt or code files outside docs, evidence, traces, logs, examples, fixtures, specs, tests, data, eval and results folders, which hold recorded data); Anthropic-style `input_schema` tools; Python `@tool`, `@function_tool`, `@kernel_function`, `@agent.tool`; Vercel AI SDK `name: tool({...})` |
| `cli_command` | argparse `add_parser`, click and typer commands, commander/yargs/cac/oclif `.command()`, cobra `Use:` |
| `ci_job` | One per GitHub Actions job; `detail` is the job's display name |
| `scheduled` | Cron schedules from GitHub Actions, wrangler `crons`, `vercel.json` `crons`, Kubernetes CronJobs and crontab files; Cloudflare `scheduled()` handlers; node-cron, `cron` package, APScheduler, Python `schedule`, Celery beat, Modal `Cron`/`Period`, Inngest or Trigger.dev crons, pg_cron; browser-extension `chrome.alarms.create` |
| `script` | Shell, PowerShell and batch scripts; script-language files (Python, JavaScript, TypeScript, Ruby, PHP, Go, Rust, Lua, R, Perl ...; not HTML, CSS or compiled-language sources) under `scripts/`, `script/` or `bin/` or with the executable bit; files with a shebang; Python files with an `if __name__ == "__main__":` guard. Test files are excluded |
| `compose_service` | Service names in compose files |
| `container_build` | One per Dockerfile |
| `procfile_process` | `Procfile` process types |
| `precommit_hook` | Hook ids in `.pre-commit-config.yaml`, lefthook `pre-commit` commands, and `.husky/<hook>` files |

Verbs are not extracted from inside test files (only their existence counts as test evidence). Jupyter notebooks
are decoded and their code cells scanned like Python files (routes, tools, CLI commands, schedulers, `pip install`
lines), but a notebook is not itself listed as a `script`.

`category` is exactly one of `build`, `run_serve`, `test_check`, `deploy`, `data_processing`, `agent_tool`,
`scheduled`, `other`. `mcp_tool` and `agent_tool` are always `agent_tool`; `scheduled` is `scheduled`; routes,
compose services and Procfile processes are `run_serve`; Dockerfiles are `build`. Other kinds use ordered keyword
rules on the name (then the command for npm scripts and Makefile targets, the job body for CI jobs, and the
directory for scripts); first match wins: data processing (strong: `db`, `migrate`, `seed`, `prisma` ...), deploy,
test/check, build, data processing (weak: `ingest`, `scrape`, `train`, `embed`, `export` ...), run/serve. With no
match, CLI commands, entry points and scripts default to `run_serve`, and npm scripts, Makefile targets and CI jobs
to `other`. The rules are in `scanner/hs_patterns.py`.

## `classification`

| Field | Meaning |
| --- | --- |
| `nouns` | Counts per noun category: `docs`, `code`, `prompt`, `dataset`, `asset`, `config` and `test_evaluation` are file counts (each considered file has exactly one category); `tool` is `dependencies.distinct_count`; `model` is model files plus distinct model patterns (from `models.meta` and `models.other`) with at least one mention; `prompt` adds long system-prompt strings to prompt files |
| `files_by_category` | File counts per category, including `other` for files that fit none |
| `verbs`, `verb_kinds` | Copies of `verbs.by_category` and `verbs.by_kind` |

File category precedence (first match wins): possible credential or env file → `config`; agent instruction file →
`docs`; test or evaluation path → `test_evaluation`; prompt path → `prompt`; model weight or model config →
`model`; CI, Docker, compose, manifest, lockfile, deploy or MCP config, `.github/` → `config`; dataset → `dataset`;
asset → `asset`; known config name → `config`; doc extension, doc name or `docs/` directory → `docs`; config
extension → `config`; programming or markup extension → `code`; otherwise `other`.

## Other outputs

| File | Deterministic? | Contents |
| --- | --- | --- |
| `summary.json`, `summary.md` | Yes | Aggregate, descriptive counts across all repo files. No ranking, scoring or judging of teams |
| `all.csv` | Yes | One row per repo with headline counts. Text cells that start with `=`, `+`, `-` or `@` get a leading `'` so spreadsheets do not treat them as formulas |
| `runs/clone-log.json` | No (wall-clock) | Per repo: every attempt (oldest first) with run id, scanner version, clone time, duration, exit code, network retries, bytes on disk before deletion, extraction time, outcome and pinned commit; `latest` is the attempt that wrote the current repo file |
| `runs/run-<id>.json`, `runs/attempts-<id>.jsonl` | No | Per run: start and end, wall time, peak and total clone bytes, outcome counts, git and Python versions. Every pass is kept, including the superseded 1.0.0 pass and two passes stopped early (`"interrupted": true`); all current repo files come from scanner 1.2.0 |
| `raw/SOURCES.json` | n/a | URL, fetch time, sha256 and size of each downloaded directory file |
