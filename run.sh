#!/usr/bin/env bash
# Creates a local venv on first run (no sudo needed), then starts the app.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python -m venv .venv
  .venv/bin/pip install -r requirements.txt
  .venv/bin/pip install --no-deps "moviepy==2.2.1"
fi
exec .venv/bin/python main.py
