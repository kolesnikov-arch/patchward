"""fa-patchward CLI.

    fa-patchward select   freeze the task set you will measure yourself on
    fa-patchward run      run your agent (ungated) over it -> predictions.jsonl
    fa-patchward report   score predictions against ground-truth -> your number
    fa-patchward verify   recompute the number from raw reports (honesty check)

Between `run` and `report` you evaluate predictions.jsonl with the public
SWE-bench harness — this tool does not re-implement it. See README.md.
"""
import argparse
import shlex

from . import report as report_mod
from . import run as run_mod
from . import scaffold as scaffold_mod
from . import select as select_mod


def _read_ids(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]


def main(argv=None):
    p = argparse.ArgumentParser(prog="fa-patchward", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    ini = sub.add_parser("init", help="scaffold an adapter + pre-registration here")
    ini.add_argument("--dir", default=".")

    sel = sub.add_parser("select", help="freeze a task set")
    sel.add_argument("--dataset", default="SWE-bench/SWE-bench_Lite")
    sel.add_argument("--split", default=None)
    sel.add_argument("--n", type=int, default=50)
    sel.add_argument("--seed", type=int, default=50)
    sel.add_argument("--exclude", default=None,
                     help="file of instance ids to exclude (e.g. tuning tasks)")
    sel.add_argument("--from-ids", default=None,
                     help="use this id file verbatim instead of sampling")
    sel.add_argument("--out", default="frozen")

    r = sub.add_parser("run", help="run your agent ungated over the task set")
    r.add_argument("--tasks", default="frozen/tasks.txt")
    r.add_argument("--agent", required=True,
                   help="adapter command, e.g. 'python adapters/noop_agent.py'")
    r.add_argument("--out", default="predictions.jsonl")
    r.add_argument("--label", default="my-agent")
    r.add_argument("--dataset", default="SWE-bench/SWE-bench_Lite",
                   help="dataset to enrich task records for the adapter")
    r.add_argument("--timeout", type=int, default=1800)

    rep = sub.add_parser("report", help="score predictions -> your number")
    rep.add_argument("--predictions", default="predictions.jsonl")
    rep.add_argument("--reports", required=True,
                     help="dir of SWE-bench report.json (from the harness)")
    rep.add_argument("--tasks", default=None,
                     help="restrict/report over exactly this id set")
    rep.add_argument("--label", default="my-agent")
    rep.add_argument("--out", default="report")

    v = sub.add_parser("verify", help="recompute the number from raw reports")
    v.add_argument("--report-dir", default="report")
    v.add_argument("--reports", required=True)
    v.add_argument("--predictions", default="predictions.jsonl")
    v.add_argument("--tasks", default=None)

    args = p.parse_args(argv)

    if args.cmd == "init":
        scaffold_mod.init(args.dir)
    elif args.cmd == "select":
        if args.from_ids:
            select_mod.from_ids(args.from_ids, args.out)
        else:
            select_mod.seeded_sample(args.dataset, args.n, args.seed, args.out,
                                     exclude_path=args.exclude, split=args.split)
    elif args.cmd == "run":
        ids = _read_ids(args.tasks)
        run_mod.run(ids, shlex.split(args.agent), args.out, args.label,
                    dataset=args.dataset, timeout=args.timeout)
    elif args.cmd == "report":
        ids = _read_ids(args.tasks) if args.tasks else None
        report_mod.report(args.predictions, args.reports, args.out, args.label, ids)
    elif args.cmd == "verify":
        ids = _read_ids(args.tasks) if args.tasks else None
        report_mod.verify(args.report_dir, args.reports, args.predictions, ids)


if __name__ == "__main__":
    main()
