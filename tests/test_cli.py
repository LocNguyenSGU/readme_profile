from datetime import datetime, timezone
from pathlib import Path

import pytest

from readme_updater.cli import build_parser
from readme_updater.cli import main
from readme_updater.config import RuntimeConfig
from readme_updater.models import ContributionRecord
from readme_updater.service import collect_recent_contributions
from readme_updater.service import describe_ineligibility


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


def test_main_update_writes_svg_and_readme(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "before\n<!-- contributions:start -->\nold\n<!-- contributions:end -->\nafter\n"
    )
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
            "svg": "<svg>fallback</svg>",
            "summary_svg": "<svg>summary</svg>",
            "svg_cards": [
                {
                    "repo_full_name": "owner/repo",
                    "svg": "<svg>repo-card</svg>",
                }
            ],
        },
    )
    monkeypatch.setattr("sys.argv", ["readme-updater", "update"])

    exit_code = main()

    assert exit_code == 0
    assert "## Recent Open Source Contributions" in readme_path.read_text()
    assert svg_path.read_text() == "<svg>summary</svg>"


def test_main_update_appends_block_when_readme_has_no_markers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text("# Profile\n")
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
            "readme_block": (
                "## Recent Open Source Contributions\n\n"
                "<table>\n"
                "  <tr>\n"
                "    <th>Repository</th>\n"
                "    <th>Merged PRs</th>\n"
                "    <th>Latest Merge</th>\n"
                "    <th>Contribution Card</th>\n"
                "  </tr>\n"
                "  <tr>\n"
                '    <td><a href="https://github.com/owner/repo">owner/repo</a></td>\n'
                "    <td>2</td>\n"
                "    <td>2026-04-11</td>\n"
                '    <td align="center"><img src="./assets/contributions-owner-repo.svg" alt="owner/repo contribution card" width="420" /></td>\n'
                "  </tr>\n"
                "</table>"
            ),
            "svg": "<svg>fallback</svg>",
            "summary_svg": "<svg>summary</svg>",
            "svg_cards": [
                {
                    "repo_full_name": "owner/repo",
                    "svg": "<svg>repo-card</svg>",
                }
            ],
        },
    )
    monkeypatch.setattr("sys.argv", ["readme-updater", "update"])

    exit_code = main()

    assert exit_code == 0
    assert "<!-- contributions:start -->" in readme_path.read_text()
    assert readme_path.read_text().count("owner/repo") == 3


def test_main_update_writes_one_svg_per_repo_when_multiple_groups(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "before\n<!-- contributions:start -->\nold\n<!-- contributions:end -->\nafter\n"
    )
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
            "svg": "<svg>fallback</svg>",
            "summary_svg": "<svg>summary</svg>",
            "svg_cards": [
                {
                    "repo_full_name": "HKUDS/DeepTutor",
                    "svg": "<svg>card1</svg>",
                },
                {
                    "repo_full_name": "chatgptprojects/clear-code",
                    "svg": "<svg>card2</svg>",
                },
            ],
        },
    )
    monkeypatch.setattr("sys.argv", ["readme-updater", "update"])

    exit_code = main()

    assert exit_code == 0
    assert svg_path.read_text() == "<svg>summary</svg>"
    assert (tmp_path / "assets" / "contributions-hkuds-deeptutor.svg").read_text() == "<svg>card1</svg>"
    assert (tmp_path / "assets" / "contributions-chatgptprojects-clear-code.svg").read_text() == "<svg>card2</svg>"


def test_main_update_dry_run_does_not_modify_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    readme_path = tmp_path / "README.md"
    readme_path.write_text(
        "before\n<!-- contributions:start -->\nold\n<!-- contributions:end -->\nafter\n"
    )

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
    assert (
        readme_path.read_text()
        == "before\n<!-- contributions:start -->\nold\n<!-- contributions:end -->\nafter\n"
    )
    assert "## Recent Open Source Contributions" in capsys.readouterr().out


def test_main_update_returns_error_for_missing_credentials(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_USER", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        [
            "readme-updater",
            "update",
            "--days",
            "30",
            "--readme",
            "README.md",
            "--svg-output",
            "assets/contributions.svg",
        ],
    )

    exit_code = main()

    assert exit_code == 1
    assert (
        capsys.readouterr().err
        == "Missing required environment variable: GITHUB_TOKEN\n"
    )


class FakeGitHubClient:
    def fetch_notifications(self, *, since: str | None = None) -> list[dict]:
        return [
            {
                "subject": {
                    "type": "PullRequest",
                    "url": "https://api.github.com/repos/owner/repo/pulls/101",
                }
            },
            {
                "subject": {
                    "type": "PullRequest",
                    "url": "https://api.github.com/repos/owner/repo/pulls/101",
                }
            },
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
            head_repo_exists=True,
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


def test_collect_recent_contributions_logs_verbose_skip_reasons() -> None:
    messages: list[str] = []

    class VerboseFakeGitHubClient:
        def fetch_notifications(self, *, since: str | None = None) -> list[dict]:
            return [
                {
                    "subject": {
                        "type": "PullRequest",
                        "url": "https://api.github.com/repos/owner/repo/pulls/101",
                    }
                }
            ]

        def fetch_pull_request(
            self, owner: str, repo: str, number: int
        ) -> ContributionRecord:
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
                head_repo_is_fork=False,
                head_repo_exists=True,
                base_repo_owner="owner",
                is_merged=True,
            )

    results = collect_recent_contributions(
        github_client=VerboseFakeGitHubClient(),
        github_user="nguyenhuuloc",
        days=30,
        now=datetime(2026, 4, 12, tzinfo=timezone.utc),
        logger=messages.append,
    )

    assert results == []
    assert "Fetched 1 notifications" in messages[0]
    assert any("head_repo_is_not_fork" in message for message in messages)


def test_describe_ineligibility_returns_expected_reason() -> None:
    reason = describe_ineligibility(
        ContributionRecord(
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
            head_repo_is_fork=False,
            head_repo_exists=True,
            base_repo_owner="owner",
            is_merged=True,
        ),
        github_user="nguyenhuuloc",
    )

    assert reason == "head_repo_is_not_fork"


def test_main_appends_when_readme_markers_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
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

    assert main() == 0
    assert "<!-- contributions:start -->" in readme_path.read_text()
    assert "content" in readme_path.read_text()
