"""Backwards-compatible shim for the original ``chaos_runner`` entrypoint.

The experiment-running logic now lives in the :mod:`chaos_lab` package. This
module is kept so existing references (``python src/chaos_runner.py``) continue
to work; it simply delegates to the packaged Click CLI.
"""

from __future__ import annotations

from chaos_lab.cli import main

if __name__ == "__main__":  # pragma: no cover
    main()
