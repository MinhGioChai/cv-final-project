# EN?VI VLM benchmark

Incremental publication ? part 1/6: pinned CPU environment and data foundation.

This commit provides strict manifests, atomic UTF-8 I/O, parsing, QA/leakage
checks, sampling and the CPU test environment. Dataset acquisition, paired
evaluation, GPU pilots and the 22-packet review workflow are published in
subsequent commits. This is zero-shot evaluation, not model training.

Use Python 3.12 from the repository root (Windows PowerShell):

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements-stage0.lock.txt
.venv/Scripts/python.exe -m pip install --no-build-isolation --no-deps -e .
.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider
.venv/Scripts/python.exe scripts/check_repository.py
```

On Linux/macOS replace `Scripts/python.exe` with `bin/python`. No GPU,
model weights or dataset images are required for these synthetic tests.
The CLI is added with the pilot/evaluation integration, not in this part.
Raw images, checkpoints, credentials and generated review pages stay outside Git.
