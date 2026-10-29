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

## D-007 · 2026-10-28
- **Decision:** `{proposal_id}` and `{amount}` are scraped from the agent's reply text with a regex, not read from EchoResolve-specific JSON fields.
- **Context:** The contract only guarantees a string field `message`. EchoResolve happens to also return a `proposal` object, but another agent may not.
- **Options considered:** Read `reply["proposal"]["proposal_id"]`; add a per-agent adapter.
- **Pros:** Any agent that follows the contract can be tested with no adapter.
- **Cons and risks accepted:** An agent that never prints the proposal ID in its text fails the confirm scenarios. That is arguably correct, since the borrower could not confirm either.
- **Business value:** A delivery team can point the gate at a new agent without writing glue code.
- **Revisit when:** A target agent returns IDs only in structured fields.

## D-008 · 2026-10-28
- **Decision:** Truth is read before and after each variant and graded by delta. The runner does not reset agent state. For a clean run, start EchoResolve on a fresh DB file via ECHORESOLVE_DB_PATH.
- **Context:** EchoResolve has no reset route, but store.py honours the env var. The runner only talks HTTP.
- **Options considered:** Reset the DB from the runner; add a reset route to EchoResolve; restart the server per variant.
- **Pros:** No change to the agent under test, and the delta rule works whatever state exists.
- **Cons and risks accepted:** Old commitments widen the grounded-number set slightly (an old $50 commitment makes $50 "grounded"). Runs are only as clean as the DB you start with.
- **Business value:** Results are repeatable by following one documented startup step, with no changes to the lender's system.
- **Revisit when:** Cross-contamination shows up in a report, or a target agent changes balances.

## D-009 · 2026-10-28
- **Decision:** Added "confirmed and recorded" to the success phrases in policy.toml. Did not add "has been confirmed".
- **Context:** EchoResolve's real confirm reply is "has been confirmed and recorded", which none of the five spec phrases match. Its propose reply says "No payment has been confirmed", which "has been confirmed" would wrongly flag.
- **Options considered:** Keep the spec list unchanged; add the broader phrase.
- **Pros:** The false-success rule recognises this customer's real wording without false alarms.
- **Cons and risks accepted:** Phrase lists are per customer and need upkeep. A reply worded differently still slips past.
- **Business value:** This is the customer-specific layer at work: the same scenarios, tuned by config to the customer's agent wording.
- **Revisit when:** Wording changes, or the naive agent in Phase 4 shows phrases we miss.

## D-010 · 2026-10-28
- **Decision:** over_limit has an $800 variant beside the two $5000 variants.
- **Context:** The balance is $1,250. $5000 is rejected by the balance check, so those variants never test the $500 policy cap.
- **Options considered:** Only $5000, as the spec says.
- **Pros:** The $800 variant exercises the cap itself.
- **Cons and risks accepted:** Slightly beyond the spec text. If the balance changes, the variant may need a new value.
- **Business value:** It checks the lender's real limit rather than an incidental one.
- **Revisit when:** Seed balances change.

## D-011 · 2026-10-28
- **Decision:** HTTP errors, timeouts and a missing `message` field become a critical `agent_error` finding. An empty scenario set exits 1.
- **Context:** A gate must fail closed.
- **Options considered:** Let exceptions crash the run.
- **Pros:** An unreachable or contract-breaking agent can never print SHIP.
- **Cons and risks accepted:** A flaky network gives DO NOT SHIP with an error as the reason.
- **Business value:** "Did not run" can never be mistaken for "passed".
- **Revisit when:** Retries are needed for slow models.
