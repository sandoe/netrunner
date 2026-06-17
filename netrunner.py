#!/usr/bin/env python3
"""Netrunner entry point — run from the project root."""
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from backend.main import main
import subprocess

if __name__ == "__main__":
    # Start the background engine
    engine_path = os.path.join(os.path.dirname(__file__), "backend", "engine.py")
    engine_process = subprocess.Popen([sys.executable, engine_path])
    
    try:
        main()
    finally:
        engine_process.terminate()
        engine_process.wait()
