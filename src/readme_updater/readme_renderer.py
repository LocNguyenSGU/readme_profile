from __future__ import annotations

import re
from datetime import datetime

from readme_updater.models import RepositoryContributions

START_MARKER = "<!-- contributions:start -->"
END_MARKER = "<!-- contributions:end -->"
REPO_LINK_PATTERN = re.compile(
    r'<a href="https://github\.com/[^"/]+/[^"/]+">([^<]+)</a>'
)


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


def _format_merge_date(value: datetime | None) -> str:
    if value is None:
        return "Unknown"
    return value.date().isoformat()


def _latest_merge_date(group: RepositoryContributions) -> str:
    merged_at_values = [
        contribution.merged_at
        for contribution in group.contributions
        if contribution.merged_at is not None
    ]
    return _format_merge_date(max(merged_at_values, default=None))


def _extract_repo_names(readme_text: str) -> set[str]:
    return {match.group(1).strip() for match in REPO_LINK_PATTERN.finditer(readme_text)}


def wrap_marker_block(block_text: str) -> str:
    return f"{START_MARKER}\n{block_text.strip()}\n{END_MARKER}"


def render_readme_block(groups: list[RepositoryContributions], *, days: int) -> str:
    lines = [
        "## Recent Open Source Contributions",
        "",
        "### SVG Cards By Repository",
        "",
    ]

    if not groups:
        lines.append("No merged upstream contributions in the selected time window.")
        return "\n".join(lines)

    lines.extend(
        [
            "<table>",
            "  <tr>",
            "    <th>Repository</th>",
            "    <th>Latest Merge</th>",
            "    <th>Contribution Card</th>",
            "  </tr>",
        ]
    )

    for group in groups:
        file_name = f"contributions-{_slugify_repo_name(group.repo_full_name)}.svg"
        lines.extend(
            [
                "  <tr>",
                (
                    f'    <td><a href="{group.repo_url}">{_escape_link_text(group.repo_full_name)}</a></td>'
                ),
                f"    <td>{_latest_merge_date(group)}</td>",
                '    <td align="center">',
                (
                    f'      <img src="./assets/{file_name}" '
                    f'alt="{_escape_link_text(group.repo_full_name)} contribution card" width="420" />'
                ),
                "    </td>",
                "  </tr>",
            ]
        )

    lines.append("</table>")

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

    existing = readme_text[start_index:end_index].strip()
    candidate = block_text.strip()

    if existing == candidate:
        return readme_text

    merged = candidate

    before = readme_text[:start_index]
    after = readme_text[end_index:]
    return f"{before}\n{merged}\n{after}"


def render_full_readme(
    readme_text: str,
    groups: list[RepositoryContributions],
    *,
    days: int,
) -> str:
    block_text = render_readme_block(groups, days=days)
    if START_MARKER in readme_text or END_MARKER in readme_text:
        return replace_marker_block(readme_text, block_text)

    existing_repos = _extract_repo_names(readme_text)
    groups_to_append = [
        group for group in groups if group.repo_full_name not in existing_repos
    ]
    if not groups_to_append:
        return readme_text

    wrapped_block = wrap_marker_block(render_readme_block(groups_to_append, days=days))
    if wrapped_block in readme_text:
        return readme_text

    separator = "\n" if readme_text.endswith("\n") else "\n\n"
    return f"{readme_text}{separator}{wrapped_block}\n"
