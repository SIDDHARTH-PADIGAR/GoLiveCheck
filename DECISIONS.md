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
