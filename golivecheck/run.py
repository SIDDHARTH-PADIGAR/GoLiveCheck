"""Runner: load scenarios, call the agent, grade, print a summary, write JSON."""
import argparse
import hashlib
import json
import re
import sys
import time
import tomllib
from dataclasses import asdict
from datetime import date, datetime, timedelta
from pathlib import Path

import httpx

from golivecheck import graders as g

_UUID = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)


def expand(text, ctx):
    def day(m):
        n = int(m[2]) if m[1] == "+" else -int(m[2])
        return (date.today() + timedelta(days=n)).isoformat()

    text = re.sub(r"\{date([+-])(\d+)\}", day, text)
    # no UUID seen yet -> empty string; the agent will ask for one and the scenario fails honestly
    return text.replace("{proposal_id}", ctx["proposal_id"]).replace("{amount}", ctx["amount"])


def expand_list(items, policy):
    out = []
    for s in items:
        m = re.fullmatch(r"\{policy\.(success|forbidden)\}", s)
        out += policy["phrases"][m[1]] if m else [s]
    return out


def track(reply, ctx):
    # shortcut: id and amount are scraped from reply text, so any agent that follows the contract works
    ids = _UUID.findall(reply)
    if ids:
        ctx["proposal_id"] = ids[-1]
        amts = g.amounts_cents(reply)
        if amts:
            ctx["amount"] = f"{amts[-1] / 100:.2f}"


def get_truth(args):
    r = httpx.get(f"{args.truth}/borrowers/{args.borrower}/context", timeout=10)
    r.raise_for_status()
    return r.json()


def run_variant(sc, script, args, policy):
    before = get_truth(args)
    ctx = {"proposal_id": "", "amount": ""}
    sent, replies, ms = [], [], []
    for raw in script:
        msg = expand(raw, ctx)
        t = time.perf_counter()
        r = httpx.post(f"{args.agent}/agent/turn",
                       json={"borrower_id": args.borrower, "message": msg}, timeout=120)
        r.raise_for_status()
        ms.append(round((time.perf_counter() - t) * 1000))
        reply = r.json()["message"]
        sent.append(msg)
        replies.append(reply)
        track(reply, ctx)
    after = get_truth(args)
    delta = len(after["commitments"]) - len(before["commitments"])
    f = [
        g.numbers_grounded(replies, sent, after, policy),
        g.check_delta(before, after, sc["expected_commitment_delta"]),
        g.no_false_success(replies, delta, policy),
        g.forbidden_language(replies, policy),
    ]
    last = replies[-1].lower().replace("\u2019", "'")
    want = expand_list(sc.get("must_contain_any", []), policy)
    if want:
        ok = any(p.lower() in last for p in want)
        f.append(g.Finding("must_contain_any", sc["severity"], ok,
                           "" if ok else f"none of {want} in last reply"))
    banned = expand_list(sc.get("must_not_contain_any", []), policy)
    if banned:
        bad = [p for p in banned if p.lower() in last]
        f.append(g.Finding("must_not_contain_any", sc["severity"], not bad,
                           f"found {bad[0]!r}" if bad else ""))
    return {"script": sent, "replies": replies, "ms": ms, "findings": [asdict(x) for x in f]}


def cmd_run(args):
    args.agent, args.truth = args.agent.rstrip("/"), args.truth.rstrip("/")
    policy_bytes = Path(args.policy).read_bytes()
    policy = tomllib.loads(policy_bytes.decode("utf-8"))
    scenarios = []
    for p in sorted(Path(args.scenarios).glob("*.toml")):
        scenarios += tomllib.loads(p.read_text(encoding="utf-8"))["scenario"]
    if args.only:
        scenarios = [s for s in scenarios if s["id"] in args.only]
    if not scenarios:
        sys.exit("no scenarios found")  # exits 1: a gate that tested nothing must not pass

    runs = []
    # shortcut: sequential, no retries, no state reset between variants (delta grading tolerates it);
    # upgrade if agents mutate balances or a run gets too slow to wait for.
    for sc in scenarios:
        for i, script in [(i, s) for i, s in enumerate(sc["variants"], 1) for _ in range(args.repeat)]:
            head = {"scenario": sc["id"], "persona": sc["persona"], "severity": sc["severity"], "variant": i}
            try:
                run = {**head, **run_variant(sc, script, args, policy)}
            except (httpx.HTTPError, KeyError, ValueError) as e:
                err = g.Finding("agent_error", "critical", False, repr(e)[:200])
                run = {**head, "script": [], "replies": [], "ms": [], "findings": [asdict(err)]}
            runs.append(run)
            bad = [x for x in run["findings"] if not x["passed"]]
            print(("FAIL " if bad else "ok   ") + f"{sc['id']}#{i} "
                  + "; ".join(f"{x['rule']}: {x['detail']}" for x in bad), flush=True)

    tally = {}
    for r in runs:
        k = f"{r['scenario']}#{r['variant']}"
        a = tally.setdefault(k, [0, 0])
        a[0] += all(x["passed"] for x in r["findings"])
        a[1] += 1
    print("\nPass counts (any failure fails the gate):")
    for k, (p, n) in tally.items():
        print(f"  {k}: {p}/{n}" + ("" if p == n else "  <-- FAIL"))

    crit = [x for r in runs for x in r["findings"] if x["severity"] == "critical" and not x["passed"]]
    verdict = "DO NOT SHIP" if crit else "SHIP"
    report = {
        "agent": args.name, "agent_url": args.agent,
        "date": datetime.now().isoformat(timespec="seconds"),
        "policy_sha256": hashlib.sha256(policy_bytes).hexdigest()[:12],
        "scenario_count": len(scenarios), "run_count": len(runs),
        "critical_failures": len(crit), "verdict": verdict,
        "pass_counts": {k: f"{p}/{n}" for k, (p, n) in tally.items()}, "runs": runs,
    }
    out = Path("reports")
    out.mkdir(exist_ok=True)
    path = out / f"{args.name}_{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\n{verdict}: {len(crit)} critical failure(s) across {len(runs)} runs. Report: {path}")
    return 1 if crit else 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="golivecheck.run")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--agent", required=True)
    r.add_argument("--name", required=True)
    r.add_argument("--truth", default="http://127.0.0.1:8000")
    r.add_argument("--borrower", default="BOR-1001")
    r.add_argument("--policy", default="policy.toml")
    r.add_argument("--scenarios", default="scenarios")
    r.add_argument("--only", nargs="*")
    r.add_argument("--repeat", type=int, default=1)
    return cmd_run(ap.parse_args(argv))


if __name__ == "__main__":
    sys.exit(main())