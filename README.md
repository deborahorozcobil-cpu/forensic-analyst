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

### Step 1 — Get the code on your machine

Two ways. Either works.

**Option A — Clone with git** (recommended if you'll be updating it later):

```bash
cd ~/Projects 2>/dev/null || mkdir -p ~/Projects && cd ~/Projects
git clone https://github.com/deborahorozcobil-cpu/forensic-analyst.git
cd forensic-analyst
```

**Option B — Download as a zip** (if you don't have git or just want it once):

1. On the GitHub page, click the green **`<> Code`** button → **Download ZIP**
2. Move the downloaded zip to `~/Projects/` (or wherever you like) and unzip it
3. In Terminal:
   ```bash
   cd ~/Projects/forensic-analyst-main
   # (the folder name will end in -main when downloaded as a zip)
   ```

### Step 2 — Run the installer

From inside the folder:

```bash
bash install.sh
```

The installer will:

- Create a Python virtual environment in `.venv/`
- Install dependencies (anthropic, requests, beautifulsoup4, lxml, markdown)
- Ask you to paste your Anthropic API key — get one at [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys). You'll need at least $5 of credit on your account.
- Save the key to `~/.anthropic-key` with strict permissions (only readable by you)
- Copy the `Forensic Analyst.command` launcher to your Desktop
- Add a `forensic` shell alias to your `~/.zshrc`

**When the installer asks for your API key**: copy it from the Anthropic console with the copy button (📋), come back to Terminal, press **Cmd-V** (input is hidden on purpose — you won't see anything), then press **Enter**.

### Step 3 — Open a new Terminal window

The `forensic` alias only loads in new Terminal sessions. Close the current Terminal window and open a fresh one. Now you can use the tool.

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
