"""RePOPE VI proposals; neither vocabulary reuse nor drafting creates approval."""
from .translate import QUESTION_PATTERN


def propose_repope(rows, *, pilot_dictionary, extras):
    phrases={}
    for word,item in pilot_dictionary.items():
        if item['status']=='rejected':continue
        phrases[word]={'phrase':' '.join(x for x in (item.get('classifier_vi',''),item['object_vi']) if x),
                       'origin':'existing_pilot_dictionary','dictionary_status':item['status']}
    for word,phrase in extras['phrases'].items():
        if not isinstance(phrase,str) or not phrase.strip():raise ValueError('Draft noun phrase cannot be blank')
        if word in phrases:raise ValueError('New proposals cannot silently override the pilot dictionary')
        phrases[word]={'phrase':phrase,'origin':'assistant_draft','dictionary_status':'pending'}
    result=[]
    for row in rows:
        if row.source_dataset!='repope' or row.task!='object_existence':raise ValueError('RePOPE object-existence only')
        match=QUESTION_PATTERN.fullmatch(row.question_en)
        word=match.group('object') if match else None
        entry=phrases.get(word)
        question=f"Trong ảnh có {entry['phrase']} nào không?" if entry else ''
        result.append({'sample_id':row.sample_id,'question_en':row.question_en,'object_en':word,
            'question_vi':question,'translation_status':'requires_review' if question else 'missing',
            'origin':entry['origin'] if entry else 'unmapped','dictionary_status':entry['dictionary_status'] if entry else 'missing',
            'review_note':extras.get('risk_notes',{}).get(word,''),'human_approval_created':False})
    return result
