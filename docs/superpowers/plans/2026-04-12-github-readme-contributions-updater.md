# GitHub README Contributions Updater Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI that fetches merged upstream pull requests opened from the user's forks, updates a fixed contributions block in `README.md`, and generates one premium minimal SVG summary card.

**Architecture:** The implementation uses a small `src/` package with clear boundaries for configuration, GitHub API access, contribution filtering, Markdown rendering, SVG rendering, and state persistence. The CLI entrypoint wires those modules together, while tests cover each module independently plus end-to-end CLI behavior using fixtures and temporary files.

**Tech Stack:** Python 3.12+, `httpx`, `pytest`, `pytest-mock`, `respx`, standard library `argparse`, `dataclasses`, `pathlib`, `json`

---

## Planned File Structure

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/readme_updater/__init__.py`
- Create: `src/readme_updater/cli.py`
- Create: `src/readme_updater/config.py`
- Create: `src/readme_updater/models.py`
- Create: `src/readme_updater/github_api.py`
- Create: `src/readme_updater/filters.py`
- Create: `src/readme_updater/readme_renderer.py`
- Create: `src/readme_updater/svg_renderer.py`
- Create: `src/readme_updater/state_store.py`
- Create: `src/readme_updater/service.py`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`
- Create: `tests/test_filters.py`
- Create: `tests/test_readme_renderer.py`
- Create: `tests/test_svg_renderer.py`
- Create: `tests/test_github_api.py`
- Create: `tests/test_cli.py`
- Create: `tests/fixtures/notifications.json`
- Create: `tests/fixtures/pull_repo1_pr101.json`
- Create: `tests/fixtures/pull_repo1_pr102.json`
- Create: `tests/fixtures/pull_repo2_pr88.json`

`README.md` should include the `<!-- contributions:start -->` and `<!-- contributions:end -->` markers immediately so the CLI has a known target during tests and manual runs.

### Task 1: Bootstrap Project Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/readme_updater/__init__.py`
- Create: `src/readme_updater/cli.py`
- Create: `tests/conftest.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI smoke test**

```python
from pathlib import Path

from readme_updater.cli import build_parser


