# Fizgig Browser Parity Audit

This document is the working contract for making the browser workbench a real
Fizgig product. A tab is not considered complete because it renders or because
it can build a preview command. It is complete only when its original controls,
validation, backend operation, progress/error states, persisted settings, and
artifacts are covered by browser/API tests.

## Baseline

The browser currently has a working FastAPI control plane, workspace-safe paths,
durable job records, artifact downloads, dataset import/scan/caption basics,
resize-only image preparation, a minimal training launch, sample prompt/override
files, profiler/extract previews and jobs, repair state/bake/render, Explorer and
Royale catalog jobs, metadata inspection, and basic preferences.

That baseline is useful infrastructure, but it is not yet behavioral parity with
`lora_trainer_gui.py`.

## Parity matrix

| Surface | Current browser state | Missing parity work | Priority |
| --- | --- | --- | --- |
| 1. Start | Folder field, local folder/file import, scan, setup warning, navigation | Original browse semantics, model-family-aware setup status, full post-training links, import progress/details | P0 |
| 2. Image Prep | Resize-only request and durable job | PNG conversion modes, face-crop modes, output/replace policy, validation summary, problem-image handling, original result counts and errors | P0 |
| 3. Captions | List, read/write caption, basic remove, image preview | Trigger word, Florence/Qwen model selection, task/instruction editor, AI caption-all, static caption-all, stop/unload, find/replace preview/apply, pagination, video/audio handling, caption progress | P0 |
| 4. Samples | Prompt file and live override | Resolution, steps, seed, reference image, frame count, turbo strength/pace, architecture-specific options, sample frequency, first-sample toggle, gallery/folder results | P0 |
| 5. Training | Dataset config, limited command preview, start job | Full original training schema: architecture, presets, optimizer, scheduler, LR/adaptive LR, network type/LoKr, blocks, context LoRA, Krea 2, MiniMax H3, quantization/FP8, checkpoint/state policy, timestep weighting, cache, resume, sample controls, pause/resume/stop, full argv/config round-trip | P0 |
| Profiler | Generic preview/start form | Original profiler inputs/options, report lifecycle, report/artifact viewer, exact command and output contract | P1 |
| Repair Studio | Default state, JSON/block sliders, bake/render jobs | Original block/timestep controls, preview gallery, donor blending semantics, family-specific validation, output/artifact viewer, cancellation and logs | P1 |
| LoRA the Explorer | Catalog scan and generic render job | Original mutation/evolution workflow, candidate selection, favorites, generation history, Repair Studio handoff, artifact gallery | P1 |
| Extract | Generic source/output/samples/rank form | Original block/timestep-targeted extraction options, LyCORIS/LoHa support, output metadata, progress/results | P1 |
| Metadata | SafeTensors header inspection | Original metadata editing fields, thumbnail/file selection, save/write contract, validation and reload | P1 |
| Preferences | DiT/VAE/text encoder/output path | Complete model-family paths, download/help links, runtime/GPU options, captioning settings, defaults, persistence and migration | P0 |
| Hidden original tools | Jobs, Royale exist in browser menu | Preserve exact LoRA Royale and Metadata behavior; expose Jobs as a diagnostic surface, not a replacement for missing tab behavior | P1 |

## Backend contract requirements

Every browser operation must follow the same contract:

1. Validate all user paths against the configured workspace before starting.
2. Return a typed response with the normalized values actually used.
3. Use a durable job for work that can outlive an HTTP request.
4. Persist stdout/stderr, progress, cancellation state, exit code, and result paths.
5. Return workspace-relative artifact paths only; the browser obtains them through
   the authenticated artifact endpoint.
6. Reuse the original Fizgig command builders and worker implementations rather
   than silently approximating their options.
7. Add an API contract test for success, invalid input, missing model/file,
   cancellation, and failed worker execution.

## GPU/Modal requirements

The browser API must not claim that a job is GPU-ready merely because it built an
argv preview. Before a real training/render job starts, the service must report:

- selected device and backend (CUDA, ROCm, CPU fallback where supported),
- visible GPU name, VRAM, and torch/device availability,
- model files mounted and readable in the worker,
- the exact resolved config/argv,
- worker image/runtime version,
- durable job progress and terminal result.

Modal deployment is a separate acceptance gate. Local loopback tests and a Vite
build do not verify Modal volume mounts, secrets, GPU selection, or worker
execution. Those must be tested with a small no-training health/config job before
any expensive training run.

## Implementation order

1. Expand the shared typed API and job contract, including runtime/GPU status.
2. Complete Preferences and model-family configuration because every GPU tab
   depends on it.
3. Complete Start, Image Prep, and Captions as the dataset preparation path.
4. Complete Samples and Training using the original settings schema and command
   builders.
5. Complete Profiler, Repair Studio, Explorer, Extract, Metadata, and Royale.
6. Add browser interaction tests for every primary control and API contract tests
   for every route and failure mode.
7. Run a Modal smoke deployment and a small GPU validation job, then compare the
   generated configs, logs, and artifacts with the desktop implementation.

## Definition of done

The browser phase is complete only when a user can start from an uploaded dataset,
prepare it, caption it, configure samples, validate and launch a real GPU
training job, monitor/cancel/resume it, inspect outputs, and use every workbench
tab without falling back to the desktop GUI or an undocumented API.
