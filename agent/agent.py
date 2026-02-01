#!/usr/bin/env python
"""Launcher for the packaged Helios agent.

This small script mirrors the previous simple-entrypoint used during
local testing. It imports the package CLI and invokes it so running
`python agent/agent.py` works from the workspace root.
"""
from helios_agent.cli import main


if __name__ == "__main__":
    main()
