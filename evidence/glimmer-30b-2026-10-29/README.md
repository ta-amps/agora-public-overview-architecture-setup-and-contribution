# Muse Glimmer 30B tuned as a tool-call specialist (October 29, 2026)

This is the evidence for one measured result: a QLoRA adapter that makes Muse Glimmer 30B produce Tessera tool calls
more reliably.
- **How it was made:** trained on free cloud GPUs (Kaggle), with synthetic examples only.
- **What it is:** one synthetic task. It shows the tuning loop works; it is not a general benchmark.
- **What it is not:** nothing was promoted, admitted or registered, and the adapter weights are not published here.

## The result

On a fresh test set of 150 rows, built after training and registered by hash before scoring:

| | Base | With the adapter |
| --- | --- | --- |
| Exact match | 93.3% | 99.3% |
| Valid JSON | 96.7% | 100.0% |
| Correct refusals | 97.3% | 99.3% |

- **The paired difference:** +6.0%, with a paired bootstrap 95% interval of +2.0% to
  +10.7%. 10 rows improved and 1 regressed.
- **The frozen test set** used during development: 87.3% to
  98.7%.
- **The promotion rule:** `tool-call-specialist.promotion` v1 (sha256 `bf0fa821717c2400…`) was fixed before
  scoring. It returned `promote_candidate`, with 12 of 12 checks passing.

## What makes the comparison fair

- **Pre-registration.** The fresh test set's hashes were recorded before any model saw it. See
  `fresh-holdout-v1-receipt.json`.
- **No leakage.** There are 0 exact, request-level or held-out-family matches against the 511 training rows.
  - Against the older test set, 54 rows share only a request *shape*; no row shares a request or an exact match.
- **Integrity checks.** In `fresh-2b-decision.json`, under `integrity`, every check is `true`:
  - no contamination;
  - the frozen base model is unchanged;
  - a fresh reload of the adapter reproduced its outputs (8 of
    8 regenerated rows matched exactly);
  - the test-set digests match.

## Files

| File | Bytes | sha256 |
| --- | --- | --- |
| `fresh-2b-decision.json` | 5,439 | `553354e339b912e5230be7582203fb502a4e94621fe4f97ca93fa7e0826db683` |
| `fresh-holdout-v1-receipt.json` | 2,474 | `0ce30e9ff593a4e7238012236e38368c219fc235284d03e1fb898d728c196d56` |
| `phase2a-tuning63-compare.json` | 2,578 | `30fc1830c260e90b0cace77e30ecc5de42c9d3ec08046798a62336f615e48a4b` |
| `phase2a-tuning63-summary.json` | 5,568 | `5a1c39872aed6a7ad1bf8d0f3dead7d7af2720b45e98d73f79b6c79a2bfec985` |
| `phase2b-tuning511-compare.json` | 2,536 | `9e14d7ce8f0ac7ace83e25fef51b159cdbd81167ac67c8ef6562b436f5dfda39` |
| `phase2b-tuning511-summary.json` | 5,535 | `88fba975d9d1de2dd1d527e64190eee8a41d41bccc925c3e255e41ed04645d34` |
| `smoke-v1-summary.json` | 2,390 | `1813af5b868c31265c36f4d2176faa57b44ce94ab81d24b4f9dd4d3d5516335f` |
| `smoke-v2-summary.json` | 3,702 | `2ac2edb16546f391d75513391eb0ef3e460867ce8833dd6ddc06a2de13f0bf0e` |
| `index.json` | 29,522 | `df45235c11fdef668af87611e273e501e4e01711bade3fb0417fed1e1c84f398` |
| `index-pre-phase2.json` | 8,287 | `84d3be35c1dc311e4b844f4ef5f9ffef5f3c89491ddd291839320e1a3bfcfcfa` |

`index.json` lists the sha256 of every training, test and code file the run used, and those files stay private.
The two `phase2*` pairs are the earlier 63-row and 511-row training runs, and the smoke summaries are the setup checks.
Some files record container image digests from the machine that produced them. In `fresh-holdout-v1-receipt.json`, one local folder path
(`alt_snapshot_check.snapshot`) is replaced for publication; the original file's sha256 is `24bda01014a36d1969da386384164aecb90038f15aed85e9f00ffba39876c923`.
