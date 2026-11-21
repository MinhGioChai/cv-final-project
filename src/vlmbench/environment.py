"""Lightweight environment inventory; never imports or downloads model weights."""

import csv
from datetime import datetime, timezone
import importlib.metadata
import io
import platform
import shutil
import subprocess
from typing import Any


def inspect_environment() -> dict[str, Any]:
    packages = {}
    for name in ("torch", "torchvision", "transformers", "accelerate", "bitsandbytes", "qwen-vl-utils", "Pillow",
                 "tokenizers", "huggingface-hub", "safetensors", "numpy", "sentencepiece", "protobuf"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    gpus = []
    command = shutil.which("nvidia-smi")
    status = "not_found"
    if command:
        try:
            result = subprocess.run([command, "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader,nounits"],
                                    capture_output=True, text=True, timeout=10, check=False)
            status = "ok" if result.returncode == 0 else "driver_query_failed"
            if result.returncode == 0:
                for row in csv.reader(io.StringIO(result.stdout)):
                    if len(row) == 3:
                        gpus.append({"name": row[0].strip(), "total_memory_mib": int(row[1].strip()), "driver_version": row[2].strip()})
        except (OSError, ValueError, subprocess.TimeoutExpired):
            status = "driver_query_failed"
    missing = [name for name in ("torch", "transformers", "accelerate") if packages[name] is None]
    return {
        "recorded_at_utc": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "os": platform.system(), "packages": packages, "nvidia_smi_status": status, "gpus": gpus,
        "missing_core_inference_packages": missing, "torch_cuda_runtime_tested": False,
        "model_weights_downloaded_by_check": False,
        "status": "inference_dependencies_missing" if missing else "runtime_smoke_test_required",
        "next_step": "Choose the inference environment, pin/install model dependencies there, then test CUDA and model loading on a QA-ready subset",
    }
