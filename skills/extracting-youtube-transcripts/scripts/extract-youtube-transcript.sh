#!/bin/bash
# Extract clean transcript text from a YouTube video using yt-dlp
#
# Usage:
#   extract-youtube-transcript.sh <youtube-url> [output-file]
#
# If output-file is omitted, prints to stdout.
# Strips VTT formatting, timestamps, and duplicate lines.
#
# Dependencies: yt-dlp, python3
#
# Examples:
#   extract-youtube-transcript.sh "https://www.youtube.com/watch?v=abc123"
#   extract-youtube-transcript.sh "https://www.youtube.com/watch?v=abc123" /tmp/transcript.txt

set -euo pipefail

URL="${1:-}"
OUTPUT="${2:-}"

if [[ -z "$URL" ]]; then
  echo "Usage: extract-youtube-transcript.sh <youtube-url> [output-file]" >&2
  exit 1
fi

# Validate it looks like a YouTube URL
if [[ ! "$URL" =~ youtube\.com|youtu\.be ]]; then
  echo "Error: doesn't look like a YouTube URL" >&2
  exit 1
fi

# Check dependencies
if ! command -v yt-dlp &>/dev/null; then
  echo "Error: yt-dlp not found. Install with: brew install yt-dlp" >&2
  exit 1
fi

# Create temp dir for VTT download
TMPDIR=$(mktemp -d)
trap "rm -rf $TMPDIR" EXIT

# Strip timestamp parameter if present (not needed for transcript)
CLEAN_URL=$(echo "$URL" | sed 's/[&?]t=[0-9]*s\?//g')

# Download auto-generated subtitles
yt-dlp \
  --write-auto-sub \
  --sub-lang en \
  --skip-download \
  --sub-format vtt \
  -o "$TMPDIR/%(id)s" \
  "$CLEAN_URL" 2>&1 | grep -v "^$" >&2

# Find the VTT file
VTT_FILE=$(find "$TMPDIR" -name "*.vtt" | head -1)

if [[ -z "$VTT_FILE" ]]; then
  echo "Error: no subtitles found for this video" >&2
  exit 1
fi

# Clean VTT into plain text
TRANSCRIPT=$(python3 -c "
import re, sys

with open('$VTT_FILE') as f:
    text = f.read()

lines = text.split('\n')
clean = []
seen = set()
for line in lines:
    line = line.strip()
    if not line or line.startswith('WEBVTT') or line.startswith('Kind:') or line.startswith('Language:'):
        continue
    if '-->' in line or re.match(r'^\d{2}:\d{2}', line):
        continue
    line = re.sub(r'<[^>]+>', '', line)
    if line and line not in seen:
        seen.add(line)
        clean.append(line)

print(' '.join(clean))
")

if [[ -n "$OUTPUT" ]]; then
  echo "$TRANSCRIPT" > "$OUTPUT"
  CHARS=$(echo "$TRANSCRIPT" | wc -c | tr -d ' ')
  echo "Wrote $CHARS chars to $OUTPUT" >&2
else
  echo "$TRANSCRIPT"
fi
