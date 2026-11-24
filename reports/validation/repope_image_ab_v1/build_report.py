"""Build the diagnostic report from verified real metrics and a reviewed recommendation."""
import json
import re
from pathlib import Path

FOLDER=Path(__file__).resolve().parent


def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|',
        *['| '+' | '.join(str(x) for x in row)+' |' for row in rows]])


def build():
    first=json.loads((FOLDER/'phase1_metrics.json').read_text(encoding='utf-8'))
    final=json.loads((FOLDER/'metrics.json').read_text(encoding='utf-8'))
    choice=json.loads((FOLDER/'recommendation.json').read_text(encoding='utf-8'))
    software=json.loads((FOLDER/'software_checks.json').read_text(encoding='utf-8'))
    tested=re.search(r'(\d+) passed in ([0-9.]+)s',software['stdout'])
    stable=sum(len(r['unique_parsed_responses'])==1 and r['valid']==r['excluded_repeats'] for r in final['warmup_stability'])
    branches=table(['Model','Nhánh','Cells','Đúng','Valid','Latency p50 / p95 ms','Peak allocated / reserved MiB'],[
        [r['model'],r['branch'],r['n'],r['correct'],r['valid'],
         f"{r['latency_p50_ms']:.1f} / {r['latency_p95_ms']:.1f}",
         f"{r['peak_allocated_mib']:.1f} / {r['peak_reserved_mib']:.1f}"] for r in final['branch_summary']])
    predictions=table(['Model','Ngôn ngữ','Cặp valid','Flips','A đúng → B sai','A sai → B đúng'],[
        [r['model'],r['language'],r['jointly_valid_AB'],r['prediction_flips'],r['A_correct_B_incorrect'],r['A_incorrect_B_correct']]
        for r in final['AB_comparisons']])
    consistency=table(['Model','Four-way valid','EN–VI bất đồng A','EN–VI bất đồng B','Thay đổi B−A'],[
        [r['model'],r['four_way_valid'],r['A_disagreements'],r['B_disagreements'],r['change_B_minus_A']]
        for r in final['EN_VI_consistency']])
    language=table(['Model','Language','Branch','Correct / expected','Invalid / failed / missing','p50 / p95 ms'],[
        [r['model'],r['language'],r['branch'],f"{r['correct']} / {r['expected']}",
         f"{r['invalid']} / {r['failed']} / {r['missing']}",f"{r['latency_p50_ms']:.1f} / {r['latency_p95_ms']:.1f}"]
        for r in final['metrics']])
    text=f'''# GPU RePOPE image A B diagnostic

Ngày 24/11/2026. Hạn thuyết trình 03/12/2026.
**Mode: REPOPE_ONLY_DIAGNOSTIC. Đây không phải validation bốn task hoặc M3.**

## Kết quả thực và phạm vi

Phase 1 đã đo {first['recorded']}/48 cells trên 6 ảnh QA-approved, cộng
{first['warmup_generations']} warm-up riêng. Hai model load/generate/parse đạt,
không OOM. Phase 2 tái sử dụng 48 cells tương thích, đo thêm 192 cells trên
24 ảnh còn lại. Tổng {final['recorded']}/240 measured cells, missing={final['missing']},
{final['warmup_generations']} warm-up qua hai phase; không cộng lại Phase 1
thành 288 measured cells. Raw đến từ GPU thật, không có predictions giả.

RTX 3060 Laptop 6 GB, Qwen2.5-VL-3B NF4/FP16 và Gemma 3 4B IT NF4/BF16.
Checkpoint/revisions, prompts, decoding, processor config và ảnh nguồn giữ
nguyên. A RGB→thumbnail512 LANCZOS→processor, B RGB→processor.
Qwen giữ min/max pixel 200.704/401.408; Gemma vẫn no-pan-and-scan và processor
896×896, nên B không phải thử nghiệm bỏ mọi giới hạn/default processor.
Cùng model/processor instance trong mỗi phase; mỗi phase/model warm-up hai lượt mỗi nhánh,
AB/BA theo thứ tự toàn pool cố định. Không tự fallback precision hoặc đổi model.

## Tính hợp lệ và gates

30 ảnh được bind theo hash manifest QA lịch sử, human QA JSON/import events,
row hashes và source annotation cache đúng revision. So source question/label
bằng auditor offline hiện có; kiểm SHA256 ảnh, registry pilot exclusions và
main ID/hash exclusions. Chọn sáu mẫu cân bằng category×label trước outputs.
Không sửa dataset, ground truth, review JSON, main configs hoặc pilot cũ.

Mode full vẫn đòi 30 mẫu/bốn task/human QA/provenance/exclusions như trước.
Diagnostic dùng gates riêng trên pool RePOPE đã approved; thiếu ba task chỉ
được miễn trong mode này, không biến full validation thành đạt.

| Gate | Trạng thái | Còn thiếu |
|---|---|---|
| M1 | IN_PROGRESS | 1.000 main vẫn chờ human review/import đầy đủ |
| M2 | PENDING | Nhóm chốt preprocessing/protocol; frozen=false, chưa receipt |
| M3 | NOT_RUN | Main GPU smoke bốn task sau M1/M2; diagnostic này không hoàn thành M3 |

## Prediction và consistency

{predictions}

Flips và correctness transitions chỉ trên cùng cặp A/B đều valid. Accuracy
nhỏ bên dưới chỉ mô tả subset, không dùng để chọn nhánh tối đa hóa điểm.

{consistency}

Denominator consistency là cùng tập EN-A/VI-A/EN-B/VI-B đều valid.

## Latency và bộ nhớ

{branches}

{language}

Latency đo chung từ verify hash/đọc/decode/RGB/thumbnail qua processor,
generate, decode/diagnostics và synchronize. Loại model load, warm-up và
checkpoint write. Một repeat; p50/p95 mô tả run hiện tại, không claim chênh
lệch có ý nghĩa thống kê. Không dùng timer này để xếp tốc độ hai model vì
Gemma adapter có thêm logits diagnostics.

Peak allocated/reserved là số đo allocator PyTorch, không phải residency
VRAM vật lý. Gemma reserved có thể lớn hơn capacity 6.144 MiB được driver
báo; không suy thành model chỉ dùng dedicated VRAM hoặc chắc chắn phù hợp
mọi ảnh. Chưa đo shared memory/paging. Cần main smoke bốn task riêng.
Warm-up/order/thermal/cache giữa phase có thể ảnh hưởng timing và reserved.
Warm-up trên cùng một ảnh anchor có {stable}/4 nhóm model×branch giữ cùng
parsed response qua các repeats/phases; kiểm tra này không chứng minh tính
deterministic của toàn bộ 30 ảnh.

## Recommendation

**{choice['recommendation']}**

{choice['reason']}

{choice['limits']}

Nếu nhóm đồng ý đổi policy, tạo version/hashes/protocol receipt mới theo
quy trình. Không có main config nào được đổi hoặc tự freeze trong phiên này.
Thứ tự ưu tiên vẫn main human QA → protocol freeze → main GPU smoke → main
inference. Validation bốn task/supplement 24 mẫu là việc riêng, không còn
chặn mọi diagnostic. Không mở RQ3/RQ4, branch C hoặc training.

## Provenance và tái sử dụng

Fingerprint chung `{final['config_fingerprint']}` bind source/QA/input/settings/
implementation; selection/phase ghi riêng. Phase 2 kiểm đủ Phase 1 của cả
hai model và từ chối invalid/failed/missing. Trước generation mới, đối chiếu
environment packages/GPU, code state, settings/prompt snapshots và processor
identity. Mỗi cell giữ row/image/prompt hashes và runtime fingerprint riêng.
`reuse.json` bind SHA256 predictions/metadata Phase 1; analyzer kiểm lại các
hashes, không trộn runtime không tương thích. Một mẫu chỉ được tính một lần.

Run dùng HEAD `0a910e6` với `code_dirty=true` vì harness diagnostic chưa commit
lúc bắt đầu đo; không gán ngược commit công bố sau đó vào raw. Fingerprint
bind bytes implementation đang chạy, receipts giữ hashes để đối chiếu code
được công bố. Settings snapshot là candidate config chung; field branch A/B
quyết định có thumbnail, không sửa YAML giữa hai nhánh. Không chạy software
suite hay tác vụ GPU khác đồng thời với lượt đo; đây vẫn là laptop/one repeat,
không phải môi trường throughput benchmark được cô lập hoàn toàn.

Raw và metadata local ở `results/pilot/repope_image_ab_v1/phase1/` và
`phase2/`; mỗi thư mục có qwen/gemma. Danh mục/hash raw ở
[metrics.json](metrics.json), [Phase 1 metrics](phase1_metrics.json).
ZIP riêng không ảnh/weights: `exports/repope_image_ab_diagnostic_v1.zip`.
Không copy raw giả trong unit tests vào evidence GPU.

```powershell
$env:HF_HOME = "$PWD/.cache/huggingface"
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py run --mode repope-diagnostic --size 6 --model qwen --output results/pilot/repope_image_ab_v1/phase1/qwen --execute
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py run --mode repope-diagnostic --size 6 --model gemma --output results/pilot/repope_image_ab_v1/phase1/gemma --execute
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py run --mode repope-diagnostic --size 30 --phase1 results/pilot/repope_image_ab_v1/phase1 --model qwen --output results/pilot/repope_image_ab_v1/phase2/qwen --execute
.venv-infer/Scripts/python.exe scripts/validate_image_ab.py run --mode repope-diagnostic --size 30 --phase1 results/pilot/repope_image_ab_v1/phase1 --model gemma --output results/pilot/repope_image_ab_v1/phase2/gemma --execute
.venv/Scripts/python.exe reports/validation/repope_image_ab_v1/analyze_diagnostic.py --size 30 --output reports/validation/repope_image_ab_v1/metrics_rerun.json
```

Chọn namespace mới cho rerun, không ghi đè run/evidence hiện có; dùng cùng
phase1 parent khi mở rộng. Code/source fingerprint phải khớp.
Nếu rerun trong namespace khác, truyền --run-root tương ứng cho analyzer.
Checkout đúng version code/inputs đã bind hashes khi tái phân tích lịch sử;
không bỏ kiểm hash để ghép run sau khi protocol/data thay đổi. Tests và
preservation receipt nằm trong thư mục report; commands ở đây là các lệnh
run thực của phiên này. CPU synthetic tests kiểm gates và reuse, không thay
bằng chứng load/generate GPU. Các reports v1 giữ nguyên như lịch sử trước
khi người dùng cho phép RePOPE-only.

## Source code tests và bảo toàn

- [repope_diagnostic.py](../../../src/vlmbench/repope_diagnostic.py): gates riêng,
  source/QA binding, selection và reuse kiểm tương thích.
- [image_ab.py](../../../src/vlmbench/image_ab.py): tái sử dụng instrumentation
  sau gates riêng; full mode vẫn giữ điều kiện bốn task và từ chối diagnostic plan.
- [CLI](../../../scripts/validate_image_ab.py): thêm --mode repope-diagnostic,
  --size và --phase1; mode mặc định vẫn full.
- [Tests](../../../tests/test_image_ab.py): thêm 7 tests diagnostic, tổng27
  A/B tests. Full suite thực **{tested[1]} passed/{tested[2]} s** sau khi GPU
  measurement đã kết thúc. [stdout/checks](software_checks.json),
  [JUnit](software_tests.xml); fake torch/reviewers chỉ trong pytest tmp.
- [Preservation](preservation.json): 813 ảnh khớp hash, main configs/data/
  review JSON và legacy runners/history giữ nguyên. [Raw ZIP receipt](raw_bundle.json).
- Helpers analyze_diagnostic.py/build_report.py trong thư mục này tái tạo
  bảng/report từ raw đã kiểm provenance. README/completion ghi trạng thái mới.
'''
    (FOLDER/'report.md').write_text(text,encoding='utf-8',newline='\n')
    print('Built report from verified real GPU metrics')


if __name__=='__main__':build()
