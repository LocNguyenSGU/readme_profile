from datetime import datetime, timezone

import pytest

from readme_updater.models import ContributionRecord, RepositoryContributions
from readme_updater.readme_renderer import (
    ReadmeMarkerError,
    format_stars,
    render_full_readme,
    render_readme_block,
    replace_marker_block,
)


def make_group() -> RepositoryContributions:
    contribution = ContributionRecord(
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        repo_owner="owner",
        repo_name="repo",
        upstream_stars=12400,
        pr_number=101,
        pr_title="Improve parser fallback",
        pr_url="https://github.com/owner/repo/pull/101",
        merged_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
        author_login="nguyenhuuloc",
        head_repo_full_name="nguyenhuuloc/repo",
        head_repo_owner="nguyenhuuloc",
        head_repo_is_fork=True,
        head_repo_exists=True,
        base_repo_owner="owner",
        is_merged=True,
    )
    return RepositoryContributions(
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        upstream_stars=12400,
        contributions=[contribution],
    )


def make_group_with_title(title: str) -> RepositoryContributions:
    group = make_group()
    contribution = group.contributions[0]
    return RepositoryContributions(
        repo_full_name=group.repo_full_name,
        repo_url=group.repo_url,
        upstream_stars=group.upstream_stars,
        contributions=[
            ContributionRecord(
                repo_full_name=contribution.repo_full_name,
                repo_url=contribution.repo_url,
                repo_owner=contribution.repo_owner,
                repo_name=contribution.repo_name,
                upstream_stars=contribution.upstream_stars,
                pr_number=contribution.pr_number,
                pr_title=title,
                pr_url=contribution.pr_url,
                merged_at=contribution.merged_at,
                author_login=contribution.author_login,
                head_repo_full_name=contribution.head_repo_full_name,
                head_repo_owner=contribution.head_repo_owner,
                head_repo_is_fork=contribution.head_repo_is_fork,
                head_repo_exists=contribution.head_repo_exists,
                base_repo_owner=contribution.base_repo_owner,
                is_merged=contribution.is_merged,
            )
        ],
    )


def test_format_stars_abbreviates_thousands() -> None:
    assert format_stars(12400) == "12.4k"


def test_render_readme_block_includes_repo_and_latest_merge() -> None:
    block = render_readme_block([make_group()], days=30)
    assert "### SVG Cards By Repository" in block
    assert "<table>" in block
    assert '<th>Repository</th>' in block
    assert '<th>Latest Merge</th>' in block
    assert '<th>Contribution Card</th>' in block
    assert '<th>Merged PRs</th>' not in block
    assert '<td><a href="https://github.com/owner/repo">owner/repo</a></td>' in block
    assert "<td>2026-04-10</td>" in block
    assert "./assets/contributions-owner-repo.svg" in block


def test_render_readme_block_escapes_markdown_breaking_title_characters() -> None:
    block = render_readme_block([make_group_with_title("Fix ] bracket handling")], days=30)
    assert '<td><a href="https://github.com/owner/repo">owner/repo</a></td>' in block


def test_render_readme_block_includes_empty_state_when_no_groups() -> None:
    block = render_readme_block([], days=30)
    assert "No merged upstream contributions in the selected time window." in block


def test_replace_marker_block_replaces_existing_content() -> None:
    original = "before\n<!-- contributions:start -->\nold\n<!-- contributions:end -->\nafter\n"
    updated = replace_marker_block(original, "new block")
    assert (
        updated
        == "before\n<!-- contributions:start -->\nnew block\n<!-- contributions:end -->\nafter\n"
    )


def test_replace_marker_block_rejects_malformed_marker_ordering() -> None:
    malformed = "before\n<!-- contributions:end -->\nold\n<!-- contributions:start -->\nafter\n"
    with pytest.raises(ReadmeMarkerError):
        replace_marker_block(malformed, "new")


def test_replace_marker_block_skips_exact_duplicate_block() -> None:
    original = "before\n<!-- contributions:start -->\nold\n<!-- contributions:end -->\nafter\n"
    updated = replace_marker_block(original, "old")
    assert updated == original


def test_replace_marker_block_requires_both_markers() -> None:
    with pytest.raises(ReadmeMarkerError):
        replace_marker_block("missing markers", "new")


def test_render_full_readme_appends_marker_block_when_missing() -> None:
    original = "# Profile\n"

    updated = render_full_readme(original, [make_group()], days=30)

    assert updated.endswith("<!-- contributions:end -->\n")
    assert "## Recent Open Source Contributions" in updated
    assert '<td><a href="https://github.com/owner/repo">owner/repo</a></td>' in updated


def test_render_full_readme_appends_only_repos_not_already_present() -> None:
    original = """# Profile

## Recent Open Source Contributions

<table>
  <tr>
    <th>Repository</th>
    <th>Latest Merge</th>
    <th>Contribution Card</th>
  </tr>
  <tr>
    <td><a href="https://github.com/owner/repo">owner/repo</a></td>
    <td>2026-04-10</td>
    <td align="center">
      <img src="./assets/contributions-owner-repo.svg" alt="owner/repo contribution card" width="420" />
    </td>
  </tr>
</table>
"""

    updated = render_full_readme(original, [make_group()], days=30)

    assert updated == original
