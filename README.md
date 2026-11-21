# EN-VI VLM benchmark

Incremental publication - part 3/6: paired evaluation and image-cluster bootstrap.

Paired task metrics and image-cluster confidence intervals are available through Python APIs. Small real pilot output snapshots permit CPU analysis without images; the CLI arrives in part 4.

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
