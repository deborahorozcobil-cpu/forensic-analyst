#!/bin/zsh
# Double-click launcher for forensic_analyst.py.
# Prompts for a ticker and an analysis type, then runs the analysis.

set -e
PROJECT_DIR="$HOME/Projects/forensic-analyst"
cd "$PROJECT_DIR"

# 1) Ask for ticker
TICKER=$(osascript <<'APPLESCRIPT'
try
  set ticker to text returned of (display dialog "Enter a stock ticker (e.g. AAPL, MSFT, TSLA):" default answer "AAPL" with title "Forensic Analyst" buttons {"Cancel", "Next"} default button "Next")
  return ticker
on error
  return ""
end try
APPLESCRIPT
)

if [ -z "$TICKER" ]; then
  echo "Cancelled."
  exit 0
fi

# Normalize to uppercase
TICKER=$(echo "$TICKER" | tr '[:lower:]' '[:upper:]' | tr -d ' ')

# 2) Ask which kind of analysis
CHOICE=$(osascript <<APPLESCRIPT
try
  set options to {"Annual report (10-K) — most thorough", "Annual report (10-K) + year-over-year comparison", "Latest quarterly report (10-Q) — faster and cheaper"}
  set chosen to choose from list options with title "Forensic Analyst — $TICKER" with prompt "Which analysis do you want to run on $TICKER?" default items {"Annual report (10-K) — most thorough"} OK button name "Run" cancel button name "Cancel"
  if chosen is false then
    return "cancel"
  else
    return item 1 of chosen
  end if
on error
  return "cancel"
end try
APPLESCRIPT
)

EXTRA_FLAGS=()
case "$CHOICE" in
  "cancel")
    echo "Cancelled."
    exit 0
    ;;
  "Annual report (10-K) — most thorough")
    LABEL="10-K"
    ;;
  "Annual report (10-K) + year-over-year comparison")
    EXTRA_FLAGS=(--compare)
    LABEL="10-K with YoY comparison"
    ;;
  "Latest quarterly report (10-Q) — faster and cheaper")
    EXTRA_FLAGS=(--form 10-Q)
    LABEL="10-Q"
    ;;
esac

echo "================================================================"
echo "  Forensic Analyst"
echo "  Ticker:   $TICKER"
echo "  Analysis: $LABEL"
echo "================================================================"
echo

.venv/bin/python forensic_analyst.py "$TICKER" "${EXTRA_FLAGS[@]}"

echo
echo "================================================================"
echo "  Done. The HTML report should have opened in your browser."
echo "  All reports are saved in: ~/Documents/forensic-reports/"
echo "================================================================"
echo
echo "Press Return to close this window..."
read -r _
