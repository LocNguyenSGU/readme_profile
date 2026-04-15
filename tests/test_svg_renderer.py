from datetime import datetime, timezone

from readme_updater.models import ContributionRecord, RepositoryContributions
from readme_updater.svg_renderer import build_summary_metrics
from readme_updater.svg_renderer import render_repo_svg_cards
from readme_updater.svg_renderer import render_svg_card


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


def test_build_summary_metrics_counts_groups_prs_and_top_repo() -> None:
    metrics = build_summary_metrics(make_groups(), days=30)
    assert metrics.total_merged_prs == 1
    assert metrics.total_repos == 1
    assert metrics.top_repo_name == "HKUDS/DeepTutor"
    assert metrics.top_repo_stars_label == "17.0k"
    assert metrics.window_label == "Last 30 days"


def test_render_svg_card_uses_premium_technical_prestige_copy() -> None:
    svg = render_svg_card(build_summary_metrics(make_groups(), days=30))
    assert "Merged Upstream Contributions" in svg
    assert "merged PRs" in svg
    assert "Top target" in svg
    assert "1 upstream repo" in svg
    assert "17.0k stars" in svg
    assert "Last 30 days" in svg
    assert "Repository Of The Day" not in svg


def test_render_svg_card_uses_editorial_typography_and_layered_surface() -> None:
    svg = render_svg_card(build_summary_metrics(make_groups(), days=30))
    assert 'rx="18"' in svg
    assert "fill-opacity" in svg
    assert 'id="decorative-emblem"' in svg
    assert "Arial, sans-serif" in svg


def test_render_svg_card_empty_state_keeps_same_visual_shell() -> None:
    svg = render_svg_card(build_summary_metrics([], days=3))
    assert "No merged upstream PRs" in svg
    assert "Last 3 days" in svg
    assert "<svg" in svg


def test_render_repo_svg_cards_returns_one_card_per_repo_with_distinct_colors() -> None:
    deep_tutor = make_groups()[0]
    second_repo = RepositoryContributions(
        repo_full_name="chatgptprojects/clear-code",
        repo_url="https://github.com/chatgptprojects/clear-code",
        upstream_stars=2000,
        contributions=deep_tutor.contributions,
    )

    cards = render_repo_svg_cards([deep_tutor, second_repo], days=30)

    assert len(cards) == 2
    assert cards[0]["repo_full_name"] == "HKUDS/DeepTutor"
    assert cards[1]["repo_full_name"] == "chatgptprojects/clear-code"
    assert cards[0]["color"] != cards[1]["color"]
    assert "HKUDS/DeepTutor" in cards[0]["svg"]
    assert "chatgptprojects/clear-code" in cards[1]["svg"]
    assert "Latest merge: 2026-04-08" in cards[0]["svg"]
    assert "merged PR" in cards[0]["svg"]
    assert "Repository Of The Day" not in cards[0]["svg"]
