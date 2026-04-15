# SVG Contribution Card Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the generated SVG contribution summary card so it looks more premium and technically prestigious while preserving the same contribution data and GitHub README compatibility.

**Architecture:** Keep the change isolated to the SVG renderer by refining the summary-card layout, typography, and SVG surface treatment inside `svg_renderer.py`. Preserve the existing data flow and metric computation contract, updating tests only where wording or expected SVG content needs to change.

**Tech Stack:** Python 3.12+, `pytest`, standard library `dataclasses`, `html`

---

## Planned File Structure

**Files:**
- Modify: `src/readme_updater/svg_renderer.py`
- Modify: `tests/test_svg_renderer.py`

This redesign does not require changes to filtering, README Markdown rendering, config loading, or CLI orchestration.

### Task 1: Redesign The SVG Card Surface And Hierarchy

**Files:**
- Modify: `src/readme_updater/svg_renderer.py`
- Test: `tests/test_svg_renderer.py`

- [ ] **Step 1: Write the failing visual-contract tests**

```python
from datetime import datetime, timezone

from readme_updater.models import ContributionRecord, RepositoryContributions
from readme_updater.svg_renderer import build_summary_metrics, render_svg_card


def make_groups() -> list[RepositoryContributions]:
    contribution = ContributionRecord(
        repo_full_name="HKUDS/DeepTutor",
        repo_url="https://github.com/HKUDS/DeepTutor",
        repo_owner="HKUDS",
        repo_name="DeepTutor",
        upstream_stars=17000,
        pr_number=262,
        pr_title="docs: clarify github copilot provider login semantics",
        pr_url="https://github.com/HKUDS/DeepTutor/pull/262",
        merged_at=datetime(2026, 4, 8, tzinfo=timezone.utc),
        author_login="LocNguyenSGU",
        head_repo_full_name="LocNguyenSGU/DeepTutor",
        head_repo_owner="LocNguyenSGU",
        head_repo_is_fork=True,
        head_repo_exists=True,
        base_repo_owner="HKUDS",
        is_merged=True,
    )
    return [
        RepositoryContributions(
            repo_full_name="HKUDS/DeepTutor",
            repo_url="https://github.com/HKUDS/DeepTutor",
            upstream_stars=17000,
            contributions=[contribution],
        )
    ]


def test_render_svg_card_uses_premium_technical_prestige_copy() -> None:
    svg = render_svg_card(build_summary_metrics(make_groups(), days=30))
    assert "Merged Upstream Contributions" in svg
    assert "Top target" in svg
    assert "1 upstream repo" in svg
    assert "17.0k stars" in svg
    assert "Last 30 days" in svg


def test_render_svg_card_uses_editorial_typography_and_layered_surface() -> None:
    svg = render_svg_card(build_summary_metrics(make_groups(), days=30))
    assert "Georgia" in svg
    assert 'rx="28"' in svg
    assert "#0F172A" in svg
    assert "#E2E8F0" in svg


def test_render_svg_card_empty_state_keeps_same_visual_shell() -> None:
    svg = render_svg_card(build_summary_metrics([], days=3))
    assert "No merged upstream PRs" in svg
    assert "Last 3 days" in svg
    assert "<svg" in svg
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_svg_renderer.py -v`
Expected: FAIL because the current SVG text, colors, and typography do not match the redesigned visual contract.

- [ ] **Step 3: Implement the SVG redesign in one focused pass**

