# Fizgig Browser GUI — Engineering Plan

Status: planning and baseline audit

Working branch: `browser-gui`

Baseline inspected locally: `b514388` (`master`, upstream `origin/master`)

Fork remote configured: `fork -> https://github.com/vishnuteja7054/Fizgig.git`

Note: the fork fetch was attempted but GitHub DNS was unavailable in the
execution environment. The branch therefore remains based on the verified
upstream commit above until the fork is fetched successfully.

## 1. Objective

Provide a browser-native Fizgig application with a professional UI while
preserving the existing model, training, dataset, LoRA surgery, preview,
profiling, extraction, and persistence behavior.

The browser application must replace the Tk desktop shell. It must not be a
noVNC wrapper around Tkinter.

## 2. Constraints and invariants

These are non-negotiable unless explicitly changed by the user:

1. Existing model and training behavior remains the source of truth.
2. Existing `.safetensors` compatibility and metadata behavior must remain
   intact.
3. Existing dataset formats, caption sidecars, presets, preferences, output
   folders, and resume/state files must remain usable.
4. Long-running work must survive browser refreshes and reconnects.
5. A browser disconnect must not silently cancel training or destructive work.
6. GPU-heavy operations must run on the worker/device selected by the server,
   not in the browser.
7. The old Tk GUI remains runnable during migration until parity is proven.
8. Every migrated feature needs an API/service test and a browser-level smoke
   test before the corresponding Tk path is retired.

## 3. Baseline audit findings

### Repository shape

- `lora_trainer_gui.py` is 30,499 lines.
- `LoRATrainerGUI` contains approximately 730 methods.
- The repository has 119 Python source files under `src/fizgig`.
- The repository has 37 Python test files.
- Core domains already have useful boundaries: training, Krea 2, MiniMax H3,
  Klein, Repair Studio, Profiler, LoRA Royale, Extract, dataset, and scripts.

### Existing desktop surface

The Tk notebook currently exposes:

1. Start
2. Image Prep
3. Captions
4. Samples
5. Training
6. Profiler
7. Repair Studio
8. LoRA the Explorer
9. LoRA Royale
10. Extract
11. Metadata
12. Preferences

The GUI also owns file dialogs, message boxes, image rendering, subprocess
launching, worker threads, status polling, browser launching, state restoration,
training queues, gallery serving, and UI-specific validation.

### Existing reusable backend

The core package already contains substantial non-UI functionality, including:

- `src/fizgig/training/`
- `src/fizgig/krea2/`
- `src/fizgig/klein/`
- `src/fizgig/minimax/`
- `src/fizgig/repair_studio/`
- `src/fizgig/profiler/`
- `src/fizgig/lora_royale/`
- `src/fizgig/extraction/`
- `src/fizgig/dataset/`
- `src/fizgig/scripts/`

This supports an extraction-and-adapter strategy rather than rewriting model
code. However, some orchestration and validation still lives inside the Tk
class and must be moved behind services before it can be safely exposed over
HTTP.

### Current web behavior

The only existing HTTP server in the GUI is the local samples gallery, built
with `HTTPServer` and `SimpleHTTPRequestHandler`. It is not an application API
and cannot be reused as the browser frontend.

## 4. Target architecture

```text
Browser
  │ HTTPS / WebSocket
  ▼
Web frontend (React + TypeScript)
  │ typed REST + WebSocket client
  ▼
API layer (FastAPI)
  │ auth, validation, jobs, events, files
  ▼
Application services
  │ training, captions, prep, repair, explorer, royale, profiler, extract
  ▼
Existing Fizgig domain/model modules
  │
  ├── persistent workspace volume
  ├── model/cache volume
  └── GPU worker process/container
```

The API layer must not import Tkinter. The frontend must not know filesystem
paths that are meaningful only inside a container. The service layer owns the
translation between browser-safe workspace IDs and local paths.

## 5. Recommended technology choices

### Backend

- FastAPI for HTTP endpoints.
- Pydantic models for request/response contracts.
- WebSockets or Server-Sent Events for logs and job progress.
- SQLite initially for job metadata, with a repository abstraction so it can be
  moved to Postgres if multi-user operation is later required.
- A durable job table and filesystem-backed artifacts on a Modal Volume.
- One job runner per GPU worker; no in-process global model sharing across
  unrelated browser sessions until resource ownership is explicit.

### Frontend

- React + TypeScript.
- A component library with accessible tabs, forms, dialogs, tables, sliders,
  and notifications.
