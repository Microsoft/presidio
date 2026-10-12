from presidio_anonymizer.entities import PIIEntity


def test_pii_entity_repr_includes_score_when_present():
    entity = PIIEntity(start=0, end=5, entity_type="PERSON")
    entity.score = 0.85
    result = repr(entity)
    assert "score: 0.85" in result
    assert "start: 0" in result
    assert "entity_type: PERSON" in result


def test_pii_entity_repr_omits_score_when_absent():
    entity = PIIEntity(start=0, end=5, entity_type="PERSON")
    result = repr(entity)
    assert "score" not in result
    assert "start: 0" in result