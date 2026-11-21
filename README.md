# EN-VI VLM benchmark

Incremental publication - part 2/6: pinned sources, deterministic sampling and EN-VI drafts.

Pinned adapters cover RePOPE, VSR, TallyQA and the 8-class Pet subset. Metadata, pilot exclusions and unapproved main drafts are versioned. Images/cache stay outside Git.

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