```python
from __future__ import annotations

from dataclasses import dataclass
from html import escape

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

    if top_group is None:
        top_repo_name = "No merged upstream PRs"
        top_repo_stars_label = "0"
    else:
        top_repo_name = top_group.repo_full_name
        top_repo_stars_label = format_stars(top_group.upstream_stars)

    return SummaryMetrics(
        total_merged_prs=total_merged_prs,
        total_repos=total_repos,
        top_repo_name=top_repo_name,
        top_repo_stars_label=top_repo_stars_label,
        window_label=f"Last {days} days",
    )


def render_svg_card(metrics: SummaryMetrics) -> str:
    title = escape("Merged Upstream Contributions")
    primary_value = escape(str(metrics.total_merged_prs))
    repo_count_label = escape(
        f"{metrics.total_repos} upstream repo{'s' if metrics.total_repos != 1 else ''}"
    )
    top_target_label = escape(f"Top target: {metrics.top_repo_name}")
    stars_label = escape(f"{metrics.top_repo_stars_label} stars")
    window_label = escape(metrics.window_label)

    return f"""<svg width="720" height="260" viewBox="0 0 720 260" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title} summary card">
  <rect width="720" height="260" rx="28" fill="#0F172A"/>
  <rect x="20" y="20" width="680" height="220" rx="24" fill="#111827"/>
  <rect x="20.5" y="20.5" width="679" height="219" rx="23.5" stroke="#334155"/>
  <text x="44" y="56" fill="#94A3B8" font-family="Georgia, 'Times New Roman', serif" font-size="15" letter-spacing="0.14em">{title.upper()}</text>
  <text x="44" y="134" fill="#F8FAFC" font-family="Georgia, 'Times New Roman', serif" font-size="72">{primary_value}</text>
  <text x="46" y="166" fill="#CBD5E1" font-family="Georgia, 'Times New Roman', serif" font-size="18">merged PRs</text>
  <text x="300" y="96" fill="#E2E8F0" font-family="Georgia, 'Times New Roman', serif" font-size="20">{repo_count_label}</text>
  <text x="300" y="132" fill="#E2E8F0" font-family="Georgia, 'Times New Roman', serif" font-size="20">{top_target_label}</text>
  <text x="300" y="168" fill="#94A3B8" font-family="Georgia, 'Times New Roman', serif" font-size="18">{stars_label}</text>
  <text x="44" y="214" fill="#64748B" font-family="Georgia, 'Times New Roman', serif" font-size="16">{window_label}</text>
</svg>
"""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_svg_renderer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/readme_updater/svg_renderer.py tests/test_svg_renderer.py
git commit -m "feat: redesign contribution svg card"
```

### Task 2: Verify The Redesigned Card With Real README Data

**Files:**
- Modify: `src/readme_updater/svg_renderer.py` only if final wording/spacing polish is needed after verification
- Test: `tests/test_svg_renderer.py`

- [ ] **Step 1: Run a real dry-run to inspect current README-facing data**

Run: `PYTHONPATH=src python3 -m readme_updater.cli update --days 30 --dry-run --verbose`
Expected: The command prints verbose contribution filtering details and a Markdown block showing the currently eligible repositories.

- [ ] **Step 2: Run a real write-mode update to regenerate the SVG asset**

Run: `PYTHONPATH=src python3 -m readme_updater.cli update --days 30 --readme README.md --svg-output assets/contributions.svg`
Expected:
- `README.md` block is refreshed
- `assets/contributions.svg` is regenerated with the new premium visual treatment

- [ ] **Step 3: Inspect the generated SVG text surface**

Run: `sed -n '1,220p' assets/contributions.svg`
Expected:
- title reads `Merged Upstream Contributions`
- card includes `Top target:`
- card includes the repo count line
- footer includes the time window

- [ ] **Step 4: If wording polish is needed, make one final minimal renderer adjustment and rerun SVG tests**

```python
# Example of the only acceptable type of follow-up change here:
# adjust exact label text or coordinates while preserving the tested hierarchy.
```

Run: `pytest tests/test_svg_renderer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/readme_updater/svg_renderer.py tests/test_svg_renderer.py README.md assets/contributions.svg
git commit -m "chore: regenerate redesigned contribution card"
```

## Self-Review

Spec coverage check:
- technical prestige visual mood is implemented in Task 1 through palette, typography, and layout changes
- balanced emphasis between merged PR count and repo prestige is preserved in the final card hierarchy
- Markdown renderer and contribution filtering are intentionally untouched
- GitHub compatibility is preserved by staying within static inline SVG constraints
- real-data verification is covered in Task 2

Placeholder scan:
- no `TODO`, `TBD`, or unresolved placeholders remain
- every implementation step includes exact files, commands, or concrete code

Type consistency check:
- `SummaryMetrics`, `build_summary_metrics`, and `render_svg_card` remain the only SVG renderer contracts
- wording asserted in tests matches wording described in the implementation steps
