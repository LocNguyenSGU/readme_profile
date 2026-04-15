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

    if not existing:
        merged = candidate
    elif candidate in existing:
        merged = existing
    else:
        merged = f"{existing}\n\n{candidate}"

    before = readme_text[:start_index]
    after = readme_text[end_index:]
    return f"{before}\n{merged}\n{after}"
