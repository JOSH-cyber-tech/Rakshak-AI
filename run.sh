#!/usr/bin/env bash
# Zero-dependency launch. Open http://localhost:${1:-8000}
cd "$(dirname "$0")"
python3 -m api.server "${1:-8000}"
