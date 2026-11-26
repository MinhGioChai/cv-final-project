"""Readable case index and private original-JPEG HTML; never records review decisions."""
import base64
import csv
from html import escape
import io
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from vlmbench.io_utils import atomic_bytes,sha256_file,write_json

TITLES={
    'agreed_observation_differs_from_source':'A/B cùng quan sát khác nhãn nguồn',
    'observation_disagreement':'A/B quan sát khác nhau',
    'rereview_after_translation_change':'A cần duyệt lại bản dịch cuối',
    'translation_disagreement_or_incomplete':'Dịch chưa đồng thuận hoặc còn pending',
    'image_qa_disagreement_or_incomplete':'Ảnh/nhãn còn pending hoặc chưa đồng thuận',
}


def main():
    folder=Path(__file__).resolve().parent
    cases=json.loads((folder/'needs_resolution.json').read_text(encoding='utf-8'))['cases']
    summary=json.loads((folder/'aggregation.json').read_text(encoding='utf-8'))
    csv_path=folder/'needs_resolution.csv';html_path=ROOT/'exports/main_review_resolution_v1.html'
    receipt=folder/'resolution_report.json'
    if any(p.exists() for p in (csv_path,html_path,receipt)):
        raise ValueError('Preserve previous report; use a new version')
    fields=['packet','sample_id','dataset','issue','question_en','question_vi_original','question_vi_final',
        'source_ground_truth','A_id','A_translation','A_image_qa','A_observation','A_translation_notes','A_image_notes',
        'B_id','B_translation','B_image_qa','B_observation','B_translation_notes','B_image_notes','action','review_path']
    buffer=io.StringIO(newline='');writer=csv.DictWriter(buffer,fieldnames=fields);writer.writeheader()
    cards=[]
    for index,c in enumerate(cases,1):
        d=c['decision'];record={k:c[k] for k in ['packet','sample_id','dataset','question_en','question_vi_original',
            'question_vi_final','source_ground_truth','action','review_path']}
        record['issue']=TITLES.get(c['primary_issue'],c['primary_issue'])
        human=[]
        for slot,label in [('reviewer_a','A'),('reviewer_b','B')]:
            r=d[slot]
            record.update({label+'_id':r['translation']['reviewer_id'] or r['image_qa']['reviewer_id'],
                label+'_translation':r['translation']['status'],label+'_image_qa':r['image_qa']['status'],
                label+'_observation':r['image_qa']['observed_answer'],label+'_translation_notes':r['translation']['notes'],
                label+'_image_notes':r['image_qa']['notes']})
            human.append(f'<tr><th>{label}: {escape(record[label+"_id"])}</th>'
                f'<td>Dịch: {escape(r["translation"]["status"])}<br>Ảnh/nhãn: {escape(r["image_qa"]["status"])}</td>'
                f'<td>Quan sát: <b>{escape(r["image_qa"]["observed_answer"])}</b></td>'
                f'<td>Dịch: {escape(r["translation"]["notes"])}<br>Ảnh: {escape(r["image_qa"]["notes"])}</td></tr>')
        writer.writerow(record)
        path=ROOT/c['image_path'];assert sha256_file(path)==c['image_sha256']
        encoded=base64.b64encode(path.read_bytes()).decode('ascii')
        cards.append(f'<article id="{escape(c["sample_id"])}"><h2>{index}. {escape(c["packet"])} — {escape(c["sample_id"])}</h2>'
            f'<p class="issue">{escape(record["issue"])}</p><img src="data:image/jpeg;base64,{encoded}" alt="Ảnh nguồn của mẫu cần đối soát">'
            f'<p><b>EN:</b> {escape(c["question_en"])}</p><p><b>VI gốc:</b> {escape(c["question_vi_original"])}</p>'
            f'<p><b>VI cuối:</b> {escape(c["question_vi_final"])}</p><p><b>Nhãn nguồn giữ nguyên:</b> {escape(str(c["source_ground_truth"]))}</p>'
            '<table><thead><tr><th>Người duyệt</th><th>Trạng thái</th><th>Quan sát</th><th>Ghi chú nguyên văn</th></tr></thead><tbody>'
            +''.join(human)+'</tbody></table>'+f'<p><b>Việc cần làm:</b> {escape(c["action"])}</p>'
            f'<p><a href="../reports/stage1/v12/main_review/{escape(c["packet"])}.html">Mở gói review v2</a> · '
            f'<a href="../{escape(c["review_path"])}">JSON đã nộp của gói</a></p>'
            '<p>Mở gói v2, nạp JSON đã nộp, tìm đúng sample ID. Chỉ người thật ghi quyết định của mình; tải JSON mới sang version/thư mục mới. Trang này chỉ để đối soát, không lưu approval.</p></article>')
    head='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Đối soát 28 mẫu main sau review</title><style>body{font:17px/1.55 system-ui,sans-serif;max-width:1100px;margin:auto;padding:24px;background:#f7f8fa;color:#17202a}article{background:white;padding:22px;margin:24px 0;border:1px solid #ccd3da;border-radius:8px}h1,h2{line-height:1.3}h2{font-size:21px;overflow-wrap:anywhere}img{display:block;max-width:100%;height:auto;max-height:650px;object-fit:contain;margin:16px auto}table{border-collapse:collapse;width:100%}th,td{border:1px solid #c9ced4;padding:10px;vertical-align:top;text-align:left;overflow-wrap:anywhere}p{white-space:pre-wrap}.issue{font-weight:bold;color:#8b3900}a{color:#174ea6}@media print{article{break-before:page;border:0}body{background:white}}</style>
<h1>Đối soát các mẫu main chưa đạt sau review</h1>
<p>18 JSON/840 mẫu đã được kiểm và import; cộng160 Pet là972/1000 mẫu đạt. Còn28 mẫu giữ pending/rejected, không bị loại khỏi main. Ảnh dưới đây nhúng nguyên JPEG nguồn; trang chỉ hiển thị, không thay đổi dữ liệu.</p>
<p>A/B cùng phản đối nhãn chưa có nghĩa nhãn mới đã được phê duyệt. Không tự sửa ground truth, đổi EN hoặc khôi phục approval trong history. Nếu B đã áp dụng góp ý dịch của A, A vẫn cần duyệt bản cuối khi lượt hiện tại pending. Cần sửa nhãn nguồn: ghi đề xuất riêng và chốt quy trình/version trước freeze.</p>'''
    atomic_bytes(csv_path,buffer.getvalue().encode('utf-8-sig'))
    atomic_bytes(html_path,(head+''.join(cards)+'</html>').encode('utf-8'))
    write_json(receipt,{'rows':len(cases),'CSV':csv_path.relative_to(ROOT).as_posix(),'csv_sha256':sha256_file(csv_path),
        'private_HTML':html_path.relative_to(ROOT).as_posix(),'html_sha256':sha256_file(html_path),
        'image_policy':'original JPEG bytes embedded without resampling; display scaling only',
        'human_decisions_created':0,'image_sources_modified':False,'accepted_total':summary['accepted_total']})
    print(json.dumps({'cases':len(cases),'CSV':str(csv_path),'HTML':str(html_path)}))


if __name__=='__main__':main()
