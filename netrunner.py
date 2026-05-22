#!/usr/bin/env python3
"""Netrunner entry point — run from the project root."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from backend.main import main

if __name__ == "__main__":
    main()
