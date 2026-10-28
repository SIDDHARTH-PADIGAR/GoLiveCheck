# Decisions
## D-001 · 2026-10-28
- **Decision:** Runtime dependencies are only httpx and pytest. TOML via tomllib, CLI via argparse, no `__init__.py` files (namespace package).
- **Context:** Spec demands the least code and free, open-source tools on Windows.
- **Options considered:** requests, typer, pydantic, pyyaml.
- **Pros:** Two installs, nothing to break, fast setup for anyone cloning.
- **Cons and risks accepted:** Without `__init__.py`, some tools may not treat the folder as a package. We add it if one does.
- **Business value:** A delivery team can run the gate from a fresh clone in minutes, with no dependency review.
- **Revisit when:** We need a feature stdlib can't cover cleanly.

## D-002 · 2026-10-28
- **Decision:** The voice spike runs in a separate `.venv-spike`, with its packages kept out of requirements.txt.
- **Context:** Piper and faster-whisper are heavy and only needed for Phase 7.
- **Options considered:** Install into the main venv; skip the spike until Phase 7.
- **Pros:** The core harness stays light, and we learn early whether voice is feasible on this machine.
- **Cons and risks accepted:** The spike measures only one phrase on one CPU, which is a feasibility check and not a benchmark.
- **Business value:** It tells us before Phase 1 whether a measured number-accuracy claim for voice is realistic.
- **Revisit when:** Phase 7 starts, or if the spike fails (then the voice path is skipped and the README says so).

## D-003 · 2026-10-28
- **Decision:** Phase 7 stays in scope. The spike passed, and the model is faster-whisper `tiny.en` with int8 on CPU.
- **Context:** Piper and faster-whisper installed with plain pip on Windows 11, and the round-trip of one amount came back correct.
- **Options considered:** Skip Phase 7; use a larger Whisper model.
- **Pros:** A real measured number error rate for the voice path, from tools that are free.
- **Cons and risks accepted:** One phrase proves feasibility, not accuracy. Whisper writes spoken numbers as digits, so the Phase 7 comparison must normalise both sides. `tiny.en` is the weakest model and will overstate errors compared with larger ones.
- **Business value:** A lender can see a measured figure for how often amounts are misheard, instead of an assumption.
- **Revisit when:** Phase 7 starts, or if the timed re-run shows ASR is too slow to batch.
