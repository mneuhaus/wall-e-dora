"""Basic tests for the audio node."""

import pytest


def test_import_main():
    """Test that the main function can be imported and called."""
    from audio.main import main

    # Check that everything is working, and catch dora Runtime Exception as we're not running in a dora dataflow.
    with pytest.raises(RuntimeError):
        main()
