"""
DocStream command-line interface.

Usage:
    docstream convert paper.pdf --template ieee --output ./out
    docstream extract paper.pdf --output blocks.json
    docstream templates list
    docstream --version
"""

from __future__ import annotations

import argparse
import json
import sys
import threading
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Progress spinner (runs in a daemon thread)
# ---------------------------------------------------------------------------


def _spinner(stop_event: threading.Event, message: str) -> None:
    frames = ["|", "/", "-", "\\"]
    i = 0
    while not stop_event.is_set():
        sys.stderr.write(f"\r  {message} {frames[i % len(frames)]}")
        sys.stderr.flush()
        time.sleep(0.1)
        i += 1
    sys.stderr.write(f"\r  {message} done\n")
    sys.stderr.flush()


def _with_progress(message: str, fn, *args, **kwargs):
    """Run *fn* while showing a progress spinner on stderr."""
    stop = threading.Event()
    t = threading.Thread(target=_spinner, args=(stop, message), daemon=True)
    t.start()
    try:
        return fn(*args, **kwargs)
    finally:
        stop.set()
        t.join(timeout=1.0)


# ---------------------------------------------------------------------------
# Sub-command handlers
# ---------------------------------------------------------------------------


def _cmd_convert(args: argparse.Namespace) -> int:
    import docstream

    try:
        result = _with_progress(
            f"Converting {Path(args.input).name}",
            docstream.convert,
            args.input,
            template=args.template,
            output_dir=args.output,
        )
        if result.success:
            print(f"\n  PDF   -> {result.pdf_path}")
            print(f"  LaTeX -> {result.tex_path}")
            print(
                f"  Template: {result.template_used}"
                f"  |  Time: {result.processing_time_seconds:.2f}s"
            )
            return 0
        else:
            print(f"\n  Error: {result.error}", file=sys.stderr)
            return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\n  Error: {exc}", file=sys.stderr)
        return 1


def _cmd_extract(args: argparse.Namespace) -> int:
    import docstream

    try:
        blocks = _with_progress(
            f"Extracting {Path(args.input).name}",
            docstream.extract,
            args.input,
        )
        payload = [b.model_dump(mode="json") for b in blocks]
        if args.output:
            out_path = Path(args.output)
            out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
            print(f"\n  Extracted {len(blocks)} block(s) -> {out_path}")
        else:
            print(json.dumps(payload, indent=2, default=str))
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"\n  Error: {exc}", file=sys.stderr)
        return 1


def _cmd_templates_list(_args: argparse.Namespace) -> int:
    templates = {
        "report": "Academic report — article class, 1in margins, serif (lmodern)",
        "ieee": "IEEE two-column conference format (IEEEtran class)",
        "resume": "Clean resume — compact margins, no section numbers",
    }
    print("Available templates:\n")
    for name, desc in templates.items():
        print(f"  {name:<10}  {desc}")
    print()
    return 0


# ---------------------------------------------------------------------------
# Parser factory (also used by tests)
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    from docstream import __version__

    parser = argparse.ArgumentParser(
        prog="docstream",
        description="DocStream — professional document conversion (PDF -> LaTeX + PDF)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  docstream convert paper.pdf --template ieee --output ./out\n"
            "  docstream extract paper.pdf --output blocks.json\n"
            "  docstream templates list\n"
        ),
    )
    parser.add_argument(
        "--version",
        "-V",
        action="version",
        version=f"docstream {__version__}",
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # -- convert -------------------------------------------------------------
    p_conv = sub.add_parser(
        "convert",
        help="Convert a PDF to LaTeX + PDF via the full pipeline",
    )
    p_conv.add_argument("input", help="Path to the input PDF file")
    p_conv.add_argument(
        "--template",
        "-t",
        default="report",
        choices=["report", "ieee", "resume"],
        metavar="TEMPLATE",
        help="Output template: report | ieee | resume  (default: report)",
    )
    p_conv.add_argument(
        "--output",
        "-o",
        default="./out",
        metavar="DIR",
        help="Output directory for .tex and .pdf files  (default: ./out)",
    )

    # -- extract -------------------------------------------------------------
    p_ext = sub.add_parser(
        "extract",
        help="Extract raw content blocks from a PDF and emit JSON",
    )
    p_ext.add_argument("input", help="Path to the input PDF file")
    p_ext.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="Save extracted blocks as JSON (default: print to stdout)",
    )

    # -- templates -----------------------------------------------------------
    p_tpl = sub.add_parser("templates", help="Template management")
    tpl_sub = p_tpl.add_subparsers(dest="templates_command", metavar="SUBCOMMAND")
    tpl_sub.add_parser("list", help="List available built-in templates")

    return parser


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Parse CLI arguments and dispatch to the appropriate handler.

    Returns:
        Exit code — 0 on success, 1 on error.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "convert":
        return _cmd_convert(args)
    elif args.command == "extract":
        return _cmd_extract(args)
    elif args.command == "templates":
        if getattr(args, "templates_command", None) == "list":
            return _cmd_templates_list(args)
        else:
            parser.parse_args(["templates", "--help"])
            return 1
    else:
        parser.print_help()
        return 0


def _cli_entry() -> None:
    """Registered entry point: ``docstream = "docstream.cli:_cli_entry"``."""
    sys.exit(main())


if __name__ == "__main__":
    _cli_entry()
