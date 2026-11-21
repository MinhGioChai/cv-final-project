"""Source-bound assistant proposals; all new sentences remain unapproved."""
import re


def propose_vsr(rows, nouns, glossary):
    nouns={**nouns,**glossary['extra_nouns']}
    result=[]
    for row in rows:
        relation=row.category
        # Explicit source grammar: never infer direction or truth from a label.
        verb='' if relation in {'contains','consists of','has as a part'} else 'is '
        pattern=r'The (.+) '+re.escape(verb+relation)+r' the (.+)\.'
        match=re.fullmatch(pattern,row.question_en)
        if not match or relation not in glossary['relations']:
            raise ValueError('Unmapped VSR source grammar/relation')
        subject,object_=match.groups()
        if subject not in nouns or object_ not in nouns:
            raise ValueError('Unmapped VSR noun')
        text=f"{nouns[subject]} {glossary['relations'][relation]} {nouns[object_]}."
        text=text[0].upper()+text[1:]
        result.append({'sample_id':row.sample_id,'question_en':row.question_en,'question_vi':text,
            'source_record_sha256':row.source_record_sha256,'translation_status':'requires_review',
            'relation':relation,'review_note':glossary['review_note'] if relation in glossary['risk_relations'] else '',
            'human_approval_created':False})
    return result


def propose_tallyqa(rows, lines, *, expected_selection_sha256, actual_selection_sha256):
    if actual_selection_sha256!=expected_selection_sha256 or len(rows)!=len(lines):
        raise ValueError('Draft lines belong to a different exact selection/order')
    result=[]
    risks={7:'trunks đa nghĩa: bản nháp đang dùng vòi; cần đối chiếu nghĩa với ảnh.',
        10:'Nguồn viết bolders; bản nháp diễn giải là boulders/tảng đá, cần xác nhận.',
        20:'Giữ điều kiện visible lights; câu nguồn thiếu tự nhiên.',
        21:'Giữ flying man theo nguồn, không sửa sự kiện vì có vẻ bất thường.',
        27:'Nguồn motors được diễn giải là xe máy; cần kiểm tra.',
        52:'ox thường là bò đực thiến/bò kéo; kiểm tra thuật ngữ và đối tượng.',
        74:'toppings có thể là loại hoặc từng miếng; bản nháp dùng loại, cần xác nhận đơn vị đếm.',
        79:'each team: kiểm tra có số lượng thống nhất cho mỗi đội.',
        106:'Nguồn motors và cấu trúc the right of thiếu tự nhiên; kiểm tra ngữ nghĩa.',
        110:'tie dye là kiểu nhuộm loang, không phải cà vạt.',
        115:'Câu nguồn sai ngữ pháp; bản nháp giữ ý ánh nắng chiếu vào người.'}
    for i,(row,text) in enumerate(zip(rows,lines)):
        if not text.strip():raise ValueError('Empty VI proposal')
        result.append({'sample_id':row.sample_id,'question_en':row.question_en,'question_vi':text,
            'source_record_sha256':row.source_record_sha256,'translation_status':'requires_review',
            'review_note':risks.get(i,''),'human_approval_created':False})
    return result