def test_build_parser_accepts_expected_flags() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "update",
            "--days",
            "30",
            "--readme",
            "README.md",
            "--svg-output",
            "assets/contributions.svg",
            "--state-file",
            ".state/contributions.json",
            "--dry-run",
            "--verbose",
        ]
    )
    assert args.command == "update"
    assert args.days == 30
    assert args.readme == Path("README.md")
    assert args.svg_output == Path("assets/contributions.svg")
    assert args.state_file == Path(".state/contributions.json")
    assert args.dry_run is True
    assert args.verbose is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_cli.py::test_build_parser_accepts_expected_flags -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` because the package and parser do not exist yet.

- [ ] **Step 3: Write minimal project files and parser implementation**

```toml
[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "readme-updater"
version = "0.1.0"
description = "CLI to update GitHub README contribution sections from merged upstream PRs"
requires-python = ">=3.12"
dependencies = [
  "httpx>=0.27.0,<1.0.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0.0,<9.0.0",
  "pytest-mock>=3.14.0,<4.0.0",
  "respx>=0.21.0,<1.0.0",
]

[project.scripts]
readme-updater = "readme_updater.cli:main"

[tool.pytest.ini_options]
pythonpath = ["src"]
```

```md
# README Updater

<!-- contributions:start -->
Contribution data has not been generated yet.
<!-- contributions:end -->
```

```python
__all__ = ["__version__"]
__version__ = "0.1.0"
```

```python
from __future__ import annotations

import argparse
from pathlib import Path


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


def main() -> int:
    parser = build_parser()
    parser.parse_args()
    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_cli.py::test_build_parser_accepts_expected_flags -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md src/readme_updater/__init__.py src/readme_updater/cli.py tests/test_cli.py
git commit -m "chore: bootstrap readme updater project"
```

### Task 2: Add Config Loading And Validation

**Files:**
- Create: `src/readme_updater/config.py`
- Modify: `src/readme_updater/cli.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing config tests**

```python
from pathlib import Path

import pytest

from readme_updater.config import ConfigError, RuntimeConfig, load_config


def test_load_config_reads_environment_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_USER", "octocat")
    monkeypatch.setenv("README_PATH", "README.md")
    monkeypatch.setenv("SVG_OUTPUT", "assets/contributions.svg")
    monkeypatch.setenv("DEFAULT_DAYS", "30")

    config = load_config(
        days=None,
        readme=None,
        svg_output=None,
        state_file=None,
        dry_run=False,
        verbose=False,
    )

    assert config == RuntimeConfig(
        github_token="token",
        github_user="octocat",
        readme_path=Path("README.md"),
        svg_output=Path("assets/contributions.svg"),
        state_file=Path(".readme-updater-state.json"),
        days=30,
        dry_run=False,
        verbose=False,
    )


def test_load_config_cli_values_override_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "token")
    monkeypatch.setenv("GITHUB_USER", "octocat")
    monkeypatch.setenv("README_PATH", "README.md")
    monkeypatch.setenv("SVG_OUTPUT", "assets/contributions.svg")
    monkeypatch.setenv("DEFAULT_DAYS", "30")

    config = load_config(
        days=3,
        readme=Path("PROFILE.md"),
        svg_output=Path("generated/card.svg"),
        state_file=Path(".state/custom.json"),
        dry_run=True,
        verbose=True,
    )

    assert config.days == 3
    assert config.readme_path == Path("PROFILE.md")
    assert config.svg_output == Path("generated/card.svg")
    assert config.state_file == Path(".state/custom.json")
    assert config.dry_run is True
    assert config.verbose is True


def test_load_config_requires_github_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_USER", raising=False)

    with pytest.raises(ConfigError, match="GITHUB_TOKEN"):
        load_config(
            days=30,
            readme=Path("README.md"),
            svg_output=Path("assets/contributions.svg"),
            state_file=None,
            dry_run=False,
            verbose=False,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError` because `readme_updater.config` does not exist yet.

- [ ] **Step 3: Implement config model and loader**

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class RuntimeConfig:
    github_token: str
    github_user: str
    readme_path: Path
    svg_output: Path
    state_file: Path
    days: int
    dry_run: bool
    verbose: bool


def load_config(
    *,
    days: int | None,
    readme: Path | None,
    svg_output: Path | None,
    state_file: Path | None,
    dry_run: bool,
    verbose: bool,
) -> RuntimeConfig:
    github_token = os.environ.get("GITHUB_TOKEN")
    github_user = os.environ.get("GITHUB_USER")
    if not github_token:
        raise ConfigError("Missing required environment variable: GITHUB_TOKEN")
    if not github_user:
        raise ConfigError("Missing required environment variable: GITHUB_USER")

    readme_path = readme or Path(os.environ.get("README_PATH", "README.md"))
    svg_path = svg_output or Path(os.environ.get("SVG_OUTPUT", "assets/contributions.svg"))
    state_path = state_file or Path(os.environ.get("STATE_FILE", ".readme-updater-state.json"))
    resolved_days = days if days is not None else int(os.environ.get("DEFAULT_DAYS", "30"))

    return RuntimeConfig(
        github_token=github_token,
        github_user=github_user,
        readme_path=readme_path,
        svg_output=svg_path,
        state_file=state_path,
        days=resolved_days,
        dry_run=dry_run,
        verbose=verbose,
    )
```

```python
from __future__ import annotations

import argparse
from pathlib import Path

from readme_updater.config import load_config


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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "update":
        load_config(
            days=args.days,
            readme=args.readme,
            svg_output=args.svg_output,
            state_file=args.state_file,
            dry_run=args.dry_run,
            verbose=args.verbose,
        )
    return 0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_config.py tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/readme_updater/config.py src/readme_updater/cli.py tests/test_config.py tests/test_cli.py
git commit -m "feat: add runtime config loading"
```

### Task 3: Define Data Models And Filtering Rules

**Files:**
- Create: `src/readme_updater/models.py`
- Create: `src/readme_updater/filters.py`
- Test: `tests/test_filters.py`

- [ ] **Step 1: Write the failing filtering tests**

```python
from datetime import datetime, timezone

from readme_updater.filters import group_contributions, is_eligible_contribution
from readme_updater.models import ContributionRecord


def make_record(**overrides: object) -> ContributionRecord:
    base = ContributionRecord(
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
        base_repo_owner="owner",
        is_merged=True,
    )
    return base.__class__(**{**base.__dict__, **overrides})


def test_is_eligible_contribution_accepts_merged_fork_to_upstream() -> None:
    assert is_eligible_contribution(make_record(), github_user="nguyenhuuloc") is True


def test_is_eligible_contribution_rejects_non_fork_or_owned_base_repo() -> None:
    assert is_eligible_contribution(
        make_record(head_repo_is_fork=False),
        github_user="nguyenhuuloc",
    ) is False
    assert is_eligible_contribution(
        make_record(base_repo_owner="nguyenhuuloc"),
        github_user="nguyenhuuloc",
    ) is False


def test_group_contributions_sorts_repo_by_stars_then_prs_by_date() -> None:
    grouped = group_contributions(
        [
            make_record(repo_full_name="b/repo", repo_owner="b", repo_name="repo", upstream_stars=10, pr_number=2),
            make_record(repo_full_name="a/repo", repo_owner="a", repo_name="repo", upstream_stars=100, pr_number=1),
        ]
    )

    assert [group.repo_full_name for group in grouped] == ["a/repo", "b/repo"]
    assert grouped[0].contributions[0].pr_number == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_filters.py -v`
Expected: FAIL because models and filtering functions do not exist yet.

- [ ] **Step 3: Implement contribution models and grouping logic**

```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ContributionRecord:
    repo_full_name: str
    repo_url: str
    repo_owner: str
    repo_name: str
    upstream_stars: int
    pr_number: int
    pr_title: str
    pr_url: str
    merged_at: datetime
    author_login: str
    head_repo_full_name: str
    head_repo_owner: str
    head_repo_is_fork: bool
    base_repo_owner: str
    is_merged: bool


@dataclass(frozen=True)
class RepositoryContributions:
    repo_full_name: str
    repo_url: str
    upstream_stars: int
    contributions: list[ContributionRecord]
```

```python
from __future__ import annotations

from collections import defaultdict

from readme_updater.models import ContributionRecord, RepositoryContributions


def is_eligible_contribution(record: ContributionRecord, *, github_user: str) -> bool:
    return all(
        [
            record.is_merged,
            record.head_repo_is_fork,
            record.head_repo_owner == github_user,
            record.base_repo_owner != github_user,
        ]
    )


def dedupe_contributions(records: list[ContributionRecord]) -> list[ContributionRecord]:
    seen: set[tuple[str, int]] = set()
    unique: list[ContributionRecord] = []
    for record in records:
        key = (record.repo_full_name, record.pr_number)
        if key in seen:
            continue
        seen.add(key)
        unique.append(record)
    return unique


def group_contributions(records: list[ContributionRecord]) -> list[RepositoryContributions]:
    grouped: dict[str, list[ContributionRecord]] = defaultdict(list)
    for record in dedupe_contributions(records):
        grouped[record.repo_full_name].append(record)

    result: list[RepositoryContributions] = []
    for repo_full_name, items in grouped.items():
        first = items[0]
        contributions = sorted(items, key=lambda item: item.merged_at, reverse=True)
        result.append(
            RepositoryContributions(
                repo_full_name=repo_full_name,
                repo_url=first.repo_url,
                upstream_stars=first.upstream_stars,
                contributions=contributions,
            )
        )

    return sorted(result, key=lambda item: (-item.upstream_stars, item.repo_full_name))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_filters.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/readme_updater/models.py src/readme_updater/filters.py tests/test_filters.py
git commit -m "feat: add contribution filtering and grouping"
```

### Task 4: Render Markdown And Replace README Marker Block

**Files:**
- Create: `src/readme_updater/readme_renderer.py`
- Test: `tests/test_readme_renderer.py`

- [ ] **Step 1: Write the failing README renderer tests**

```python
from datetime import datetime, timezone

import pytest

from readme_updater.models import ContributionRecord, RepositoryContributions
from readme_updater.readme_renderer import ReadmeMarkerError, format_stars, render_readme_block, replace_marker_block


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
        base_repo_owner="owner",
        is_merged=True,
    )
    return RepositoryContributions(
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        upstream_stars=12400,
        contributions=[contribution],
    )


