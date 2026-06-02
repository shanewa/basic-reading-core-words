#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CLI entry point — logic lives in vocab_pdf package."""

import sys
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from vocab_pdf.cli import main

if __name__ == "__main__":
    sys.exit(main())
