"""Markdown report from the JSON report dict. Plain string formatting."""
import math


def pct(vals, p):
    v = sorted(vals)
    return v[max(0, math.ceil(p / 100 * len(v)) - 1)] if v else 0


def cell(s):
    return str(s).replace("|", "\\|").replace("\n", " ")


def to_markdown(rep, budget=5000):
    runs = rep["runs"]
    rules = {}
    for r in runs:
        for f in r["findings"]:
            a = rules.setdefault((f["rule"], f["severity"]), [0, 0])
            a[0 if f["passed"] else 1] += 1
    groups = {}
    for r in runs:
        groups.setdefault((r["scenario"], r["variant"], r["persona"]), []).append(r)
    ms = [m for r in runs for m in r["ms"]]
    warm = ms[1:]  # shortcut: first turn of the run is treated as the model cold start
    L = [f"# GoLiveCheck report: {rep['agent']}", "",
         f"**Verdict: {rep['verdict']}** ({rep['critical_failures']} critical failures)", "",
         f"- Agent: {rep['agent']} ({rep['agent_url']})",
         f"- Policy file hash: {rep['policy_sha256']}",
         f"- Scenarios: {rep['scenario_count']} ({rep['run_count']} runs)",
         f"- Date: {rep['date']}", "",
         "## Rules", "", "| Rule | Severity | Pass | Fail |", "|---|---|---|---|"]
    L += [f"| {k[0]} | {k[1]} | {v[0]} | {v[1]} |" for k, v in rules.items()]
    L += ["", "## Scenarios", "",
          "| Scenario | Persona | Passed | Result | Failing rule :: last reply (max 200 chars) |",
          "|---|---|---|---|---|"]
    for (s, v, p), rs in groups.items():
        bad = [r for r in rs if any(not f["passed"] for f in r["findings"])]
        ex = ""
        if bad:
            f = next(f for f in bad[0]["findings"] if not f["passed"])
            last = bad[0]["replies"][-1] if bad[0]["replies"] else ""
            ex = f"{f['rule']}: {f['detail']} :: {last[:200]}"
        L.append(f"| {s}#{v} | {p} | {len(rs) - len(bad)}/{len(rs)} | "
                 f"{'FAIL' if bad else 'pass'} | {cell(ex)} |")
    warn = "WARN" if pct(ms, 95) > budget else "ok"
    L += ["", "## Latency (warn only, never fails the gate)", "",
          f"- All turns ({len(ms)}): p50 {pct(ms, 50)} ms, p95 {pct(ms, 95)} ms, max {max(ms, default=0)} ms [{warn}, budget {budget} ms]",
          f"- Excluding first turn (cold start): p50 {pct(warm, 50)} ms, p95 {pct(warm, 95)} ms",
          "", "---",
          "This report tests only the rules listed above. It does not prove compliance, accuracy or business value."]
    return "\n".join(L) + "\n"