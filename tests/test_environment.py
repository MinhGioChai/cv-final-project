import importlib.metadata
from types import SimpleNamespace

from vlmbench.environment import inspect_environment


def test_missing_runtime_is_not_reported_as_ready(monkeypatch):
    monkeypatch.setattr("vlmbench.environment.shutil.which", lambda name: None)
    def missing(name):
        raise importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr("vlmbench.environment.importlib.metadata.version", missing)
    report = inspect_environment()
    assert report["status"] == "inference_dependencies_missing"
    assert not report["torch_cuda_runtime_tested"]
    assert report["gpus"] == []


def test_driver_inventory_does_not_claim_cuda_model_loading(monkeypatch):
    monkeypatch.setattr("vlmbench.environment.shutil.which", lambda name: "synthetic_nvidia_smi")
    monkeypatch.setattr("vlmbench.environment.subprocess.run", lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="synthetic_test_only GPU, 6144, 999.0\n"))
    monkeypatch.setattr("vlmbench.environment.importlib.metadata.version", lambda name: "synthetic_test_only")
    report = inspect_environment()
    assert report["gpus"][0]["total_memory_mib"] == 6144
    assert report["status"] == "runtime_smoke_test_required"
    assert not report["model_weights_downloaded_by_check"]
    assert not report["torch_cuda_runtime_tested"]
