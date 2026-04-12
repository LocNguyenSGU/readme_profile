from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from readme_updater.config import ConfigError
from readme_updater.config import load_config
from readme_updater.github_api import GitHubApiError
from readme_updater.readme_renderer import ReadmeMarkerError
from readme_updater.readme_renderer import replace_marker_block
from readme_updater.service import run_update


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="readme-updater")
    subparsers = parser.add_subparsers(dest="command", required=True)

    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("--days", type=int)
    update_parser.add_argument("--readme", type=Path)
    update_parser.add_argument("--svg-output", type=Path, dest="svg_output")
    update_parser.add_argument("--state-file", type=Path, dest="state_file")
    update_parser.add_argument("--dry-run", action="store_true")
    update_parser.add_argument("--verbose", action="store_true")
    return parser


def _slugify_repo_name(repo_full_name: str) -> str:
    slug = repo_full_name.lower().replace("/", "-")
    slug = re.sub(r"[^a-z0-9-]", "-", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "repo"


def _write_svg_outputs(svg_output: Path, result: dict[str, object]) -> None:
    svg_output.parent.mkdir(parents=True, exist_ok=True)

    # Always keep a stable summary card path for README embeds.
    summary_svg = result.get("summary_svg")
    if isinstance(summary_svg, str) and summary_svg.strip():
        svg_output.write_text(summary_svg)

    raw_cards = result.get("svg_cards")
    if not isinstance(raw_cards, list) or not raw_cards:
        if not (isinstance(summary_svg, str) and summary_svg.strip()):
            svg_output.write_text(str(result.get("svg", "")))
        return

    if len(raw_cards) == 1:
        first_card = raw_cards[0]
        if isinstance(first_card, dict):
            if not (isinstance(summary_svg, str) and summary_svg.strip()):
                svg_output.write_text(str(first_card.get("svg", result.get("svg", ""))))
            return
        if not (isinstance(summary_svg, str) and summary_svg.strip()):
            svg_output.write_text(str(result.get("svg", "")))
        return

    for card in raw_cards:
        if not isinstance(card, dict):
            continue
        repo_name = str(card.get("repo_full_name", "repo"))
        file_name = f"{svg_output.stem}-{_slugify_repo_name(repo_name)}{svg_output.suffix}"
        output_path = svg_output.parent / file_name
        output_path.write_text(str(card.get("svg", "")))


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "update":
        try:
            config = load_config(
                days=args.days,
                readme=args.readme,
                svg_output=args.svg_output,
                state_file=args.state_file,
                dry_run=args.dry_run,
                verbose=args.verbose,
            )
            result = run_update(config)

            if config.dry_run:
                print(str(result["readme_block"]))
                return 0

            current_readme = config.readme_path.read_text()
            updated_readme = replace_marker_block(current_readme, str(result["readme_block"]))
            config.readme_path.write_text(updated_readme)
            _write_svg_outputs(config.svg_output, result)
            return 0
        except (ConfigError, GitHubApiError, ReadmeMarkerError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
