from __future__ import annotations

from datetime import datetime, timedelta, timezone
import sys
from typing import Callable

from readme_updater.filters import dedupe_contributions, is_eligible_contribution
from readme_updater.filters import group_contributions
from readme_updater.github_api import GitHubClient
from readme_updater.models import ContributionRecord
from readme_updater.readme_renderer import render_readme_block
from readme_updater.svg_renderer import build_summary_metrics, render_svg_card
from readme_updater.svg_renderer import render_repo_svg_cards


def parse_pull_request_identity(url: str) -> tuple[str, str, int]:
    parts = url.rstrip("/").split("/")
    return parts[-4], parts[-3], int(parts[-1])


def describe_ineligibility(record: ContributionRecord, *, github_user: str) -> str:
    if not record.is_merged:
        return "not_merged"
    if not record.head_repo_exists:
        return "head_repo_missing"
    if not record.head_repo_is_fork:
        return "head_repo_is_not_fork"
    if record.head_repo_owner != github_user:
        return "head_repo_owner_mismatch"
    if record.base_repo_owner == github_user:
        return "base_repo_owned_by_user"
    return "unknown"


def collect_recent_contributions(
    *,
    github_client: object,
    github_user: str,
    days: int,
    now: datetime | None = None,
    logger: Callable[[str], None] | None = None,
) -> list[ContributionRecord]:
    current_time = now or datetime.now(timezone.utc)
    cutoff = current_time - timedelta(days=days)
    notifications = github_client.fetch_notifications(
        since=cutoff.replace(microsecond=0).isoformat().replace("+00:00", "Z")
    )
    if logger is not None:
        logger(f"Fetched {len(notifications)} notifications")
    records: list[ContributionRecord] = []
    candidate_count = 0

    for notification in notifications:
        subject = notification.get("subject", {})
        if subject.get("type") != "PullRequest":
            continue
        candidate_count += 1
        owner, repo, number = parse_pull_request_identity(subject["url"])
        record = github_client.fetch_pull_request(owner, repo, number)
        if not is_eligible_contribution(record, github_user=github_user):
            if logger is not None:
                logger(
                    f"Skipped {record.repo_full_name}#{record.pr_number}: "
                    f"{describe_ineligibility(record, github_user=github_user)}"
                )
            continue
        if record.merged_at is None or record.merged_at < cutoff:
            if logger is not None:
                logger(
                    f"Skipped {record.repo_full_name}#{record.pr_number}: outside_time_window"
                )
            continue
        records.append(record)

    unique_records = dedupe_contributions(records)
    if logger is not None:
        logger(f"Pull request candidates: {candidate_count}")
        logger(f"Eligible recent contributions: {len(unique_records)}")
    return unique_records


def run_update(runtime_config: object) -> dict[str, object]:
    github_client = GitHubClient(github_token=runtime_config.github_token)
    logger = (
        lambda message: print(message, file=sys.stderr)
        if getattr(runtime_config, "verbose", False)
        else None
    )
    contributions = collect_recent_contributions(
        github_client=github_client,
        github_user=runtime_config.github_user,
        days=runtime_config.days,
        now=datetime.now(timezone.utc),
        logger=logger,
    )
    groups = group_contributions(contributions)
    readme_block = render_readme_block(groups, days=runtime_config.days)
    summary_svg = render_svg_card(build_summary_metrics(groups, days=runtime_config.days))
    repo_svg_cards = render_repo_svg_cards(groups, days=runtime_config.days)
    return {
        "groups": groups,
        "readme_block": readme_block,
        "svg": repo_svg_cards[0]["svg"],
        "summary_svg": summary_svg,
        "svg_cards": repo_svg_cards,
    }
