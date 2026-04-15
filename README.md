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
## Recent Open Source Contributions

<img src="./assets/contributions.svg" alt="Recent open source contributions" width="100%" />
<!-- contributions:end -->
