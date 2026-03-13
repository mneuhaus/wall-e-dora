"""Basic tests for the web node."""

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'web'))


def test_import_main(monkeypatch):
    """Test that the main function can be imported and called."""
    from web import main as web_main

    monkeypatch.setattr(web_main, 'start_background_webserver', lambda: None)

    # Check that everything is working, and catch dora Runtime Exception as we're not running in a dora dataflow.
    with pytest.raises(RuntimeError):
        web_main.main()
