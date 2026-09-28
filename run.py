#!/usr/bin/env python3
"""SatyaBid — Intelligent Bid Scrutiny & Cartel Detection

One-command runner: Launches the local server and automatically opens Screen S1.
Usage:
    python run.py
"""

import os
import sys

if __name__ == "__main__":
    repo_root = os.path.dirname(os.path.abspath(__file__))
    mvp_dir = os.path.join(repo_root, "mvp")
    os.chdir(mvp_dir)
    sys.path.insert(0, mvp_dir)
    import serve
    # Default to opening browser if not specified
    if "--no-open" in sys.argv:
        sys.argv.remove("--no-open")
    else:
        if "--open" not in sys.argv:
            sys.argv.append("--open")
    serve.main()
