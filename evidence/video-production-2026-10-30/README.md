# Evidence: how the Eranos video (v2) was made

This bundle backs the closing line of the v2 cuts: "This entire video was made from nouns and verbs, claimed and finished by workers on Tessera, with a receipt for every step." It covers the production run that made both v2 cuts, the 3:00 cut ("Full · 3 min") and the 60 s cut ("Short · 1 min"). The v1 run has its own bundle, `evidence-bundle/`.

Run `python3 verify.py` in this folder. It needs only the Python standard library, and it checks four things:

1. All 16 receipts recompute from their tasks' outputs.
2. Every input that came from an earlier task is one of that task's receipted outputs.
3. Every noun value matches its pin.
4. Every published file in `media.json` traces back to a receipt.

## Files

| File | Bytes | SHA-256 | What it is |
|---|---|---|---|
| `production-receipts.json` | 57,083 | 2baa1634f135457cab4c5ca3cff344e2198164848e2ed7d5200d5834c34057b9 | Every verb and task, its receipt and outcome, and the nouns it made, read from the store |
| `media.json` | 3,763 | 357db5d1e343816e87fff41695cbff7fb6759ab277b32fd6b0fa6ccc31970051 | Path, SHA-256 and bytes of every published v2 file |
| `eranos-3m.video-qa.json` | 4,982 | 9fc7ea94604947a0ddb26169d053c16c32e0ec3cc4ea546c16357402bb50dcf9 | QA report, 3:00 caption-free MP4 |
| `eranos-3m-open-captions.video-qa.json` | 5,029 | b24b8b692107292642944d7ce562b81bb792a0932f1f35f51e3065f17fb3c3c8 | QA report, 3:00 open-captions render (source of `eranos-3m.vtt`) |
| `eranos-60s.video-qa.json` | 4,979 | e0a3161bedb4708507143e8c8950df45485c1be6d2df8b923b52b5b0b3d7348a | QA report, 60 s caption-free MP4 |
| `eranos-60s-open-captions.video-qa.json` | 5,023 | c97bd39ce4ec592b404ef30e07cb4f52128e465332ceffbb3591dec9f24ad996 | QA report, 60 s open-captions render (source of `eranos-60s.vtt`) |
| `receipts-verify.json` | 464,952 | b344227c1bcdd8c6c6ade6180c60d5371ceae0ede4663867bd017ea461c4b36c | For each task: its input pins, its verbatim output and its receipt. Also the nouns that tie each published file to a receipt. |
| `verify.py` | 2,159 | 96160b688e4e933608ee2cc6aba7051237e0f05093cf541788ac5091792d056d | The checker described above (unchanged from v1) |

No file needed changing for this bundle: none contained a local absolute path, credential or personal data.

- The first six files are byte-identical copies of the files in `final-v2/`.
- `production-receipts.json` names the store by a relative path.
- The `k_…` values are local key IDs, not secrets. No key secret was ever written to disk.

## The run

The v2 production ran on October 30, 2026, from 08:46 to 09:13 EDT.

**Where it ran.** One local Tessera store, `production-run-v2`, at commit 2e7d6ab of tessera-infrastructure-work-and-storage-engine. It ran in-process on SQLite with content-addressed blobs.

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

**Network.** Only read-only GETs of public pages, during capture-screens:

- the redeployed Eranos site (version e34558b8): home, /help and /nonprofits;
- Agora's home and /use-cases/;
- seven slides of Agora's live decks;
- Tessera's public `llms.txt`, for its tool count.

**The request box.** The synthetic need was typed into the live /nonprofits box with `fill()`: no click, no Enter, no submit. The capture records `"sent": false`. The box was cleared before the page closed.

## How a receipt binds inputs to outputs

- **Inputs.** Each task's brief names its input nouns by exact pin: store, key, version and value SHA-256. The requester fills those slots only from receipted outputs of the tasks it depends on, or from its own setup nouns.
  - In `receipts-verify.json`, the 16 tasks name 161 input pins.
  - 142 of them are outputs of earlier receipted tasks.
  - 19 are uses of 16 setup nouns: the two video briefs, the capture plan, shot list, cut plan, narration plan, the stage, and nine unchanged voice-set lines.
- **Outputs.** Each verb's output lists every noun it made by exact pin, together with its acceptance checks.
- **Receipt.** Tessera's rule is `receipt = sha256(canonical_json({task_id, fencing_token, ok, output, error}))`:
  - The fencing token comes from the worker's lease, so a receipt proves which lease wrote which output.
  - Changing one byte of an output, or one output noun's digest, changes the receipt.
  - Identical work gives identical receipts: the two write-script receipts (a2cd9a79…, 7e38e35c…) are the same as in v1.
