"""Adds project root to sys.path at import time — import this in standalone scripts."""
import sys
import os

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if _root not in sys.path:
    sys.path.insert(0, _root)
