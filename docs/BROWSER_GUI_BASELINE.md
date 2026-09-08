# Browser GUI Migration — Baseline Report

Date: 2026-09-09

Branch: `browser-gui`

Commit: `4578635` (`docs: plan browser gui migration`)

## Repository state

- Working tree: clean at the time of the baseline check.
- `fork/browser-gui` points to the planning commit.
- `origin/master` and `fork/master` point to `b514388`.
- No production source files have been modified yet.

## Static validation

Command:

```bash
python3 -m compileall -q lora_trainer_gui.py src tests
```

Result: PASS.

## Test runner availability

Command:

```bash
python3 -m pytest --collect-only -q
```

Result: NOT RUN — `pytest` is not installed in the current environment.

This is an environment limitation, not a test failure. The repository contains
37 Python test files. Before relying on runtime test results, create or select a
project environment matching the repository's supported dependencies and record
the Python/PyTorch/platform versions.

## Architecture observations confirmed from source

- `lora_trainer_gui.py` is a 30,499-line Tkinter application.
- `LoRATrainerGUI` contains approximately 730 methods.
- The domain implementation is already split across 119 Python files under
  `src/fizgig`.
- The GUI owns substantial orchestration: Tk variables and callbacks, file
  dialogs, message boxes, image widgets, subprocesses, worker threads, local
  gallery serving, training queue state, and model-session lifecycle.
- The existing local HTTP server is only the samples gallery; it is not an API
  boundary and is not sufficient for browser delivery.

## Baseline decision

Do not begin by rewriting model modules or copying Tk callbacks into HTTP
handlers. First extract pure services for workspace/preferences/presets,
dataset operations, configuration building, and durable jobs. Keep the Tk GUI
using those services during the migration so the old and new interfaces can be
validated against the same behavior.