- TanStack Query or equivalent for server state and cache invalidation.
- A typed API client generated from the FastAPI OpenAPI schema.
- Browser-native upload/download, image/video/audio preview, progress views,
  and reconnect handling.

### Deployment

- One Modal web service for the browser API/frontend.
- Separate Modal worker function or class for model-heavy jobs.
- Modal Volumes for models, datasets, caches, profiles, outputs, and job logs.
- Explicit CPU/GPU profiles; the browser service must not claim a GPU when it
  is only serving UI and metadata.

## 6. Migration strategy

### Phase 0 — Baseline and safety

Deliverables:

- Confirm the fork branch is synchronized with the intended upstream commit.
- Record Python, PyTorch, CUDA/ROCm, and dependency versions used by the
  baseline.
- Run the existing static checks and the relevant test suite.
- Add a browser migration test marker and CI command without changing runtime
  behavior.
- Freeze a small fixture workspace containing sample configs, captions,
  metadata, and representative LoRA file stubs where licensing permits.

Exit criteria:

- Existing launcher and domain tests pass.
- A clean baseline report is committed.
- No browser code has changed production behavior.

### Phase 1 — Extract pure application contracts

Create `src/fizgig/app/` with services that do not import Tkinter:

- `workspace_service.py`
- `preferences_service.py`
- `dataset_service.py`
- `caption_service.py`
- `image_prep_service.py`
- `training_service.py`
- `job_service.py`
- `repair_service.py`
- `explorer_service.py`
- `royale_service.py`
- `profiler_service.py`
- `extract_service.py`

Each service should accept typed values and return typed results. It should not
receive Tk variables, widgets, callbacks, or message-box functions.

The first extraction targets are the least model-sensitive operations:

1. Preferences and workspace paths
2. Dataset scanning and caption file operations
3. Preset load/save and validation
4. Training command/config construction
5. Job status and log collection

Exit criteria:

- Service tests cover behavior currently tested only through GUI objects.
- Tk uses the new services for the migrated paths.
- No service imports `tkinter`, `ImageTk`, `filedialog`, or `messagebox`.

### Phase 2 — Browser foundation

Deliverables:

- `server/` FastAPI application.
- `/api/health` and `/api/version`.
- Workspace/session model.
- Error envelope and request ID convention.
- Structured logging.
- WebSocket/SSE event protocol.
- React shell with navigation, route guards, loading/error states, and theme.
- Modal deployment definition with a CPU-only UI profile.

Exit criteria:

- Browser opens a healthy app URL without noVNC.
- A user can create/select a workspace and see its persisted state.
- Refreshing the browser preserves the selected workspace.

### Phase 3 — Dataset and Start workflow

Implement the first useful end-to-end path:

1. Upload or select a dataset folder.
2. Scan supported files.
3. Show thumbnails and caption presence.
4. Edit/save captions.
5. Validate trigger word and dataset settings.
6. Save the same config format used by the desktop app.

Exit criteria:

- A dataset created in the browser opens correctly in the Tk app.
- A dataset created in the Tk app opens correctly in the browser.
- No path traversal is possible through upload or file endpoints.

### Phase 4 — Job system and Training tab

Implement jobs as durable records rather than browser-bound subprocesses:

- `queued`, `starting`, `running`, `paused`, `completed`, `failed`,
  `cancel_requested`, and `cancelled` states.
- Idempotent start/cancel/pause/resume commands.
- Append-only event/log stream with sequence numbers.
- Reconnect from the last received event sequence.
- Checkpoint/output discovery.
- Training queue persistence.

The existing command builders and state files must be wrapped first. Do not
rewrite training algorithms in this phase.

Exit criteria:

- Closing the browser does not stop a running job.
- Reopening the browser shows accurate status and logs.
- Pause/resume/cancel behavior matches the desktop app.
- Output checkpoints are discoverable and downloadable.

### Phase 5 — Samples, Profiler, Extract, Metadata

Migrate artifact-oriented tools next because they have clear input/output
boundaries:

- Samples and gallery previews.
- Profiler reports and sidecars.
- Extract lower-rank LoRAs.
- Metadata inspection/edit/save.

Replace local `webbrowser.open()` behavior with browser routes and artifact
links. Replace local gallery HTTP servers with an API-backed artifact viewer.

### Phase 6 — Repair Studio, Explorer, and Royale

These are the highest-risk features because they hold long-lived model engines,
large previews, caches, sliders, video/audio playback, and concurrent workers.

Implement a session-owned engine manager:

