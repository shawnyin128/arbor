#!/usr/bin/env python3
"""Arbor command line entry.

Two callers share this entry: the plugin hook launcher (``hook <event>``) and the
``arbor`` skill (``doctor``, ``init``, ``context``). Keeping one implementation
behind both means hook behavior and reported behavior cannot drift apart.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))

from arbor_core import doctor as doctor_module  # noqa: E402
from arbor_core import hooks as hooks_module  # noqa: E402
from arbor_core import init as init_module  # noqa: E402
from arbor_core import packet as packet_module  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="arbor", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    hook = sub.add_parser("hook", help="run a hook entrypoint against stdin")
    hook.add_argument("event", choices=sorted(hooks_module.ENTRYPOINTS))

    check = sub.add_parser("doctor", help="report the state of Arbor surfaces")
    check.add_argument("--root", type=Path, default=Path.cwd())
    check.add_argument(
        "--strict",
        action="store_true",
        help="exit nonzero unless every surface is ok",
    )

    scaffold = sub.add_parser("init", help="create missing Arbor files")
    scaffold.add_argument("--root", type=Path, default=Path.cwd())
    scaffold.add_argument("--dry-run", action="store_true")

    context = sub.add_parser("context", help="print the packet SessionStart would inject")
    context.add_argument("--root", type=Path, default=Path.cwd())

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "hook":
        entrypoint = hooks_module.ENTRYPOINTS[args.event]
        code, output = entrypoint(sys.stdin.read())
        if output:
            sys.stdout.write(output)
        return code

    if args.command == "doctor":
        root = args.root.resolve()
        rows = doctor_module.collect(root)
        sys.stdout.write(doctor_module.render(root, rows))
        if args.strict and doctor_module.result(rows) != doctor_module.OK:
            return 1
        return 0

    if args.command == "init":
        try:
            actions = init_module.run(args.root.resolve(), dry_run=args.dry_run)
        except init_module.InitError as exc:
            sys.stderr.write(f"arbor init: {exc}\n")
            return 2
        sys.stdout.write(init_module.render(args.root.resolve(), actions))
        return 0

    if args.command == "context":
        rendered, receipt = packet_module.build(args.root.resolve())
        sys.stdout.write(rendered)
        sys.stderr.write(f"{receipt}\n")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
