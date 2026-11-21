"""Generate output-free Colab/Kaggle notebooks using the current team pilot launcher."""
import hashlib
import json
from pathlib import Path


def cell(kind,source):
    source=source.strip()
    value={'cell_type':kind,'id':hashlib.sha256(source.encode()).hexdigest()[:12],
           'metadata':{},'source':source.splitlines(keepends=True)}
    if kind=='code':value.update(execution_count=None,outputs=[])
    return value


def generate(platform):
    if platform not in {'colab','kaggle'}:raise ValueError('Choose colab/kaggle')
    cells=[cell('markdown',f'''# EN–VI team pilot — {platform.title()}
Máy cá nhân không cần GPU. Bật GPU trên {platform.title()}; Kaggle cần Internet On.
Qwen dùng NF4/FP16; Gemma dùng NF4/BF16 và cần GPU có native BF16.
Mặc định 2 mẫu × EN/VI; tối đa 10 mẫu mỗi model. Chạy từng model một.
Dùng ZIP mới `pilot_team_v1.zip`, có 30 ảnh pilot đã QA; không dùng ZIP workspace lớn.
Gemma cần tài khoản đã được cấp quyền và secret HF_TOKEN của chính bạn.
Notebook không chứa token hoặc output model. Cloud generation chưa được project xác minh thực tế.
''')]
    bootstrap='''
import os, sys, json, zipfile, shutil, subprocess, hashlib, stat
from pathlib import Path

def safe_extract(archive_path, destination):
    destination=Path(destination).resolve()
    with zipfile.ZipFile(archive_path) as archive:
        if sum(i.file_size for i in archive.infolist())>100*1024**2:
            raise ValueError("Use the small pilot_team ZIP, not the main workspace/weights ZIP")
        names=archive.namelist()
        if len(names)!=len(set(names)):
            raise ValueError("Duplicate archive entries")
        for item in archive.infolist():
            target=(destination/item.filename).resolve()
            if not item.filename.startswith("vlmbench-pilot/") or not target.is_relative_to(destination/"vlmbench-pilot") or ".." in Path(item.filename).parts or stat.S_ISLNK(item.external_attr>>16):
                raise ValueError("Unsafe pilot archive path/type")
        # Do not overwrite a previous workspace silently.
        for item in archive.infolist():
            target=destination/item.filename
            if target.is_file() and target.read_bytes()!=archive.read(item):
                raise ValueError("Existing pilot workspace differs. Use a fresh runtime or separate folder")
        archive.extractall(destination)
'''
    if platform=='colab':
        bootstrap+='''
PLATFORM="colab"
WORK=Path("/content")
from google.colab import files
uploaded=files.upload()  # Upload exactly one pilot_team_v1.zip.
bundles=[Path(name) for name in uploaded if name.endswith(".zip")]
assert len(bundles)==1, "Upload one current pilot_team ZIP"
safe_extract(bundles[0],WORK)
ROOT=WORK/"vlmbench-pilot"
del uploaded  # Release uploaded ZIP bytes from notebook memory.
'''
    else:
        bootstrap+='''
PLATFORM="kaggle"
WORK=Path("/kaggle/working")
# Attach the PRIVATE Dataset containing pilot_team_v1.zip first.
bundles=list(Path("/kaggle/input").rglob("pilot_team*.zip"))
if bundles:
    assert len(bundles)==1, "Attach a single pilot bundle"
    safe_extract(bundles[0],WORK)
else:
    candidates=[p.parent for p in Path("/kaggle/input").rglob("BUNDLE_CONTENTS.json")
                if (p.parent/"scripts/run_pilot.py").is_file()]
    assert len(candidates)==1, "Attach the current pilot ZIP/extracted Dataset"
    target=WORK/"vlmbench-pilot"
    if target.exists():
        assert (target/"BUNDLE_CONTENTS.json").read_bytes()==(candidates[0]/"BUNDLE_CONTENTS.json").read_bytes(), "Workspace differs"
    else:
        shutil.copytree(candidates[0],target)
ROOT=WORK/"vlmbench-pilot"
'''
    bootstrap+='''
assert (ROOT/"BUNDLE_CONTENTS.json").is_file(), "Invalid pilot bundle"
bundle_info=json.loads((ROOT/"BUNDLE_CONTENTS.json").read_text(encoding="utf-8"))
assert bundle_info["manifest"]=="data/pilot/stage1_qa_v1/pilot_manifest.csv", "Rebuild pilot_team_v1.zip with approved pilot manifest"
assert (ROOT/"scripts/run_pilot.py").is_file(), "Old bundle: current launcher is missing"
for name,spec in bundle_info["files"].items():
    target=(ROOT/name).resolve()
    assert target.is_relative_to(ROOT.resolve()), "Invalid bundle index path"
    assert hashlib.sha256(target.read_bytes()).hexdigest()==spec["sha256"], name
print({"project":str(ROOT),"pilot_rows":bundle_info["rows"],"workflow":"team_pilot_v1"})
'''
    cells.append(cell('code',bootstrap))
    cells.append(cell('markdown','''## 1. Môi trường GPU riêng
Cài đúng runtime lock; cell này chưa tải model weights. Python hỗ trợ 3.11–3.13.
Venv/cache ở /tmp, không lưu vào Drive hoặc Kaggle outputs. Không nâng package tùy ý.
'''))
    cells.append(cell('code','''
ENV_DIR=Path("/tmp/vlmbench-infer")
subprocess.run([sys.executable,str(ROOT/"scripts/setup_inference.py"),"--env",str(ENV_DIR)],check=True,cwd=ROOT)
PYTHON=ENV_DIR/"bin/python"
assert PYTHON.is_file()
subprocess.run([str(PYTHON),"-m","vlmbench.cli","doctor"],check=True,cwd=ROOT)
'''))
    cells.append(cell('markdown','''## 2. Chọn model, run name và checkpoint
Mỗi người/phiên dùng RUN_NAME riêng. Lần đầu RESUME=False; tăng LIMIT từ 2 lên 10
hoặc chạy tiếp cùng runtime/config thì đặt RESUME=True. Không nhập checkpoint GPU/config khác.
Gemma cần secret HF_TOKEN được notebook cấp quyền đọc; không paste token vào cell.
'''))
    config='''
MODEL="qwen"  # "gemma" uses the BF16 runner, never the legacy FP16 adapter.
LIMIT=2
RUN_NAME="smoke_001"  # Change before a new independent run.
RESUME=False
ALLOW_DOWNLOAD=True  # False means cached files only.
os.environ["HF_HOME"]="/tmp/vlmbench-hf-cache"
os.environ["HF_HUB_CACHE"]="/tmp/vlmbench-hf-cache/hub"
if MODEL=="gemma" and ALLOW_DOWNLOAD:
    try:
'''
    config+=('        from google.colab import userdata\n        token=userdata.get("HF_TOKEN")\n' if platform=='colab' else
             '        from kaggle_secrets import UserSecretsClient\n        token=UserSecretsClient().get_secret("HF_TOKEN")\n')
    config+='''
        if not token:raise ValueError("missing")
        os.environ["HF_TOKEN"]=token
        del token
    except Exception:
        raise RuntimeError("Enable the HF_TOKEN notebook secret for your licensed Gemma account") from None
'''
    if platform=='colab':
        config+='''
USE_DRIVE=True  # Mount your own Drive only if you want persistent checkpoint files.
if USE_DRIVE:
    from google.colab import drive
    drive.mount("/content/drive")
    OUT=Path("/content/drive/MyDrive/vlmbench-results/colab")
else:
    OUT=WORK/"vlmbench-results/colab"
'''
    else:
        config+='''
OUT=WORK/"vlmbench-results/kaggle"
# Save Version/download result ZIP; /tmp packages and weights are intentionally excluded.
'''
    config+='''
RESULT=OUT/"team_v1"/RUN_NAME/f"{MODEL}.jsonl"

def pilot(*extra):
    argv=[str(PYTHON),str(ROOT/"scripts/run_pilot.py"),"--python",str(PYTHON),
          "--model",MODEL,"--platform",PLATFORM,"--limit",str(LIMIT),
          "--run-name",RUN_NAME,"--output",str(RESULT)]
    if ALLOW_DOWNLOAD:argv.append("--online")
    if RESUME:argv.append("--resume")
    return subprocess.run([*argv,*extra],cwd=ROOT,check=True)

pilot("--dry-run")  # No model download/load, no predictions written.
'''
    cells.append(cell('code',config))
    cells.append(cell('markdown','''## 3. Chạy thật trên GPU
Cell dưới tải weights nếu ALLOW_DOWNLOAD=True. GPU check chạy trước tải weights;
Gemma dừng nếu thiếu native BF16, không tự fallback sang FP16/model khác.
Nếu OOM/lỗi, giữ JSONL/meta/summary rồi xem nguyên nhân. Resume chỉ cùng model/config/runtime.
Pilot rows đã human QA approved; đây vẫn là engineering pilot, không phải main benchmark.
'''))
    cells.append(cell('code','''
try:
    pilot()
except subprocess.CalledProcessError as error:
    print(f"Pilot stopped with exit code {error.returncode}; inspect the error and keep checkpoint files before retrying.")
summary=RESULT.with_suffix(".summary.json")
if summary.exists():
    print(json.loads(summary.read_text(encoding="utf-8")))
'''))
    cells.append(cell('markdown','''## 4. Tải kết quả
Giữ toàn bộ JSONL/.meta.json/.summary.json/.load_error.json nếu có. ZIP chỉ chứa results,
không chứa token, venv hoặc weights. Tải sau mỗi model, trước khi mất runtime.
Đổi MODEL rồi chạy lại phần 2–4 để thử model còn lại. Không cần chạy lại setup nếu venv còn nguyên.
'''))
    export='''
assert OUT.exists(), "No output directory yet; inspect pilot/preflight errors"
archive=shutil.make_archive(str(WORK/f"vlmbench-results-{PLATFORM}-{RUN_NAME}"),"zip",root_dir=OUT)
print(archive)
'''
    export+=('files.download(archive)\n' if platform=='colab' else
             'from IPython.display import FileLink,display\ndisplay(FileLink(archive))\n')
    cells.append(cell('code',export))
    return {'cells':cells,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
        'language_info':{'name':'python'},'vlmbench_workflow':'team_pilot_v1'},'nbformat':4,'nbformat_minor':5}


if __name__=='__main__':
    root=Path(__file__).resolve().parents[1]
    for platform in ['colab','kaggle']:
        (root/f'notebooks/pilot_{platform}.ipynb').write_text(json.dumps(generate(platform),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
