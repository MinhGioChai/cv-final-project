from types import SimpleNamespace

import pytest

from vlmbench.main_translations import propose_repope


def row(question='Is there a bowl in the image?'):
    return SimpleNamespace(sample_id='synthetic_test_only',source_dataset='repope',task='object_existence',question_en=question)


def test_existing_classifier_preserved_but_question_never_auto_approved():
    dictionary={'bowl':{'object_vi':'bát','classifier_vi':'cái','status':'approved'}}
    proposal=propose_repope([row()],pilot_dictionary=dictionary,extras={'phrases':{}})[0]
    assert proposal['question_vi']=='Trong ảnh có cái bát nào không?'
    assert proposal['dictionary_status']=='approved' and proposal['translation_status']=='requires_review'
    assert not proposal['human_approval_created']


def test_new_vocabulary_is_pending_with_risk_note():
    result=propose_repope([row('Is there a snowboard in the image?')],pilot_dictionary={},
        extras={'phrases':{'snowboard':'chiếc ván trượt tuyết đơn'},'risk_notes':{'snowboard':'synthetic_test_only review'}})[0]
    assert result['dictionary_status']=='pending' and result['review_note']=='synthetic_test_only review'
    assert result['translation_status']=='requires_review'


def test_unknown_object_or_pattern_stays_missing():
    for question in ('Is there a mystery in the image?','Can you see a bowl?'):
        result=propose_repope([row(question)],pilot_dictionary={},extras={'phrases':{}})[0]
        assert result['question_vi']=='' and result['translation_status']=='missing'


def test_new_glossary_cannot_override_existing_pilot_phrase():
    with pytest.raises(ValueError,match='override'):
        propose_repope([row()],pilot_dictionary={'bowl':{'object_vi':'bát','classifier_vi':'cái','status':'approved'}},
                       extras={'phrases':{'bowl':'synthetic_test_only replacement'}})


def test_rejected_dictionary_does_not_silently_supply_translation():
    result=propose_repope([row()],pilot_dictionary={'bowl':{'object_vi':'wrong','status':'rejected'}},extras={'phrases':{}})[0]
    assert result['translation_status']=='missing'
