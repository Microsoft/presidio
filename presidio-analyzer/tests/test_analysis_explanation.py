from presidio_analyzer import AnalysisExplanation


def test_when_explanation_created_then_identified_text_is_empty():
    explanation = AnalysisExplanation(recognizer="RecognizerName", original_score=0.5)

    assert explanation.identified_text is None
    assert explanation.to_dict()["identified_text"] is None


def test_when_identified_text_is_set_then_it_is_serialized():
    explanation = AnalysisExplanation(recognizer="RecognizerName", original_score=0.5)

    explanation.set_identified_text("AC432223")

    assert explanation.identified_text == "AC432223"
    assert explanation.to_dict()["identified_text"] == "AC432223"
