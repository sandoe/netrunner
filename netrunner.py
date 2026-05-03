#!/usr/bin/env python3
"""Netrunner entry point — run from the project root."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from backend.main import main

if __name__ == "__main__":
    main()