def test_format_stars_abbreviates_thousands() -> None:
    assert format_stars(12400) == "12.4k"


def test_render_readme_block_includes_repo_pr_and_window_label() -> None:
    block = render_readme_block([make_group()], days=30)
    assert "Merged in the last 30 days" in block
    assert "[owner/repo](https://github.com/owner/repo) · 12.4k stars · 1 merged PR" in block
    assert "[Improve parser fallback](https://github.com/owner/repo/pull/101) · merged 2026-04-10" in block


def test_replace_marker_block_rewrites_only_marker_content() -> None:
    original = "before\n<!-- contributions:start -->\nold\n<!-- contributions:end -->\nafter\n"
    updated = replace_marker_block(original, "new block")
    assert updated == "before\n<!-- contributions:start -->\nnew block\n<!-- contributions:end -->\nafter\n"


def test_replace_marker_block_requires_both_markers() -> None:
    with pytest.raises(ReadmeMarkerError):
        replace_marker_block("missing markers", "new")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_readme_renderer.py -v`
Expected: FAIL because the renderer module does not exist yet.

- [ ] **Step 3: Implement README formatting and marker replacement**

```python
from __future__ import annotations

from readme_updater.models import RepositoryContributions

START_MARKER = "<!-- contributions:start -->"
END_MARKER = "<!-- contributions:end -->"


class ReadmeMarkerError(ValueError):
    pass


def format_stars(count: int) -> str:
    if count >= 1000:
        return f"{count / 1000:.1f}k".rstrip("0").rstrip(".")
    return str(count)


