#!/bin/sh
# Builds resume.html, Ajay_Kumar_Dwivedi.pdf, index.html and dark.html from README.md.
# Uses the `python` on PATH, so activate your virtual environment first:
#   source .venv/bin/activate && pip install -r requirements-build.txt && ./build.sh
exec python "$(dirname "$0")/build.py" "$@"
