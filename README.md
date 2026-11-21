# EN-VI VLM benchmark

Incremental publication - part 4/6: bounded local/cloud pilots and integrated CLI.

The CLI, Qwen NF4/FP16 and Gemma NF4/BF16 team pilot launcher are available. No actual cloud GPU generation has been verified. Pilot image data is obtained privately.

## Check this snapshot (Python 3.12)

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-stage0.lock.txt
.venv/Scripts/python.exe -m pip install --no-build-isolation --no-deps -e .
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe scripts/check_repository.py
```

Linux/macOS: replace `Scripts/python.exe` with `bin/python`. Tests are synthetic,
CPU-only, and do not download images or model weights. Full research/team
documentation is published in the final documentation part. Do not run the
main benchmark before human QA, baseline freeze and explicit run approval.

CLI inventory: `.venv/Scripts/python.exe -m vlmbench.cli --help`.