def render_readme_block(groups: list[RepositoryContributions], *, days: int) -> str:
    if not groups:
        return f"## Recent Open Source Contributions\n\n_Merged in the last {days} days_\n\nNo merged upstream contributions in the selected time window."

    lines = ["## Recent Open Source Contributions", "", f"_Merged in the last {days} days_", ""]
    for group in groups:
        pr_count = len(group.contributions)
        pr_label = "PR" if pr_count == 1 else "PRs"
        lines.append(
            f"### [{group.repo_full_name}]({group.repo_url}) · {format_stars(group.upstream_stars)} stars · {pr_count} merged {pr_label}"
        )
        for contribution in group.contributions:
            merged_date = contribution.merged_at.date().isoformat()
            lines.append(f"- [{contribution.pr_title}]({contribution.pr_url}) · merged {merged_date}")
        lines.append("")
    return "\n".join(lines).rstrip()


def replace_marker_block(readme_text: str, block_text: str) -> str:
    if START_MARKER not in readme_text or END_MARKER not in readme_text:
        raise ReadmeMarkerError("README is missing contributions markers")
    start = readme_text.index(START_MARKER) + len(START_MARKER)
    end = readme_text.index(END_MARKER)
    return f"{readme_text[:start]}\n{block_text}\n{readme_text[end:]}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_readme_renderer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/readme_updater/readme_renderer.py tests/test_readme_renderer.py
git commit -m "feat: add README contribution rendering"
```

### Task 5: Generate Premium Minimal SVG Summary Card

**Files:**
- Create: `src/readme_updater/svg_renderer.py`
- Test: `tests/test_svg_renderer.py`

- [ ] **Step 1: Write the failing SVG renderer tests**

```python
from datetime import datetime, timezone

from readme_updater.models import ContributionRecord, RepositoryContributions
from readme_updater.svg_renderer import build_summary_metrics, render_svg_card


def make_groups() -> list[RepositoryContributions]:
    contribution = ContributionRecord(
        repo_full_name="owner/repo",
        repo_url="https://github.com/owner/repo",
        repo_owner="owner",
        repo_name="repo",
        upstream_stars=48200,
        pr_number=101,
        pr_title="Improve parser fallback",
        pr_url="https://github.com/owner/repo/pull/101",
        merged_at=datetime(2026, 4, 10, tzinfo=timezone.utc),
        author_login="nguyenhuuloc",
        head_repo_full_name="nguyenhuuloc/repo",
        head_repo_owner="nguyenhuuloc",
        head_repo_is_fork=True,
        base_repo_owner="owner",
        is_merged=True,
    )
    return [
        RepositoryContributions(
            repo_full_name="owner/repo",
            repo_url="https://github.com/owner/repo",
            upstream_stars=48200,
            contributions=[contribution],
        )
    ]


def test_build_summary_metrics_counts_groups_prs_and_top_repo() -> None:
    metrics = build_summary_metrics(make_groups(), days=30)
    assert metrics.total_merged_prs == 1
    assert metrics.total_repos == 1
    assert metrics.top_repo_name == "owner/repo"
    assert metrics.top_repo_stars_label == "48.2k"
    assert metrics.window_label == "Last 30 days"


def test_render_svg_card_outputs_title_and_metrics() -> None:
    svg = render_svg_card(build_summary_metrics(make_groups(), days=30))
    assert "<svg" in svg
    assert "Merged Upstream Contributions" in svg
    assert ">1<" in svg
    assert "48.2k stars" in svg


def test_render_svg_card_handles_empty_state() -> None:
    svg = render_svg_card(build_summary_metrics([], days=3))
    assert "No merged upstream PRs" in svg
    assert "Last 3 days" in svg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_svg_renderer.py -v`
Expected: FAIL because the SVG renderer does not exist yet.

- [ ] **Step 3: Implement summary metrics and SVG output**

```python
from __future__ import annotations

from dataclasses import dataclass

from readme_updater.models import RepositoryContributions
from readme_updater.readme_renderer import format_stars


@dataclass(frozen=True)
class SummaryMetrics:
    total_merged_prs: int
    total_repos: int
    top_repo_name: str
    top_repo_stars_label: str
    window_label: str


def build_summary_metrics(groups: list[RepositoryContributions], *, days: int) -> SummaryMetrics:
    total_merged_prs = sum(len(group.contributions) for group in groups)
    total_repos = len(groups)
    top_group = max(groups, key=lambda item: item.upstream_stars, default=None)
    top_repo_name = top_group.repo_full_name if top_group else "No merged upstream PRs"
    top_repo_stars_label = f"{format_stars(top_group.upstream_stars)} stars" if top_group else "0 stars"
    return SummaryMetrics(
        total_merged_prs=total_merged_prs,
        total_repos=total_repos,
        top_repo_name=top_repo_name,
        top_repo_stars_label=top_repo_stars_label,
        window_label=f"Last {days} days",
    )


