"""Explicit setup step for a separate inference venv; run locally or from cloud notebooks."""
import argparse
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", default=".venv-infer", help="New or existing inference venv")
    args = parser.parse_args()
    if not (3, 11) <= sys.version_info[:2] <= (3, 13):
        raise SystemExit("Use Python 3.11–3.13 with this runtime lock (3.12 is the project baseline)")
    root = Path(__file__).resolve().parents[1]
    env = Path(args.env).resolve()
    subprocess.run([sys.executable, "-m", "venv", str(env)], check=True)
    python = env / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    commands = [
        [str(python), "-m", "pip", "install", "--disable-pip-version-check", "torch==2.7.1", "torchvision==0.22.1", "--index-url", "https://download.pytorch.org/whl/cu126"],
        [str(python), "-m", "pip", "install", "-r", str(root / "requirements-inference.lock.txt")],
        [str(python), "-m", "pip", "install", "--no-deps", "--no-build-isolation", "-e", str(root)],
        [str(python), "-m", "pip", "check"],
        [str(python), "-c", "import torch; print({'torch':torch.__version__, 'cuda_build':torch.version.cuda, 'cuda_available':torch.cuda.is_available()})"],
    ]
    for command in commands:
        subprocess.run(command, check=True, cwd=root)
    print(f"Inference Python: {python}")


if __name__ == "__main__":
    main()
