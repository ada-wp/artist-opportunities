from __future__ import annotations

import argparse
from pathlib import Path

from .recommend import recommend_for_artist
from .render import render_json, render_markdown
from .ui_prototype import write_ui_prototype


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Recommend top open calls for painters.")
    parser.add_argument("--artist-id", required=True, help="Artist profile id from seed fixtures.")
    parser.add_argument(
        "--format",
        choices=["json", "markdown", "both"],
        default="both",
        help="Output format.",
    )
    parser.add_argument(
        "--output-dir",
        help="Optional directory to write recommendation files.",
    )
    parser.add_argument(
        "--write-ui-prototype",
        help="Optional path to write the workflow prototype UI HTML.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.write_ui_prototype:
        path = write_ui_prototype(args.write_ui_prototype)
        print(f"Wrote UI prototype to {path}")
        return

    payload = recommend_for_artist(args.artist_id)

    json_output = render_json(payload)
    markdown_output = render_markdown(payload)

    if args.format in {"json", "both"}:
        print(json_output)
    if args.format in {"markdown", "both"}:
        print(markdown_output)

    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if args.format in {"json", "both"}:
            (output_dir / f"{args.artist_id}.json").write_text(json_output, encoding="utf-8")
        if args.format in {"markdown", "both"}:
            (output_dir / f"{args.artist_id}.md").write_text(markdown_output, encoding="utf-8")
