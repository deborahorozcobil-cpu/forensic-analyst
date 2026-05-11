"""Forensic financial statement analyst.

Usage:
    python forensic_analyst.py AAPL
    python forensic_analyst.py AAPL --compare
"""

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import anthropic
import markdown as md_lib
import requests
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

SEC_UA = "Forensic Analyst forensic-analyst@example.com"
SEC_HEADERS = {"User-Agent": SEC_UA, "Accept-Encoding": "gzip, deflate"}
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
ARCHIVE_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_clean}/{document}"

MODEL = "claude-opus-4-7"

DEFAULT_REPORT_DIR = Path.home() / "Documents" / "forensic-reports"

REPORT_PREAMBLE = """# Forensic Financial Statement Analysis

> **What this report flags.** This agent reads the SEC filing for the specific accounting patterns that have empirically preceded large stock declines, restatements, and frauds. Findings are organized into three tiers of severity.
>
> **Tier 1 — Catastrophic.** Patterns that have preceded 30%+ drawdowns, bankruptcies, or accounting frauds. Things like net income diverging from operating cash flow, revenue recognition irregularities, an auditor change, restatement of prior periods, going-concern language, or a material weakness in internal controls. *Any single Tier 1 flag is reason to step away from the long side.*
>
> **Tier 2 — Multiple compression.** Quality-of-earnings issues that have preceded 10–25% declines as the market re-rates the equity. Stock-based comp growing faster than revenue, receivables growing faster than sales (rising DSO), inventory bloating relative to COGS, off-balance-sheet liabilities, goodwill that hasn't been impaired despite weak performance, heavy customer concentration. *Worth watching; not necessarily actionable alone.*
>
> **Tier 3 — Context.** Disclosures worth knowing but not actionable by themselves: accounting policy changes, segment reorganizations, critical audit matters, insider transaction patterns, litigation contingencies, executive turnover at the CFO/controller level.
>
> **Verdict scale:** 🟢 **GREEN** (clean) → 🟡 **YELLOW** (watch list) → 🟠 **ORANGE** (deteriorating quality) → 🔴 **RED** (likely fraud, distress, or accounting failure)

---

"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
         max-width: 860px; margin: 40px auto; padding: 0 20px;
         color: #1d1d1f; line-height: 1.55; }}
  h1 {{ border-bottom: 2px solid #1d1d1f; padding-bottom: 8px; }}
  h2 {{ margin-top: 2em; border-bottom: 1px solid #d2d2d7; padding-bottom: 4px; }}
  h3 {{ margin-top: 1.5em; }}
  blockquote {{ background: #f5f5f7; border-left: 4px solid #6e6e73;
                padding: 12px 18px; margin: 1.2em 0; border-radius: 4px; }}
  code {{ background: #f5f5f7; padding: 2px 5px; border-radius: 3px;
          font-size: 0.92em; }}
  table {{ border-collapse: collapse; margin: 1em 0; }}
  th, td {{ border: 1px solid #d2d2d7; padding: 6px 12px; text-align: left; }}
  th {{ background: #f5f5f7; }}
  hr {{ border: none; border-top: 1px solid #d2d2d7; margin: 2em 0; }}
  strong {{ color: #1d1d1f; }}
  .meta {{ color: #6e6e73; font-size: 0.9em; margin-bottom: 2em; }}
</style>
</head>
<body>
<div class="meta">Generated {timestamp} by forensic_analyst.py</div>
{body}
</body>
</html>
"""

