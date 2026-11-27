# Setup chung
Dùng `project/scripts/setup_inference.py` và `requirements-inference.lock.txt` hiện có.
Giữ package pins; không cài đè CUDA driver của cloud host. Baseline dùng Python 3.12,
setup script hiện nhận 3.11–3.13; từng môi trường vẫn cần kiểm package compatibility.
Venv `.venv-cloud/` ngoài Git, project cài editable.

Restore 783 approved main images + hai raw source inputs bằng
`scripts/main_team_bundle.py`; kiểm source bindings/checksums trước ghi.
File khác bytes sẽ bị từ chối. Model weights/token không nằm trong bundle.
TV2/TV3 hoàn thiện platform setup và xác minh environment thật bằng evidence.
