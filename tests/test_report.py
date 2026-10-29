from golivecheck.report import pct, to_markdown


def test_pct():
    v = list(range(1, 11))
    assert (pct(v, 50), pct(v, 95), pct([], 50)) == (5, 10, 0)


def test_markdown():
    f = lambda ok: [{"rule": "commitment_delta", "severity": "critical", "passed": ok, "detail": "expected 1, got 0"}]
    run = lambda ok: {"scenario": "s", "persona": "p", "variant": 1, "script": ["a"], "replies": ["clarify?"], "ms": [100], "findings": f(ok)}
    rep = {"agent": "x", "agent_url": "u", "verdict": "DO NOT SHIP", "critical_failures": 1,
           "policy_sha256": "h", "scenario_count": 1, "run_count": 2, "date": "d", "runs": [run(True), run(False)]}
    md = to_markdown(rep)
    assert "DO NOT SHIP" in md and "1/2" in md and "expected 1, got 0 :: clarify?" in md