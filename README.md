# Forensic Analyst

A command-line tool that reads SEC 10-K and 10-Q filings and surfaces accounting red flags that have empirically preceded large stock declines. It uses the Anthropic API (Claude) under the hood.

The agent organizes findings into three tiers:

- **Tier 1 — Catastrophic.** Patterns that have preceded 30%+ drawdowns, frauds, or bankruptcies (NI vs. CFO divergence, revenue recognition irregularities, auditor changes, restatements, going-concern language).
- **Tier 2 — Multiple compression.** Quality-of-earnings issues that have preceded 10–25% declines (SBC outpacing revenue, working capital deterioration, off-balance-sheet liabilities, goodwill impairment risk).
- **Tier 3 — Context.** Disclosures worth knowing but not actionable alone (policy changes, segment changes, CAMs, insider patterns, litigation).

Each flag cites the specific line item or footnote, gives year-over-year numbers, and explains the historical precedent. Final verdict is GREEN / YELLOW / ORANGE / RED.

## Requirements

- macOS (the Desktop launcher is macOS-only; the Python script works anywhere)
- Python 3.10 or newer
- An Anthropic API key with credit (https://console.anthropic.com/settings/keys — $5 is enough to get started)

## Install

1. Unzip this folder somewhere stable. Recommended: `~/Projects/forensic-analyst/`.

2. Open Terminal and `cd` into the folder. For example:

   ```bash
   cd ~/Projects/forensic-analyst
   ```

3. Run the installer:

   ```bash
   bash install.sh
   ```

   It will:
   - Create a Python virtual environment in `.venv/`
   - Install dependencies (anthropic, requests, beautifulsoup4, lxml, markdown)
   - Ask you to paste your API key (input is hidden — won't show on screen)
   - Save the key to `~/.anthropic-key` with `chmod 600` (only readable by you)
   - Copy `Forensic Analyst.command` to your Desktop
   - Add a `forensic` shell alias to your `~/.zshrc`

   **Important:** when it asks for the key, copy it from console.anthropic.com using the copy button (📋), then in Terminal press Cmd-V (you won't see anything — that's intentional) and press Enter.

4. Open a **new** Terminal window so the alias loads.

## Usage

Three equivalent ways to run an analysis:

### 1. Double-click the Desktop icon (no Terminal needed)

Double-click **Forensic Analyst.command** on your Desktop. It asks for a ticker and an analysis type, then opens the report in your browser.

### 2. The `forensic` shell command

From any Terminal window:

```bash
forensic AAPL                 # latest 10-K
forensic AAPL --compare       # latest 10-K + YoY delta vs prior year
forensic AAPL --form 10-Q     # latest quarterly report
```

### 3. Direct Python invocation

```bash
cd ~/Projects/forensic-analyst
.venv/bin/python forensic_analyst.py AAPL
```

## Where reports are saved

All reports go to `~/Documents/forensic-reports/` as both Markdown (`.md`) and HTML (`.html`). The HTML auto-opens in your default browser when each run finishes.

Files are named `{TICKER}_{FORM}_{PERIOD}_{TIMESTAMP}`, e.g. `AAPL_10-K_2025-09-27_2026-05-12_001435.html`.

## Cost

Each run uses Claude Opus 4.7 via the Anthropic API. Rough costs:

| Command | Typical cost | Time |
|---|---|---|
| `forensic TICKER` (10-K) | $0.30 – $0.80 | 60–90s |
| `forensic TICKER --compare` | $1.00 – $1.50 | 2–3 min |
| `forensic TICKER --form 10-Q` | $0.20 – $0.40 | 45–60s |

Large filings (banks, conglomerates) cost more. $5 of credit comfortably covers 10+ runs.

## Files in this folder

- `forensic_analyst.py` — the main script
- `install.sh` — one-shot installer (run this first)
- `setup-key.sh` — interactive API key setup (called by install.sh)
- `Forensic Analyst.command` — macOS double-click launcher (copied to Desktop by install.sh)
- `requirements.txt` — Python dependencies
- `README.md` — this file

## Troubleshooting

**"unable to verify the developer"** when double-clicking the .command file.
Right-click the file → **Open** → confirm in the dialog. macOS only asks once.

**"invalid x-api-key"**
Your `~/.anthropic-key` file has a wrong or partial key. Re-run `bash setup-key.sh` from the project folder to redo it.

**"Your credit balance is too low"**
Add credit at https://console.anthropic.com/settings/billing.

**`forensic` command not found**
Open a **new** Terminal window — the alias only loads in new sessions after install. If still not working, run `source ~/.zshrc`.

## Security note

`~/.anthropic-key` is a personal secret. Never commit it to git, paste it into chat windows, screenshots, or share it with anyone. Each user installs the tool with their own key.
