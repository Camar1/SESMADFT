from __future__ import annotations

import pathlib
import sys

import app


ROOT = pathlib.Path(__file__).resolve().parent
sys.stdout = (ROOT / "ses_server_8000.out.log").open("a", encoding="utf-8")
sys.stderr = (ROOT / "ses_server_8000.err.log").open("a", encoding="utf-8")
sys.argv = ["app.py", "--port", "8000"]

app.main()