SYSTEM_PROMPT = """You are a forensic financial statement analyst. Your job is to read SEC filings (10-K and 10-Q) the way Howard Schilit, Jim Chanos, or a short-seller's research team would: with deep suspicion, searching for the specific accounting patterns that have empirically preceded large stock price declines.

You are speaking to a trader who already understands technicals, news flow, and price action — but who does NOT have the accounting training to read filings forensically. Your job is to surface what they would miss.

# Your analytical framework: three tiers of red flags

## Tier 1 — Catastrophic (empirically precede 30%+ drawdowns, frauds, restatements, or bankruptcies)

- **Net income vs. operating cash flow divergence**: NI growing while CFO stagnates or declines. Sustained negative free cash flow with positive NI. Precedents: Enron (NI grew, CFO collapsed), WorldCom (capitalized operating expenses), Tyco.
- **Revenue recognition irregularities**: bill-and-hold arrangements, channel stuffing, multi-element revenue with aggressive allocation, percentage-of-completion estimates that swing, related-party revenue, "other revenue" growing faster than core. Precedents: Sunbeam, Lucent, Computer Associates, Luckin Coffee.
- **Receivables growing materially faster than revenue** (DSO expansion): suggests booking sales that may not collect. Precedent: Symbol Technologies.
- **Auditor changes, especially mid-year or to a smaller firm**: a Big Four → mid-tier downgrade is a flashing light. Precedent: Wirecard (EY → BDO would have been a tell), HealthSouth.
- **Going concern paragraph or "substantial doubt" language** in the audit opinion, even hedged.
- **Restatements of prior periods** — any restatement, especially of revenue or earnings. The first restatement is almost never the last.
- **Material weakness in internal controls (ICFR)**: management or auditor admitting controls don't work. Precedent: many subsequent frauds.
- **Late filings (NT 10-K / NT 10-Q)**: management can't close the books on time. Precedent: most major frauds had late filings before unraveling.

## Tier 2 — Multiple compression (precede 10–25% declines as quality deteriorates)

- **Stock-based compensation growing materially faster than revenue** — true earnings power is eroding for shareholders even if GAAP looks fine.
- **Working capital deterioration**: rising DSO (days sales outstanding), rising DIO (days inventory outstanding), or falling DPO (days payable outstanding) all signal cash conversion stress.
- **Inventory growing faster than COGS / revenue**: writedown risk. Precedents: many retailers and semis pre-cycle.
- **Off-balance-sheet liabilities**: operating lease commitments (now mostly on BS post-ASC 842, but check footnotes), purchase obligations, unconsolidated JVs, VIEs.
- **Goodwill that's a large share of equity and hasn't been impaired despite weak segment performance** — pending impairment risk. Precedents: GE, Kraft Heinz.
- **Pension underfunding** that's material relative to market cap.
- **Customer concentration**: a single customer >10% of revenue is disclosed; if it's growing, that's leverage you don't control.
- **Aggressive non-GAAP "adjusted" metrics**: especially when adjustments grow as a share of GAAP earnings, or when recurring items (SBC, restructuring) are repeatedly excluded.
- **Effective tax rate volatility or unusually low rates** sustained without disclosed driver.
- **Debt covenants tightening** or material refinancings coming due in next 12–24 months.

## Tier 3 — Context (worth noting but not actionable alone)

- Accounting policy changes (revenue recognition, depreciation lives, inventory method)
- Segment reporting changes (especially reorganizations that obscure historical comparability)
- Critical audit matters (CAMs) in the auditor's report — what the auditor flagged as requiring extra work
- Insider transaction patterns disclosed in the filing
- Related party transactions
- Changes in CFO, controller, or chief accounting officer
- Litigation contingencies, especially SEC investigations or class actions

# Output format

Produce a Markdown report with these sections, in order:

1. **Header**: ticker, fiscal year covered, filing date, auditor
2. **VERDICT** (single line): one of GREEN / YELLOW / ORANGE / RED, with a one-sentence justification
3. **Tier 1 flags** (or "None identified" — be honest)
4. **Tier 2 flags**
5. **Tier 3 context**
6. **What looks clean** — the genuine strengths, so the trader knows what NOT to short on
7. **Bottom line for a trader** — 2–4 sentences. Are the financials consistent with the narrative? What would you watch in the next filing?

For EVERY flag you raise, you MUST include:
- The specific line item, table, or footnote (e.g. "Note 3 — Revenue Disaggregation, page 47" or "Consolidated Statements of Cash Flows")
- The actual numbers with year-over-year (or comparable period) deltas
- A one-line historical precedent: the company and what happened (e.g. "Enron 2001: NI grew 10% while CFO went negative — bankrupt 11 months later")
- Why this matters for the equity

Verdict calibration:
- **GREEN**: clean financials, no Tier 1 flags, ≤1 minor Tier 2 flag with benign explanation
- **YELLOW**: 1–2 Tier 2 flags, or several Tier 3 items, but nothing on Tier 1
- **ORANGE**: any Tier 1 flag, OR ≥3 material Tier 2 flags, OR a mix that suggests deteriorating quality
- **RED**: multiple Tier 1 flags, restatement, going concern, auditor change, or evidence of likely fraud

Be specific. Be skeptical. Cite numbers. A trader cannot act on "concerns about revenue quality" — they can act on "DSO expanded from 38 to 54 days while revenue grew 8%, suggesting $X billion of receivables that may not convert to cash."

If the filing genuinely looks clean, SAY SO. False positives destroy your credibility. The Enrons are rare; most large-cap 10-Ks are boring."""

