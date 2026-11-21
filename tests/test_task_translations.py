import pytest

from vlmbench.datasets.candidates import candidate
from vlmbench.task_translations import propose_vsr,propose_tallyqa


def source(text,relation='left of',truth='yes'):
    return candidate(dataset='vsr',split='test',revision='a'*40,row_id='1',record={},namespace='coco',
        image_id='1',image_ref='source',task='spatial',category=relation,question=text,truth=truth)


def test_spatial_preserves_subject_object_and_does_not_flip_false_label():
    glossary={'extra_nouns':{},'relations':{'left of':'ở bên trái'},'risk_relations':[],'review_note':''}
    rows=[source('The cat is left of the dog.',truth='no')]
    result=propose_vsr(rows,{'cat':'con mèo','dog':'con chó'},glossary)
    assert result[0]['question_vi']=='Con mèo ở bên trái con chó.'
    assert rows[0].ground_truth=='no'
    assert result[0]['translation_status']=='requires_review'


def test_non_copula_spatial_and_risk_note():
    glossary={'extra_nouns':{},'relations':{'contains':'chứa'},'risk_relations':['contains'],'review_note':'check'}
    result=propose_vsr([source('The cup contains the cat.','contains')],{'cat':'con mèo','cup':'cái cốc'},glossary)
    assert result[0]['question_vi']=='Cái cốc chứa con mèo.'
    assert result[0]['review_note']=='check'


@pytest.mark.parametrize('text',['The cat is right of the dog.','The cat is left of the unknown.'])
def test_unmapped_grammar_or_noun_fails(text):
    glossary={'extra_nouns':{},'relations':{'left of':'ở bên trái'},'risk_relations':[],'review_note':''}
    with pytest.raises(ValueError):propose_vsr([source(text)],{'cat':'con mèo','dog':'con chó'},glossary)


def test_tally_order_binding_and_length_required():
    with pytest.raises(ValueError):
        propose_tallyqa([],[],expected_selection_sha256='a',actual_selection_sha256='b')
    with pytest.raises(ValueError):
        propose_tallyqa([source('source')],[],expected_selection_sha256='a',actual_selection_sha256='a')


def test_tally_keeps_negation_and_count_scope_as_authored():
    text='Có bao nhiêu người không đội mũ màu xanh dương?'
    result=propose_tallyqa([source('How many people are not wearing a blue hat?')],[text],
        expected_selection_sha256='a',actual_selection_sha256='a')
    assert result[0]['question_vi']==text and not result[0]['human_approval_created']
