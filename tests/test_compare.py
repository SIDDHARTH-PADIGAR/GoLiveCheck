import json
from types import SimpleNamespace

from golivecheck.run import cmd_compare


def rep(name, passed, pc):
    return {"agent": name, "verdict": "x", "critical_failures": 0, "pass_counts": pc,
            "runs": [{"findings": [{"rule": "commitment_delta", "passed": passed}]}]}


def test_compare_flip(tmp_path, capsys):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(rep("A", True, {"s#1": "3/3", "t#1": "1/3"})))
    b.write_text(json.dumps(rep("B", False, {"s#1": "0/3", "t#1": "1/3"})))
    cmd_compare(SimpleNamespace(a=str(a), b=str(b)))
    out = capsys.readouterr().out
    assert "s#1: A 3/3 -> B 0/3  (B worse)" in out and "unchanged: 1" in out