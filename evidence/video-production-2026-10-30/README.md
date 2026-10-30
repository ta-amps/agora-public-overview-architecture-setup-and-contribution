# Evidence: how the Eranos video was made

This bundle backs the video's closing line: "This entire video was made from nouns and verbs, claimed and finished by workers on Tessera, with a receipt for every step." It covers the production run that made both published cuts: the 3:00 cut ("Full · 3 min") and the 60 s cut ("Short · 1 min").

Run `python3 verify.py` in this folder. It needs only the Python standard library, and it checks four things:

1. All 16 receipts recompute from their tasks' outputs.
2. Every input that came from an earlier task is one of that task's receipted outputs.
3. Every noun value matches its pin.
4. Every published file in `media.json` traces back to a receipt.

## Files

| File | Bytes | SHA-256 | What it is |
|---|---|---|---|
| `production-receipts.json` | 55,720 | 38b789149a6fa347e7dee32cb0bfaae6a74a8b747544cd82dcdb7b0028487270 | Every verb and task, its receipt and outcome, and the nouns it made, read from the store |
| `media.json` | 3,757 | c516e5ee26f42d4317f13a79cb16dbf78b25283e25ca8be5a434478d067cde12 | Path, SHA-256 and bytes of every published file (MP4, WebVTT, SRT, poster, QA report) |
| `eranos-3m.video-qa.json` | 4,981 | e5109265a1504e4617cda8c871b82f5c34bffaa13b9404a745e9737e284bad70 | QA report, 3:00 caption-free MP4 |
| `eranos-3m-open-captions.video-qa.json` | 5,029 | 0cf68fe4c03958fca3249f64b8c315c2507f4da892eea37d8e143b1525b7dd32 | QA report, 3:00 open-captions render (source of `eranos-3m.vtt`) |
| `eranos-60s.video-qa.json` | 4,979 | ecd2875d2e6cfa8b032cbce9774ac2065b71817ebcaef013598a6cba4c5daf39 | QA report, 60 s caption-free MP4 |
| `eranos-60s-open-captions.video-qa.json` | 5,024 | f7c1303c3dc948eb6808cf8d6b75b4bc412312d1927b7ce55d048541f073615e | QA report, 60 s open-captions render (source of `eranos-60s.vtt`) |
| `receipts-verify.json` | 459,869 | 0a29cab4183da6d75fa1126d56a73520b1ec984ed884f781858d3a820a28770e | For each task: its input pins, its verbatim output and its receipt. Also the nouns that tie each published file to a receipt. |
| `verify.py` | 2,159 | 96160b688e4e933608ee2cc6aba7051237e0f05093cf541788ac5091792d056d | The checker described above |

No file needed changing for this bundle: none contained a local absolute path, credential or personal data.

- The first six files are byte-identical copies of the delivered files.
- `production-receipts.json` names the store by a relative path.
- The `k_…` values are local key IDs, not secrets. No key secret was ever written to disk.

## The run

The final production ran on October 30, 2026, from 02:15 to 02:35 EDT.

**Where it ran.** One local Tessera store, at commit 2e7d6ab of tessera-infrastructure-work-and-storage-engine. It ran in-process on SQLite with content-addressed blobs.

**Who did the work.** Three keys:

- the requester enqueued each task once everything it depends on had a receipt with its success outcome;
- the production worker claimed and did the production verbs;
- a separate check worker claimed only check-video.

**7 verbs, 16 tasks, 16 receipts:**

- write-script ×2
- capture-screens
- make-narration
- write-captions ×2
- compose-sequence ×2
- render ×4: a caption-free and an open-captions render of each cut
- check-video ×4

Every task finished on its first attempt, with its verb's success outcome.

**No model calls.** No model API, provider or paid service was called:

- The voice is Kokoro-82M (voice af_heart), run locally on the CPU.
- The caption check is wav2vec2-base-960h, also local.
- The volunteers' agents and the steward in the recorded kit run are scripted.

**Network.** Only read-only GETs of public pages, when the screens were captured:

- Eranos's home, /help and /nonprofits;
- Agora's home and /use-cases/;
- seven slides of Agora's live decks;
- Tessera's public `llms.txt`, for its tool count.

## How a receipt binds inputs to outputs

