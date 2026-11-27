# File ownership

| File dự kiến | Owner |
|---|---|
| `scripts/run_main.py` | TV1 |
| `src/vlmbench/baseline_runtime.py` | TV1 |
| `src/vlmbench/baseline_contract.py` | TV1 |
| `scripts/team_assignment.py` | TV1 |
| `tests/test_main_sharding.py` | TV1 |
| `notebooks/main_kaggle_starter.ipynb` | TV2 |
| `scripts/cloud/kaggle_main.py` | TV2 |
| `tests/test_kaggle_main.py` | TV2 |
| `docs/team_inference_v1/shared/guides/KAGGLE.md` | TV2 |
| `notebooks/main_colab_starter.ipynb` | TV3 |
| `scripts/cloud/colab_main.py` | TV3 |
| `scripts/cloud/gpu_compatibility.py` | TV3 |
| `tests/test_colab_main.py` | TV3 |
| `docs/team_inference_v1/shared/guides/COLAB.md` | TV3 |
| `scripts/export_main_results.py` | TV4 |
| `scripts/collect_main_shards.py` | TV4 |
| `tests/test_main_collection.py` | TV4 |
| `docs/team_inference_v1/shared/guides/RECOVERY.md` | TV4 |

TV5 sở hữu integration docs/bundler/assignment contracts/release metadata;
TV1 sở hữu core runner/sharding. TV2/TV3 trao đổi trước khi sửa setup_inference.py
hoặc requirements lock chung. Data/GT/reviews/modelpins/frozenv1 artifacts không
thuộc phạm vi chỉnh sửa của bốn PR. Không gán CODEOWNERS giả khi chưa biết GitHub IDs.
