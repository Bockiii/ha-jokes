#!/usr/bin/env python3
"""Guard the two things that have silently broken releases before.

1. Version lockstep — HACS reads manifest.json's `version`, const.py's VERSION feeds the
   `?v=` cache-buster on the injected card URL, and CARD_VERSION is the card's own banner.
   If they drift, users get a stale card served under a new integration version.
2. The card's `window.customCards` entry must declare `preview: true` — HA's card picker
   maps that flag to `showElement`, and with `false` the card shows a bare description
   placeholder instead of a live preview (shipped broken in 1.4.0).

Run from the repo root: python3 scripts/check_versions.py
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "ha_jokes"
CARD = COMPONENT / "www" / "ha-jokes-card.js"

errors: list[str] = []

manifest_version = json.loads((COMPONENT / "manifest.json").read_text())["version"]

const_match = re.search(r'^VERSION\s*=\s*"([^"]+)"', (COMPONENT / "const.py").read_text(), re.M)
const_version = const_match.group(1) if const_match else None

card_text = CARD.read_text()
card_match = re.search(r'^const CARD_VERSION\s*=\s*"([^"]+)"', card_text, re.M)
card_version = card_match.group(1) if card_match else None

if const_version is None:
    errors.append("could not find VERSION in const.py")
if card_version is None:
    errors.append("could not find CARD_VERSION in ha-jokes-card.js")

if len({manifest_version, const_version, card_version}) != 1:
    errors.append(
        "version drift: manifest.json={} const.py={} CARD_VERSION={}".format(
            manifest_version, const_version, card_version
        )
    )

if not re.search(r"preview:\s*true", card_text):
    errors.append(
        "ha-jokes-card.js: window.customCards entry must set `preview: true`, "
        "otherwise the card renders no preview in HA's card picker"
    )

# Every rule in the card's <style> is document-scoped (the <style> sits in ha-card's light
# DOM), so unscoped generic selectors leak into the whole HA frontend.
style_block = re.search(r"style\.textContent = `(.*?)`;", card_text, re.S)
if not style_block:
    errors.append("could not find the card's style block")
else:
    for line in style_block.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith(".") and "{" in stripped:
            errors.append(f"unscoped CSS selector (must start with `ha-jokes-card`): {stripped}")

if errors:
    print("FAIL")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print(f"OK — version {manifest_version} in lockstep, card preview enabled, CSS scoped")
