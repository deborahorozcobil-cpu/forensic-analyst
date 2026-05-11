#!/bin/zsh
# Reads your Anthropic API key from the terminal without echoing it,
# and writes it to ~/.anthropic-key with strict permissions.

printf "Paste your API key, then press Enter (input is hidden):\n"
IFS= read -rs key
printf '%s' "$key" > ~/.anthropic-key
chmod 600 ~/.anthropic-key
unset key

bytes=$(wc -c < ~/.anthropic-key | tr -d ' ')
printf "\nSaved %s bytes to ~/.anthropic-key\n" "$bytes"
if [ "$bytes" -lt 100 ] || [ "$bytes" -gt 120 ]; then
  printf "WARNING: expected ~108 bytes for an Anthropic API key. Got %s. Probably wrong.\n" "$bytes"
fi