- **Inputs.** Each task's brief names its input nouns by exact pin: store, key, version and value SHA-256. The requester fills those slots only from receipted outputs of the tasks it depends on, or from its own setup nouns.
  - In `receipts-verify.json`, the 16 tasks name 151 input pins.
  - 132 of them are outputs of earlier receipted tasks.
  - 19 are uses of 16 setup nouns: the two video briefs, the capture plan, shot list, cut plan, narration plan, the stage, and nine unchanged voice-set lines.
- **Outputs.** Each verb's output lists every noun it made by exact pin, together with its acceptance checks.
- **Receipt.** Tessera's rule is `receipt = sha256(canonical_json({task_id, fencing_token, ok, output, error}))`:
  - The fencing token comes from the worker's lease, so a receipt proves which lease wrote which output.
  - Changing one byte of an output, or one output noun's digest, changes the receipt.
  - Identical work gives identical receipts: the two write-script receipts are the same in every draft run and in this run.
- **Published files.** Each file in `media.json` traces back to a receipted output through pinned nouns, listed under `published_files` in `receipts-verify.json`:
  - The MP4: render receipt → video noun → `asset.blob_sha256`.
  - The poster: render receipt → render bundle → poster noun.
  - The WebVTT and SRT: open-captions render receipt → render manifest.
  - Each QA file is the value of the QA noun its check-video receipt names.
- **The reveal board.** compose-sequence drew each board from the store while it ran. The 60 s board read 6 receipts at 02:20:42, and the 3:00 board read 7 receipts at 02:21:55. Render and check-video receipts come after the board, as its footer says.

## Earlier draft runs

Four draft stores came before this run. They stay in the local workspace and are not in this bundle. Each began from a fresh store.

| Store (EDT) | What happened | Fix |
|---|---|---|
| draft-run (01:23) | **Blocked.** write-captions for the 3:00 cut returned outcome *blocked* (receipt 0bdfda4b…). Its speech check compared the voice with written digits ("12" against a spoken "twelve"), and the checker misheard "Nonprofits" on a short trimmed line. | The check now compares against the line as spoken, with numbers as words. A short list of the checker's known mishearings applies only to lines over the limit, and each use is recorded. |
| draft-run-2 (01:31) | **Blocked twice.** compose-sequence for the 3:00 cut was blocked on both attempts. Attempt 1 (e1576f1c…): the video pack's pre-render QA found 46 identical frames on the reveal board, over its 45-frame (1.5 s) limit. Attempt 2 (ae5f57e0…): its search noun collided with the one attempt 1 had written under the same key. | The board's verbs now arrive 0.4 s apart. Nouns that depend on the moment now carry the attempt in their key. |
| draft-run-3 (01:44) | **Stopped by the operator.** It was stopped during make-narration, so that task has no receipt. A test render of the 3:00 cut at CRF 20 measured 58 MB, over the roughly 40 MB budget for GitHub Pages. | The 3:00 cut now renders at CRF 25 (34.7 MB). |
| draft-run-4 (01:49–02:06) | **Finished.** This is the draft that was published first: 11 tasks, 11 receipts. This run superseded it. | No DRAFT tag. A slow camera drift removes a 2 s freeze that the draft's QA found. |

## What is not claimed

- **The store is not public.** Nobody else can query the local Tessera store or its blobs. This bundle holds what you need to recompute the receipts and follow the chain, but the receipts are not anchored to a public log or to the hosted Tessera service.
- **The voice is AI-generated.** It is Kokoro-82M, voice af_heart, and labeled on screen.
- **The kit run is a local run with synthetic data.**
  - Its agents and the steward are scripted stand-ins.
  - It used a local, unmerged branch of Eranos and of the seed-pack library for the handwritten-statements kit.
  - The sort-and-split step is shown as a labeled illustration.
- **QA is the video pack's automated checks.**
  - Both open-captions renders pass 8 of 8.
  - Both caption-free MP4s pass 7 of 8. They fail caption coverage by construction, because their captions ship as the WebVTT files.
  - No person has reviewed the cuts frame by frame yet.
- **The learning results are quoted, not re-measured.** The learning slide's numbers are the deck's own results on synthetic tasks.
- **Live captures are a snapshot.** They show the public pages as they were at 02:15–02:17 EDT.
