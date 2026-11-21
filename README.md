# EN-VI VLM benchmark

Incremental publication - part 5/6: 22-packet main review and private workspace handoff.

Offline HTML templates/generator and pending review packets cover 1,000 rows in 22 batches. Two distinct translation reviewers and separate image QA are required. Main is not frozen or inference-ready.

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

Get `team_workspace_v1.zip` privately from the project owner. Restore with
`.venv/Scripts/python.exe scripts/team_workspace.py restore --archive exports/team_workspace_v1.zip`,
then open `reports/stage1/v10/main_review/index.html`. Images/generated pages
are intentionally excluded from Git; the generator is `scripts/review_main.py export`.
