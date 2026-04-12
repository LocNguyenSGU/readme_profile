from __future__ import annotations

from readme_updater.models import RepositoryContributions

START_MARKER = "<!-- contributions:start -->"
END_MARKER = "<!-- contributions:end -->"


class ReadmeMarkerError(ValueError):
    pass


def format_stars(count: int) -> str:
    if count < 1000:
        return str(count)

    value = count / 1000
    if count % 1000 == 0:
        return f"{int(value)}k"
    return f"{value:.1f}k"


def _escape_link_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("]", "\\]")


def _slugify_repo_name(repo_full_name: str) -> str:
    slug = repo_full_name.lower().replace("/", "-")
    slug = "".join(char if char.isalnum() or char == "-" else "-" for char in slug)
    while "--" in slug:
        slug = slug.replace("--", "-")
    slug = slug.strip("-")
    return slug or "repo"


def render_readme_block(groups: list[RepositoryContributions], *, days: int) -> str:
    total_prs = sum(len(group.contributions) for group in groups)
    total_repos = len(groups)
    top_group = max(groups, key=lambda item: item.upstream_stars, default=None)

    lines = [
        "## Recent Open Source Contributions",
        "",
        f"_Merged in the last {days} days_",
        "",
    ]

    if not groups:
        lines.append("No merged upstream contributions in the selected time window.")
        return "\n".join(lines)

    lines.extend(
        [
            "### Contribution Snapshot",
            "",
            '<p align="center">',
            '  <img src="./assets/contributions.svg" alt="Contribution summary card" width="88%"/>',
            "</p>",
            "",
            "| Metric | Value |",
            "|---|---|",
            f"| Total merged PRs | {total_prs} |",
            f"| Repositories | {total_repos} |",
            (
                f"| Top repository | [{top_group.repo_full_name}]({top_group.repo_url}) "
                f"({format_stars(top_group.upstream_stars)} stars) |"
                if top_group
                else "| Top repository | N/A |"
            ),
            "",
            "### Contribution Table",
            "",
            "| Repository | Stars | PR | Merged |",
            "|---|---:|---|---|",
        ]
    )

    for group in groups:
        for contribution in group.contributions:
            merged_date = contribution.merged_at.date().isoformat()
            lines.append(
                "| "
                f"[{group.repo_full_name}]({group.repo_url}) | "
                f"{format_stars(group.upstream_stars)} | "
                f"[{_escape_link_text(contribution.pr_title)}]({contribution.pr_url}) | "
                f"{merged_date} |"
            )

    lines.extend(
        [
            "",
            "### SVG Cards By Repository",
            "",
            '<p align="center">',
        ]
    )

    for group in groups:
        file_name = f"contributions-{_slugify_repo_name(group.repo_full_name)}.svg"
        lines.extend(
            [
                (
                    f'  <img src="./assets/{file_name}" '
                    f'alt="{_escape_link_text(group.repo_full_name)} contribution card" width="88%"/>'
                ),
                "  <br/>",
            ]
        )

    lines.append("</p>")

    return "\n".join(lines).rstrip()


def replace_marker_block(readme_text: str, block_text: str) -> str:
    if START_MARKER not in readme_text or END_MARKER not in readme_text:
        raise ReadmeMarkerError("README is missing contributions markers")

    start_marker_index = readme_text.index(START_MARKER)
    end_marker_index = readme_text.index(END_MARKER)
    if end_marker_index < start_marker_index:
        raise ReadmeMarkerError("README contributions markers are out of order")

    start_index = start_marker_index + len(START_MARKER)
    end_index = end_marker_index

    before = readme_text[:start_index]
    after = readme_text[end_index:]
    return f"{before}\n{block_text}\n{after}"