COMPARE_SYSTEM_PROMPT = SYSTEM_PROMPT + """

# Year-over-year comparison mode

You will be given TWO filings: the current year and the prior year. Your job is to produce a YoY DELTA report, not two independent reports.

Output sections (Markdown):

1. **Header**: ticker, current period, prior period
2. **TRAJECTORY VERDICT**: improving / stable / deteriorating / sharply deteriorating, with one-sentence justification
3. **New flags this year** (didn't exist or weren't material in prior year)
4. **Escalated flags** (existed before but got worse — quantify the deterioration)
5. **Resolved or improved concerns** (flags from prior year that are now better — be specific about what changed)
6. **What changed in disclosure** (new risk factors, restatements, accounting policy changes, auditor changes, segment changes, going-concern language added or removed)
7. **Bottom line for a trader**: 2–4 sentences on direction of travel. Is the financial story consistent with the equity narrative?

Be ruthlessly comparative. Numbers with deltas. Do not re-state both years' analyses — focus on what CHANGED."""


@dataclass
class Filing:
    ticker: str
    cik: int
    form: str
    accession: str
    filing_date: str
    period_of_report: str
    primary_document: str
    url: str
    text: str


def ticker_to_cik(ticker: str) -> int:
    r = requests.get(TICKER_MAP_URL, headers=SEC_HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    ticker_u = ticker.upper()
    for entry in data.values():
        if entry["ticker"].upper() == ticker_u:
            return int(entry["cik_str"])
    raise SystemExit(f"Ticker {ticker} not found in SEC EDGAR ticker map")


def get_filings_index(cik: int) -> dict:
    r = requests.get(SUBMISSIONS_URL.format(cik=cik), headers=SEC_HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def find_filings(submissions: dict, form: str, n: int) -> list[dict]:
    recent = submissions["filings"]["recent"]
    matches = []
    for i, f in enumerate(recent["form"]):
        if f == form:
            matches.append(
                {
                    "accession": recent["accessionNumber"][i],
                    "filing_date": recent["filingDate"][i],
                    "period_of_report": recent["reportDate"][i],
                    "primary_document": recent["primaryDocument"][i],
                }
            )
            if len(matches) >= n:
                break
    if len(matches) < n:
        raise SystemExit(
            f"Only found {len(matches)} {form} filings in recent index; need {n}"
        )
    return matches


def fetch_filing_text(cik: int, accession: str, primary_document: str) -> tuple[str, str]:
    accession_clean = accession.replace("-", "")
    url = ARCHIVE_URL.format(cik=cik, accession_clean=accession_clean, document=primary_document)
    r = requests.get(url, headers=SEC_HEADERS, timeout=60)
    r.raise_for_status()

    soup = BeautifulSoup(r.content, "lxml")
    for tag in soup(["script", "style", "head", "meta", "link"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text, url


def fetch_filing(ticker: str, form: str = "10-K", n_back: int = 1) -> Filing:
    cik = ticker_to_cik(ticker)
    sub = get_filings_index(cik)
    filings = find_filings(sub, form, n_back)
    chosen = filings[n_back - 1]
    print(
        f"  → fetching {form} accession {chosen['accession']} "
        f"(filed {chosen['filing_date']}, period {chosen['period_of_report']})",
        file=sys.stderr,
    )
    text, url = fetch_filing_text(cik, chosen["accession"], chosen["primary_document"])
    print(f"    fetched {len(text):,} chars from {url}", file=sys.stderr)
    return Filing(
        ticker=ticker.upper(),
        cik=cik,
        form=form,
        accession=chosen["accession"],
        filing_date=chosen["filing_date"],
        period_of_report=chosen["period_of_report"],
        primary_document=chosen["primary_document"],
        url=url,
        text=text,
    )


def get_anthropic_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    key_file = os.path.expanduser("~/.anthropic-key")
    if os.path.exists(key_file):
        with open(key_file) as f:
            key = f.read().strip()
        if key:
            return key
    raise SystemExit(
        "No API key found. Set ANTHROPIC_API_KEY or put your key in "
        "~/.anthropic-key (chmod 600)."
    )


def analyze_single(client: anthropic.Anthropic, filing: Filing) -> str:
    user_content = (
        f"# Filing to analyze\n\n"
        f"Ticker: {filing.ticker}\n"
        f"Form: {filing.form}\n"
        f"Period: {filing.period_of_report}\n"
        f"Filed: {filing.filing_date}\n"
        f"Source URL: {filing.url}\n\n"
        f"---\n\n"
        f"{filing.text}"
    )

    print("  → calling Claude (streaming)...", file=sys.stderr)
    chunks: list[str] = []
    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        for text in stream.text_stream:
            chunks.append(text)
            print(text, end="", flush=True)
        final = stream.get_final_message()

    print(file=sys.stderr)
    usage = final.usage
    print(
        f"\n  → tokens: input={usage.input_tokens:,} "
        f"cache_read={usage.cache_read_input_tokens:,} "
        f"cache_write={usage.cache_creation_input_tokens:,} "
        f"output={usage.output_tokens:,}",
        file=sys.stderr,
    )
    return "".join(chunks)


def analyze_compare(
    client: anthropic.Anthropic, current: Filing, prior: Filing
) -> str:
    user_content = (
        f"# Comparison task\n\n"
        f"Ticker: {current.ticker}\n"
        f"Current filing: {current.form} for period {current.period_of_report} "
        f"(filed {current.filing_date})\n"
        f"Prior filing:   {prior.form} for period {prior.period_of_report} "
        f"(filed {prior.filing_date})\n\n"
        f"Produce a YoY delta report as specified.\n\n"
        f"=================================================================\n"
        f"=== CURRENT FILING ({current.period_of_report}) — {current.url}\n"
        f"=================================================================\n\n"
        f"{current.text}\n\n"
        f"=================================================================\n"
        f"=== PRIOR FILING ({prior.period_of_report}) — {prior.url}\n"
        f"=================================================================\n\n"
        f"{prior.text}"
    )

    print("  → calling Claude with both filings (streaming)...", file=sys.stderr)
    chunks: list[str] = []
    with client.messages.stream(
        model=MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[
            {
                "type": "text",
                "text": COMPARE_SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": user_content}],
    ) as stream:
        for text in stream.text_stream:
            chunks.append(text)
            print(text, end="", flush=True)
        final = stream.get_final_message()

    print(file=sys.stderr)
    usage = final.usage
    print(
        f"\n  → tokens: input={usage.input_tokens:,} "
        f"cache_read={usage.cache_read_input_tokens:,} "
        f"cache_write={usage.cache_creation_input_tokens:,} "
        f"output={usage.output_tokens:,}",
        file=sys.stderr,
    )
    return "".join(chunks)


def save_report(
    body_markdown: str,
    ticker: str,
    period: str,
    form: str,
    output_dir: Path,
    open_after: bool,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = dt.datetime.now()
    stamp = now.strftime("%Y-%m-%d_%H%M%S")
    base = f"{ticker}_{form}_{period}_{stamp}"
    md_path = output_dir / f"{base}.md"
    html_path = output_dir / f"{base}.html"

    full_md = REPORT_PREAMBLE + body_markdown
    md_path.write_text(full_md, encoding="utf-8")

    html_body = md_lib.markdown(
        full_md,
        extensions=["fenced_code", "tables", "sane_lists"],
    )
    html_doc = HTML_TEMPLATE.format(
        title=f"{ticker} {form} {period} — Forensic Report",
        timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
        body=html_body,
    )
    html_path.write_text(html_doc, encoding="utf-8")

    print(f"\nReport saved:", file=sys.stderr)
    print(f"  Markdown: {md_path}", file=sys.stderr)
    print(f"  HTML:     {html_path}", file=sys.stderr)

    if open_after and sys.platform == "darwin":
        subprocess.run(["open", str(html_path)], check=False)
        print(f"  Opened in browser.", file=sys.stderr)

    return md_path, html_path


def main() -> None:
    p = argparse.ArgumentParser(description="Forensic financial statement analyst")
    p.add_argument("ticker", help="Stock ticker (e.g. AAPL)")
    p.add_argument(
        "--compare",
        action="store_true",
        help="Also fetch prior year 10-K and produce a YoY delta report",
    )
    p.add_argument(
        "--form",
        default="10-K",
        choices=["10-K", "10-Q"],
        help="Filing type (default 10-K)",
    )
    p.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help=f"Directory to save reports (default {DEFAULT_REPORT_DIR})",
    )
    p.add_argument(
        "--no-open",
        action="store_true",
        help="Don't auto-open the HTML report in the browser",
    )
    p.add_argument(
        "--no-save",
        action="store_true",
        help="Print to stdout only; skip saving Markdown/HTML files",
    )
    args = p.parse_args()

    print(f"[1/2] Fetching latest {args.form} for {args.ticker.upper()}...", file=sys.stderr)
    current = fetch_filing(args.ticker, form=args.form, n_back=1)

    client = anthropic.Anthropic(api_key=get_anthropic_key())

    sections: list[str] = []

    if args.compare:
        print(f"\n[1.5/2] Fetching prior {args.form}...", file=sys.stderr)
        prior = fetch_filing(args.ticker, form=args.form, n_back=2)

        print(f"\n[2a/2] Running single-filing analysis on current period...\n", file=sys.stderr)
        header1 = f"=== FORENSIC REPORT — {current.ticker} {args.form} {current.period_of_report} ==="
        print("=" * len(header1))
        print(header1)
        print("=" * len(header1))
        single_body = analyze_single(client, current)
        sections.append(single_body)

        print("\n\n")
        header2 = (
            f"=== YoY COMPARISON — {current.ticker} "
            f"{current.period_of_report} vs {prior.period_of_report} ==="
        )
        print("=" * len(header2))
        print(header2)
        print("=" * len(header2))
        print(f"\n[2b/2] Running YoY comparison...\n", file=sys.stderr)
        compare_body = analyze_compare(client, current, prior)
        sections.append(
            f"\n\n---\n\n# Year-over-year comparison: "
            f"{current.period_of_report} vs {prior.period_of_report}\n\n"
            + compare_body
        )
    else:
        print(f"\n[2/2] Running forensic analysis...\n", file=sys.stderr)
        header = f"=== FORENSIC REPORT — {current.ticker} {args.form} {current.period_of_report} ==="
        print("=" * len(header))
        print(header)
        print("=" * len(header))
        sections.append(analyze_single(client, current))

    if not args.no_save:
        body = "\n".join(sections)
        save_report(
            body_markdown=body,
            ticker=current.ticker,
            period=current.period_of_report,
            form=args.form,
            output_dir=args.output_dir,
            open_after=not args.no_open,
        )


if __name__ == "__main__":
    main()