- Explicit session ID and worker ownership.
- Lazy model loading.
- Server-side cache keys.
- Preview job cancellation and supersession.
- Progress events and preview artifact URLs.
- Bounded concurrency per GPU.
- Cleanup on idle timeout and explicit unload.

Repair Studio should be migrated before Explorer/Royale because its slider and
preview contract is the clearest foundation for the other workbench tools.

Exit criteria:

- Slider changes cannot race and display stale previews as current.
- A disconnected browser can reconnect to the active session.
- GPU memory is released on unload and idle timeout.
- Saved repaired/explored files are byte-valid and load in the existing app.

### Phase 7 — Image Prep, Gizmo, and advanced media

Move image/video/audio prep into browser-native upload, preview, and job flows.
Gizmo is currently another Tk application, so it should become a separate web
route or service rather than being embedded into the main page.

### Phase 8 — Parity hardening and controlled retirement

- Build a feature parity matrix against every Tk tab and major action.
- Run golden-workspace comparisons between Tk and browser outputs.
- Add browser end-to-end tests for critical flows.
- Add load/resource tests for concurrent sessions.
- Document unsupported platform/model combinations.
- Keep Tk as a supported fallback until parity is demonstrated.

## 7. Feature parity matrix

The following matrix is the release gate. A feature is not considered migrated
when its tab merely renders; the underlying action, state, errors, and outputs
must work.

| Area | UI | API/service | Persistence | GPU/job | Browser acceptance |
|---|---:|---:|---:|---:|---:|
| Start/workspace | pending | pending | pending | no | pending |
| Image Prep | pending | pending | pending | optional | pending |
| Captions | pending | pending | pending | optional | pending |
| Samples | pending | pending | pending | yes | pending |
| Training | pending | pending | pending | yes | pending |
| Profiler | pending | pending | pending | yes | pending |
| Repair Studio | pending | pending | pending | yes | pending |
| Explorer | pending | pending | pending | yes | pending |
| LoRA Royale | pending | pending | pending | yes | pending |
| Extract | pending | pending | pending | optional/yes | pending |
| Metadata | pending | pending | pending | no | pending |
| Preferences | pending | pending | pending | no | pending |
| Gizmo | pending | pending | pending | optional | pending |

## 8. Security and reliability requirements

- Never expose arbitrary host paths directly to the browser.
- Resolve all files beneath an allowed workspace root.
- Validate uploads by size, extension, content type, and destination.
- Use authenticated Modal endpoints for anything beyond private testing.
- Keep model files and output volumes separate from temporary job space.
- Do not put Hugging Face tokens, Modal tokens, or VNC passwords in source.
- Add cleanup for orphaned subprocesses and abandoned GPU sessions.
- Treat all filenames, captions, prompts, and metadata as user data, not shell
  fragments.
- Do not allow browser input to become an unvalidated subprocess argument.

## 9. Testing strategy

### Existing tests

Keep the current 37-file suite green. It covers important training, launcher,
state, LoKR, H3, caption, and UI behavior and must not be replaced by browser
tests.

### New tests

- Unit tests for service contracts and path/security rules.
- Contract tests for OpenAPI request/response schemas.
- Job state-machine tests, including reconnect and duplicate commands.
- Golden tests for command/config generation.
- Browser tests for Start, Captions, Training, Repair, and output download.
- Resource tests for GPU session cleanup and bounded concurrency.
- Compatibility tests that open browser-created artifacts in the Tk code path.

## 10. Definition of done for the first release

The first browser release is complete only when:

- The browser UI is served directly over HTTP/HTTPS; noVNC is not involved.
- Start, dataset/caption workflow, Training, Samples, Preferences, and output
  browsing work end to end.
- A training job continues after browser refresh/disconnect.
- Browser-created configs and outputs remain compatible with the existing app.
- Critical Repair Studio workflows are either fully migrated or explicitly
  marked unavailable; no fake controls are shipped.
- Existing tests and new service/browser tests pass.
- Modal deployment can be reproduced from a clean checkout.
- The feature parity matrix and known-limitations document are included.

## 11. Immediate next engineering tasks

1. Successfully fetch and verify the fork remote, then push `browser-gui` as
   the working branch.
2. Add a baseline report with test commands and environment information.
3. Map the GUI's state variables and command builders to service boundaries.
4. Extract workspace/preferences/preset logic without changing behavior.
5. Add the FastAPI health/version skeleton and a minimal React shell.
6. Implement the Start/dataset browser flow as the first vertical slice.
7. Demonstrate browser-created dataset/config compatibility with the Tk app.

No model or training code should be rewritten before the first vertical slice
proves that the service boundaries and persistence model are sound.