- **Published files.** Each file in `media.json` traces back to a receipted output through pinned nouns, listed under `published_files` in `receipts-verify.json`:
  - The MP4: render receipt → video noun → `asset.blob_sha256`.
  - The poster: render receipt → render bundle → poster noun.
  - The WebVTT and SRT: open-captions render receipt → render manifest.
  - Each QA file is the value of the QA noun its check-video receipt names.
- **The reveal board.** compose-sequence drew each board from the store while it ran, and counts the receipts up as it reads them. The 60 s board read 6 receipts at 08:58:17, and the 3:00 board read 7 receipts at 08:59:56. Render and check-video come after the board and are marked "after this board".
- **The fixes slide.** Its search panel shows real calls that vf.compose-sequence-3m made while it held its lease:
  - search_nouns("narration") found 48 nouns.
  - recall_execution found vf.compose-sequence-60s as a compatible method, with score 0.906.

## What changed from v1

- **Recaptured:** every Eranos screen, live from the redeployed site.
- **Readable pages:**
  - Pages are captured at narrow viewports (600–850 CSS px, device scale 2, tall pages in tiles), so they reflow instead of being cropped.
  - Each is framed at about 2×, so body text is about 28 px at 1080p.
  - Each shot has a ring and a short label for what to notice.
  - The review, steward and volunteer terminals are stacked full width at 26–28 px.
- **The need shot** opens on the live request box, with the synthetic need typed in stages and labelled SYNTHETIC EXAMPLE, not sent. The sorting that follows is still a labelled illustration.
- **The map slide** is framed on a region with no cut line.
- **The reveal board** fills the frame and counts its receipts up.
- **The end card** shows the live Eranos hero next to Agora's home.
- **Checks:** both v2 renders were scanned with the video pack's freezedetect settings and found no freeze. QA matches v1: 8 of 8 on both open-captions renders, and 7 of 8 on both caption-free MP4s.

## Earlier runs

None of these earlier stores is in this bundle. All stay in the local workspace.

| Store (EDT) | What happened |
|---|---|
| draft-run (01:23) | **Blocked.** write-captions for the 3:00 cut returned outcome *blocked*, receipt 0bdfda4b…. Its speech check compared the voice with written digits, and it misheard "Nonprofits" on a short line. Fixed by checking against the line as spoken, plus a short recorded list of known mishearings. |
| draft-run-2 (01:31) | **Blocked twice.** compose-sequence for the 3:00 cut was blocked on both attempts. Attempt 1 (e1576f1c…): the board held still 46 frames, over the 45-frame limit. Attempt 2 (ae5f57e0…): a noun key collided with attempt 1's. Fixed by spacing the board's verbs out and giving each attempt its own noun keys. |
| draft-run-3 (01:44) | **Stopped by the operator** during make-narration, so that task has no receipt. A test render at CRF 20 measured 58 MB, over the ~40 MB budget, so the 3:00 cut now renders at CRF 25. |
| draft-run-4 (01:49–02:06) | **Finished.** The first published draft: 11 tasks, 11 receipts. |
| production-run (02:15–02:35) | **Finished.** v1, both cuts: 16 tasks, 16 receipts (`evidence-bundle/`). This v2 run supersedes it. |

## What is not claimed

- **The store is not public.** Nobody else can query the local Tessera store or its blobs. This bundle holds what you need to recompute the receipts and follow the chain, but the receipts are not anchored to a public log or to the hosted Tessera service.
- **The voice is AI-generated.** It is Kokoro-82M, voice af_heart, and labelled on screen.
- **The kit run is a local run with synthetic data.**
  - Its agents and the steward are scripted stand-ins.
  - It used a local, unmerged branch of Eranos and of the seed-pack library for the handwritten-statements kit.
  - The sort-and-split step is a labelled illustration.
  - Nothing was sent through the live request box.
- **QA is the video pack's automated checks.**
  - Both caption-free MP4s fail caption coverage by construction, because their captions ship as the WebVTT files.
  - No person has reviewed the cuts frame by frame yet.
- **The learning results are quoted, not re-measured.** The learning slide's numbers are the deck's own results on synthetic tasks.
- **Live captures are a snapshot.** They show the public pages as they were at 08:52–08:54 EDT.