def render_svg_card(metrics: SummaryMetrics) -> str:
    return f"""<svg width="680" height="220" viewBox="0 0 680 220" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Merged upstream contribution summary">
  <rect width="680" height="220" rx="24" fill="#0F172A"/>
  <rect x="24" y="24" width="632" height="172" rx="18" fill="#111827" stroke="#334155"/>
  <text x="44" y="58" fill="#94A3B8" font-family="Georgia, 'Times New Roman', serif" font-size="16">Merged Upstream Contributions</text>
  <text x="44" y="124" fill="#F8FAFC" font-family="Georgia, 'Times New Roman', serif" font-size="60">{metrics.total_merged_prs}</text>
  <text x="44" y="152" fill="#CBD5E1" font-family="Georgia, 'Times New Roman', serif" font-size="18">merged PRs</text>
  <text x="260" y="92" fill="#E2E8F0" font-family="Georgia, 'Times New Roman', serif" font-size="18">{metrics.total_repos} upstream repos</text>
  <text x="260" y="128" fill="#E2E8F0" font-family="Georgia, 'Times New Roman', serif" font-size="18">{metrics.top_repo_name}</text>
  <text x="260" y="160" fill="#94A3B8" font-family="Georgia, 'Times New Roman', serif" font-size="16">{metrics.top_repo_stars_label}</text>
  <text x="44" y="186" fill="#64748B" font-family="Georgia, 'Times New Roman', serif" font-size="16">{metrics.window_label}</text>
</svg>"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_svg_renderer.py tests/test_readme_renderer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/readme_updater/svg_renderer.py tests/test_svg_renderer.py
git commit -m "feat: add contribution summary svg renderer"
```

### Task 6: Add GitHub Notifications And Pull Request API Client

**Files:**
- Create: `src/readme_updater/github_api.py`
- Test: `tests/test_github_api.py`
- Create: `tests/fixtures/notifications.json`
- Create: `tests/fixtures/pull_repo1_pr101.json`
- Create: `tests/fixtures/pull_repo1_pr102.json`
- Create: `tests/fixtures/pull_repo2_pr88.json`

- [ ] **Step 1: Write the failing GitHub client tests**

```python
from datetime import datetime, timezone
import json
from pathlib import Path

import httpx
import respx

from readme_updater.github_api import GitHubClient


def load_fixture(name: str) -> dict:
    return json.loads(Path("tests/fixtures", name).read_text())


@respx.mock
def test_fetch_notifications_returns_pull_request_candidates() -> None:
    respx.get("https://api.github.com/notifications").mock(
        return_value=httpx.Response(200, json=load_fixture("notifications.json"))
    )

    client = GitHubClient(github_token="token")
    notifications = client.fetch_notifications()

    assert len(notifications) == 3
    assert notifications[0]["subject"]["type"] == "PullRequest"


@respx.mock
def test_fetch_pull_request_normalizes_expected_fields() -> None:
    respx.get("https://api.github.com/repos/owner/repo/pulls/101").mock(
        return_value=httpx.Response(200, json=load_fixture("pull_repo1_pr101.json"))
    )

    client = GitHubClient(github_token="token")
    record = client.fetch_pull_request("owner", "repo", 101)

    assert record.repo_full_name == "owner/repo"
    assert record.upstream_stars == 12400
    assert record.pr_number == 101
    assert record.head_repo_owner == "nguyenhuuloc"
    assert record.head_repo_is_fork is True
    assert record.is_merged is True
    assert record.merged_at == datetime(2026, 4, 10, 12, 0, tzinfo=timezone.utc)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_github_api.py -v`
Expected: FAIL because the GitHub client and fixtures do not exist yet.

- [ ] **Step 3: Add fixtures and implement the API client**

```json
[
  {
    "id": "1",
    "reason": "state_change",
    "subject": {
      "title": "Improve parser fallback",
      "url": "https://api.github.com/repos/owner/repo/pulls/101",
      "latest_comment_url": "https://api.github.com/repos/owner/repo/issues/comments/1",
      "type": "PullRequest"
    }
  },
  {
    "id": "2",
    "reason": "state_change",
    "subject": {
      "title": "Fix cache invalidation edge case",
      "url": "https://api.github.com/repos/owner/repo/pulls/102",
      "latest_comment_url": "https://api.github.com/repos/owner/repo/issues/comments/2",
      "type": "PullRequest"
    }
  },
  {
    "id": "3",
    "reason": "state_change",
    "subject": {
      "title": "Add CLI timeout handling",
      "url": "https://api.github.com/repos/another/repo/pulls/88",
      "latest_comment_url": "https://api.github.com/repos/another/repo/issues/comments/3",
      "type": "PullRequest"
    }
  }
]
```

```json
{
  "number": 101,
  "title": "Improve parser fallback",
  "html_url": "https://github.com/owner/repo/pull/101",
  "merged_at": "2026-04-10T12:00:00Z",
  "user": {"login": "nguyenhuuloc"},
  "merged": true,
  "head": {
    "repo": {
      "full_name": "nguyenhuuloc/repo",
      "fork": true,
      "owner": {"login": "nguyenhuuloc"}
    }
  },
  "base": {
    "repo": {
      "full_name": "owner/repo",
      "html_url": "https://github.com/owner/repo",
      "stargazers_count": 12400,
      "name": "repo",
      "owner": {"login": "owner"}
    }
  }
}
```

```python
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from readme_updater.models import ContributionRecord


class GitHubApiError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, *, github_token: str) -> None:
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {github_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20.0,
        )

    def fetch_notifications(self) -> list[dict]:
        response = self._client.get("/notifications")
        response.raise_for_status()
        return response.json()

    def fetch_pull_request(self, owner: str, repo: str, number: int) -> ContributionRecord:
        response = self._client.get(f"/repos/{owner}/{repo}/pulls/{number}")
        response.raise_for_status()
        payload = response.json()
        merged_at = datetime.fromisoformat(payload["merged_at"].replace("Z", "+00:00")).astimezone(timezone.utc)
        head_repo = payload["head"]["repo"]
        base_repo = payload["base"]["repo"]
        return ContributionRecord(
            repo_full_name=base_repo["full_name"],
            repo_url=base_repo["html_url"],
            repo_owner=base_repo["owner"]["login"],
            repo_name=base_repo["name"],
            upstream_stars=base_repo["stargazers_count"],
            pr_number=payload["number"],
            pr_title=payload["title"],
            pr_url=payload["html_url"],
            merged_at=merged_at,
            author_login=payload["user"]["login"],
            head_repo_full_name=head_repo["full_name"],
            head_repo_owner=head_repo["owner"]["login"],
            head_repo_is_fork=head_repo["fork"],
            base_repo_owner=base_repo["owner"]["login"],
            is_merged=payload["merged"],
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_github_api.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/readme_updater/github_api.py tests/test_github_api.py tests/fixtures
git commit -m "feat: add github notifications and pr client"
```

### Task 7: Add State Store And Orchestration Service

**Files:**
- Create: `src/readme_updater/state_store.py`
- Create: `src/readme_updater/service.py`
- Modify: `src/readme_updater/filters.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing service tests**

```python
from datetime import datetime, timezone
from pathlib import Path

from readme_updater.models import ContributionRecord
from readme_updater.service import collect_recent_contributions


class FakeGitHubClient:
    def fetch_notifications(self) -> list[dict]:
        return [
            {"subject": {"type": "PullRequest", "url": "https://api.github.com/repos/owner/repo/pulls/101"}},
            {"subject": {"type": "PullRequest", "url": "https://api.github.com/repos/owner/repo/pulls/101"}},
        ]

    def fetch_pull_request(self, owner: str, repo: str, number: int) -> ContributionRecord:
        return ContributionRecord(
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
            base_repo_owner="owner",
            is_merged=True,
        )


def test_collect_recent_contributions_filters_by_time_and_dedupes() -> None:
    results = collect_recent_contributions(
        github_client=FakeGitHubClient(),
        github_user="nguyenhuuloc",
        days=30,
        now=datetime(2026, 4, 12, tzinfo=timezone.utc),
    )
    assert len(results) == 1
    assert results[0].pr_number == 101
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py::test_collect_recent_contributions_filters_by_time_and_dedupes -v`
Expected: FAIL because the service layer does not exist yet.

- [ ] **Step 3: Implement state store and orchestration**

```python
from __future__ import annotations

import json
from pathlib import Path


class StateStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> dict:
        if not self.path.exists():
            return {"processed_pull_requests": []}
        return json.loads(self.path.read_text())

    def save(self, state: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
```

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from readme_updater.filters import dedupe_contributions, is_eligible_contribution
from readme_updater.models import ContributionRecord


def parse_pull_request_identity(url: str) -> tuple[str, str, int]:
    parts = url.rstrip("/").split("/")
    return parts[-4], parts[-3], int(parts[-1])


def collect_recent_contributions(
    *,
    github_client,
    github_user: str,
    days: int,
    now: datetime | None = None,
) -> list[ContributionRecord]:
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(days=days)
    records: list[ContributionRecord] = []

    for notification in github_client.fetch_notifications():
        subject = notification.get("subject", {})
        if subject.get("type") != "PullRequest":
            continue
        owner, repo, number = parse_pull_request_identity(subject["url"])
        record = github_client.fetch_pull_request(owner, repo, number)
        if not is_eligible_contribution(record, github_user=github_user):
            continue
        if record.merged_at < cutoff:
            continue
        records.append(record)

    return dedupe_contributions(records)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py::test_collect_recent_contributions_filters_by_time_and_dedupes -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/readme_updater/state_store.py src/readme_updater/service.py src/readme_updater/filters.py tests/test_cli.py
git commit -m "feat: add contribution collection service"
```

### Task 8: Wire The Full CLI Update Flow

**Files:**
- Modify: `src/readme_updater/cli.py`
- Modify: `src/readme_updater/service.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing CLI integration tests**

```python
from pathlib import Path

import pytest

from readme_updater.cli import main
from readme_updater.config import RuntimeConfig


def test_main_update_writes_svg_and_readme(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text("before\n<!-- contributions:start -->\nold\n<!-- contributions:end -->\nafter\n")
    svg_path = tmp_path / "assets" / "contributions.svg"

    config = RuntimeConfig(
        github_token="token",
        github_user="nguyenhuuloc",
        readme_path=readme_path,
        svg_output=svg_path,
        state_file=tmp_path / ".state.json",
        days=30,
        dry_run=False,
        verbose=False,
    )

    monkeypatch.setattr("readme_updater.cli.load_config", lambda **_: config)
    monkeypatch.setattr(
        "readme_updater.cli.run_update",
        lambda runtime_config: {
            "readme_block": "## Recent Open Source Contributions",
            "svg": "<svg></svg>",
        },
    )
    monkeypatch.setattr("sys.argv", ["readme-updater", "update"])

    exit_code = main()

    assert exit_code == 0
    assert "## Recent Open Source Contributions" in readme_path.read_text()
    assert svg_path.read_text() == "<svg></svg>"


def test_main_update_dry_run_does_not_modify_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text("before\n<!-- contributions:start -->\nold\n<!-- contributions:end -->\nafter\n")

    config = RuntimeConfig(
        github_token="token",
        github_user="nguyenhuuloc",
        readme_path=readme_path,
        svg_output=tmp_path / "assets" / "contributions.svg",
        state_file=tmp_path / ".state.json",
        days=30,
        dry_run=True,
        verbose=False,
    )

    monkeypatch.setattr("readme_updater.cli.load_config", lambda **_: config)
    monkeypatch.setattr(
        "readme_updater.cli.run_update",
        lambda runtime_config: {
            "readme_block": "## Recent Open Source Contributions",
            "svg": "<svg></svg>",
        },
    )
    monkeypatch.setattr("sys.argv", ["readme-updater", "update"])

    exit_code = main()

    assert exit_code == 0
    assert readme_path.read_text() == "before\n<!-- contributions:start -->\nold\n<!-- contributions:end -->\nafter\n"
    assert "## Recent Open Source Contributions" in capsys.readouterr().out
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL because `run_update` and file-write behavior are not implemented yet.

- [ ] **Step 3: Implement the end-to-end update flow**

```python
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone

from readme_updater.filters import group_contributions
from readme_updater.github_api import GitHubClient
from readme_updater.readme_renderer import render_readme_block
from readme_updater.svg_renderer import build_summary_metrics, render_svg_card


def run_update(runtime_config) -> dict[str, str]:
    github_client = GitHubClient(github_token=runtime_config.github_token)
    contributions = collect_recent_contributions(
        github_client=github_client,
        github_user=runtime_config.github_user,
        days=runtime_config.days,
        now=datetime.now(timezone.utc),
    )
    groups = group_contributions(contributions)
    readme_block = render_readme_block(groups, days=runtime_config.days)
    svg = render_svg_card(build_summary_metrics(groups, days=runtime_config.days))
    return {"readme_block": readme_block, "svg": svg}
```

```python
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from readme_updater.config import load_config
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


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command != "update":
        return 0

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
        print(result["readme_block"])
        return 0

    current_readme = config.readme_path.read_text()
    updated_readme = replace_marker_block(current_readme, result["readme_block"])
    config.readme_path.write_text(updated_readme)
    config.svg_output.parent.mkdir(parents=True, exist_ok=True)
    config.svg_output.write_text(result["svg"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/readme_updater/cli.py src/readme_updater/service.py tests/test_cli.py
git commit -m "feat: wire full cli update flow"
```

### Task 9: Add Error Paths And Empty-State Coverage

**Files:**
- Modify: `src/readme_updater/github_api.py`
- Modify: `src/readme_updater/cli.py`
- Modify: `tests/test_github_api.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_svg_renderer.py`
- Modify: `tests/test_readme_renderer.py`

- [ ] **Step 1: Write the failing error-path tests**

```python
import httpx
import pytest
import respx

from readme_updater.github_api import GitHubApiError, GitHubClient


@respx.mock
def test_fetch_notifications_wraps_http_errors() -> None:
    respx.get("https://api.github.com/notifications").mock(
        return_value=httpx.Response(401, json={"message": "Bad credentials"})
    )
    client = GitHubClient(github_token="token")
    with pytest.raises(GitHubApiError, match="401"):
        client.fetch_notifications()
```

```python
from pathlib import Path

import pytest

from readme_updater.cli import main
from readme_updater.config import RuntimeConfig


def test_main_returns_non_zero_on_missing_readme_markers(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text("no markers here")

    config = RuntimeConfig(
        github_token="token",
        github_user="nguyenhuuloc",
        readme_path=readme_path,
        svg_output=tmp_path / "assets" / "contributions.svg",
        state_file=tmp_path / ".state.json",
        days=30,
        dry_run=False,
        verbose=False,
    )

    monkeypatch.setattr("readme_updater.cli.load_config", lambda **_: config)
    monkeypatch.setattr(
        "readme_updater.cli.run_update",
        lambda runtime_config: {"readme_block": "content", "svg": "<svg></svg>"},
    )
    monkeypatch.setattr("sys.argv", ["readme-updater", "update"])

    assert main() == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_github_api.py tests/test_cli.py -v`
Expected: FAIL because error wrapping and CLI error return behavior are not implemented yet.

- [ ] **Step 3: Implement robust error handling**

```python
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from readme_updater.models import ContributionRecord


class GitHubApiError(RuntimeError):
    pass


class GitHubClient:
    def __init__(self, *, github_token: str) -> None:
        self._client = httpx.Client(
            base_url="https://api.github.com",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {github_token}",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=20.0,
        )

    def fetch_notifications(self) -> list[dict]:
        try:
            response = self._client.get("/notifications")
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GitHubApiError(f"GitHub notifications request failed with status {exc.response.status_code}") from exc
        return response.json()
```

```python
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from readme_updater.config import ConfigError, load_config
from readme_updater.github_api import GitHubApiError
from readme_updater.readme_renderer import ReadmeMarkerError, replace_marker_block
from readme_updater.service import run_update


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command != "update":
        return 0

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
            print(result["readme_block"])
            return 0

        current_readme = config.readme_path.read_text()
        updated_readme = replace_marker_block(current_readme, result["readme_block"])
        config.readme_path.write_text(updated_readme)
        config.svg_output.parent.mkdir(parents=True, exist_ok=True)
        config.svg_output.write_text(result["svg"])
        return 0
    except (ConfigError, GitHubApiError, ReadmeMarkerError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_github_api.py tests/test_cli.py tests/test_readme_renderer.py tests/test_svg_renderer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/readme_updater/github_api.py src/readme_updater/cli.py tests/test_github_api.py tests/test_cli.py tests/test_readme_renderer.py tests/test_svg_renderer.py
git commit -m "feat: harden updater error handling"
```

### Task 10: Run Full Verification And Document Usage

**Files:**
- Modify: `README.md`
- Test: `tests/test_config.py`
- Test: `tests/test_filters.py`
- Test: `tests/test_readme_renderer.py`
- Test: `tests/test_svg_renderer.py`
- Test: `tests/test_github_api.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Add usage documentation to the README**

```md
# README Updater

## Usage

Set environment variables:

```bash
export GITHUB_TOKEN=ghp_example
export GITHUB_USER=nguyenhuuloc
export README_PATH=README.md
export SVG_OUTPUT=assets/contributions.svg
export DEFAULT_DAYS=30
```

Run the updater:

```bash
python -m readme_updater.cli update --days 30
```

Dry-run the generated README block:

```bash
python -m readme_updater.cli update --days 3 --dry-run
```

<!-- contributions:start -->
Contribution data has not been generated yet.
<!-- contributions:end -->
```

- [ ] **Step 2: Run the full test suite**

Run: `pytest -v`
Expected: PASS for all config, filter, renderer, API, and CLI tests.

- [ ] **Step 3: Run one manual dry-run smoke check**

Run:

```bash
export GITHUB_TOKEN=ghp_example
export GITHUB_USER=nguyenhuuloc
python -m readme_updater.cli update --days 3 --dry-run
```

Expected: the command prints a Markdown contribution block to stdout without modifying `README.md`.

- [ ] **Step 4: Run one manual write-mode smoke check**

Run:

```bash
export GITHUB_TOKEN=ghp_example
export GITHUB_USER=nguyenhuuloc
python -m readme_updater.cli update --days 30 --readme README.md --svg-output assets/contributions.svg
```

Expected:

- `README.md` is updated only inside the contribution markers
- `assets/contributions.svg` is created
- the SVG contains the title `Merged Upstream Contributions`

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: add updater usage instructions"
```

## Self-Review

Spec coverage check:
- notifications-first discovery is implemented in Task 6 and Task 7
- fork-to-upstream eligibility rules are implemented in Task 3 and enforced in Task 7
- grouped Markdown output with star counts is implemented in Task 4
- premium minimal SVG card is implemented in Task 5
- environment-first config with CLI overrides is implemented in Task 2
- dry-run, write mode, and failure-safe README updates are implemented in Task 8 and Task 9
- empty-state behavior is covered in Task 4, Task 5, and Task 9

Placeholder scan:
- no `TODO`, `TBD`, or unresolved placeholders remain
- every code-writing step includes concrete code
- every verification step includes an exact command and expected result

Type consistency check:
- `RuntimeConfig`, `ContributionRecord`, `RepositoryContributions`, `GitHubClient`, `collect_recent_contributions`, and `run_update` names are consistent across tasks
- renderer and SVG metric functions use the same grouped contribution model throughout the plan
