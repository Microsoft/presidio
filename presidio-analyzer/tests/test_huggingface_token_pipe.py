import logging
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import spacy
from presidio_analyzer.nlp_engine import huggingface_token_pipe as token_pipe_module
from presidio_analyzer.nlp_engine.huggingface_token_pipe import (
    FACTORY_NAME,
    HuggingFaceTokenPipe,
)


@pytest.mark.parametrize(
    ("device_type", "device_index", "expected"),
    [("cpu", None, -1), ("cuda", None, 0), ("cuda", 2, 2)],
)
def test_pipeline_device(mocker, device_type, device_index, expected):
    mocker.patch.object(
        token_pipe_module,
        "get_torch_default_device",
        return_value=SimpleNamespace(type=device_type, index=device_index),
    )

    assert token_pipe_module._pipeline_device() == expected


def test_factory_builds_token_classification_pipeline(mocker):
    inference = Mock(return_value=[])
    creator = mocker.patch.object(
        token_pipe_module, "hf_pipeline", return_value=inference
    )
    mocker.patch.object(
        token_pipe_module,
        "get_torch_default_device",
        return_value=SimpleNamespace(type="cuda", index=1),
    )
    nlp = spacy.blank("en")

    nlp.add_pipe(
        FACTORY_NAME,
        config={
            "model": "test-model",
            "revision": "model-revision",
            "stride": 8,
            "aggregation_strategy": "simple",
            "alignment_mode": "strict",
            "spans_key": "entities",
            "pipeline_kwargs": {"trust_remote_code": False},
        },
    )

    creator.assert_called_once_with(
        task="token-classification",
        model="test-model",
        revision="model-revision",
        stride=8,
        aggregation_strategy="simple",
        device=1,
        trust_remote_code=False,
    )


def test_factory_omits_none_stride(mocker):
    creator = mocker.patch.object(token_pipe_module, "hf_pipeline", return_value=Mock())
    mocker.patch.object(
        token_pipe_module,
        "get_torch_default_device",
        return_value=SimpleNamespace(type="cpu", index=None),
    )

    spacy.blank("en").add_pipe(
        FACTORY_NAME, config={"model": "test-model", "stride": None}
    )

    assert "stride" not in creator.call_args.kwargs


def test_factory_requires_transformers(mocker):
    mocker.patch.object(token_pipe_module, "hf_pipeline", None)

    with pytest.raises(ImportError, match=r"presidio-analyzer\[transformers\]"):
        spacy.blank("en").add_pipe(FACTORY_NAME, config={"model": "test-model"})


def test_factory_requires_model():
    with pytest.raises(ValueError, match="model is required"):
        spacy.blank("en").add_pipe(FACTORY_NAME)


def test_single_document_predictions_are_scored_spans():
    inference = Mock(
        return_value=[
            {
                "entity_group": "PER",
                "start": 11,
                "end": 14,
                "score": 0.98,
            }
        ]
    )
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=inference,
        alignment_mode="strict",
        spans_key="entities",
    )

    doc = pipe(spacy.blank("en").make_doc("my name is Dan"))

    assert [(span.text, span.label_) for span in doc.spans["entities"]] == [
        ("Dan", "PER")
    ]
    assert doc.spans["entities"].attrs["scores"] == [0.98]


def test_batch_predictions_remain_with_their_documents():
    inference = Mock(
        return_value=[
            [{"entity_group": "PER", "start": 0, "end": 3, "score": 0.98}],
            [{"entity_group": "ORG", "start": 0, "end": 6, "score": 0.92}],
        ]
    )
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=inference,
        alignment_mode="strict",
        spans_key="entities",
    )
    nlp = spacy.blank("en")

    docs = list(pipe.pipe(map(nlp.make_doc, ["Dan", "GitHub"]), batch_size=2))

    assert [doc.spans["entities"][0].text for doc in docs] == ["Dan", "GitHub"]
    assert [doc.spans["entities"].attrs["scores"] for doc in docs] == [
        [0.98],
        [0.92],
    ]
    inference.assert_called_once_with(["Dan", "GitHub"])


def test_batch_failure_retries_individually_without_logging_text(caplog):
    secret = "Sharon secret"
    inference = Mock(
        side_effect=[
            RuntimeError(secret),
            [{"entity_group": "PER", "start": 0, "end": 6, "score": 0.98}],
            [],
        ]
    )
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=inference,
        alignment_mode="strict",
        spans_key="entities",
    )
    nlp = spacy.blank("en")
    caplog.set_level(logging.WARNING, logger="presidio-analyzer")

    docs = list(pipe.pipe(map(nlp.make_doc, ["Sharon", "public"]), batch_size=2))

    assert docs[0].spans["entities"][0].text == "Sharon"
    assert not docs[1].spans["entities"]
    assert "RuntimeError" in caplog.text
    assert secret not in caplog.text


def test_individual_failures_are_isolated_without_logging_text(caplog):
    batch_secret = "batch secret"
    document_secret = "document secret"
    inference = Mock(
        side_effect=[
            RuntimeError(batch_secret),
            RuntimeError(document_secret),
            [],
        ]
    )
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=inference,
        alignment_mode="strict",
        spans_key="entities",
    )
    nlp = spacy.blank("en")
    caplog.set_level(logging.WARNING, logger="presidio-analyzer")

    docs = list(pipe.pipe(map(nlp.make_doc, ["private", "public"]), batch_size=2))

    assert not docs[0].spans["entities"]
    assert not docs[1].spans["entities"]
    assert "RuntimeError" in caplog.text
    assert batch_secret not in caplog.text
    assert document_secret not in caplog.text


def test_single_document_failure_adds_empty_spans(caplog):
    secret = "private text"
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=Mock(side_effect=RuntimeError(secret)),
        alignment_mode="strict",
        spans_key="entities",
    )
    caplog.set_level(logging.WARNING, logger="presidio-analyzer")

    doc = pipe(spacy.blank("en").make_doc(secret))

    assert not doc.spans["entities"]
    assert "RuntimeError" in caplog.text
    assert secret not in caplog.text


def test_batch_output_count_must_match_documents():
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=Mock(return_value=[]),
        alignment_mode="strict",
        spans_key="entities",
    )
    nlp = spacy.blank("en")

    with pytest.raises(ValueError, match="output count"):
        list(pipe.pipe(map(nlp.make_doc, ["one", "two"]), batch_size=2))


@pytest.mark.parametrize("output", [None, {}, ["invalid"]])
def test_pipeline_output_must_be_prediction_mappings(output):
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=Mock(return_value=output),
        alignment_mode="strict",
        spans_key="entities",
    )

    with pytest.raises(TypeError, match="list of mappings"):
        pipe(spacy.blank("en").make_doc("text"))


def test_unaligned_and_overlapping_predictions_are_skipped(caplog):
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=Mock(
            return_value=[
                {"entity_group": "PER", "start": 0, "end": 5, "score": 0.9},
                {"entity_group": "PER", "start": 1, "end": 5, "score": 0.8},
                {"entity_group": "ORG", "start": 6, "end": 8, "score": 0.7},
            ]
        ),
        alignment_mode="strict",
        spans_key="entities",
    )
    caplog.set_level(logging.WARNING, logger="presidio-analyzer")

    doc = pipe(spacy.blank("en").make_doc("Alice works"))

    assert [span.text for span in doc.spans["entities"]] == ["Alice"]
    assert doc.spans["entities"].attrs["scores"] == [0.9]
    assert caplog.text.count("Skipping unaligned or overlapping prediction") == 2
    assert "Alice" not in caplog.text


def test_malformed_prediction_error_does_not_include_values():
    secret = "private text"
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=Mock(return_value=[{"word": secret}]),
        alignment_mode="strict",
        spans_key="entities",
    )

    with pytest.raises(ValueError, match=r"keys=\['word'\]") as error:
        pipe(spacy.blank("en").make_doc(secret))

    assert secret not in str(error.value)


@pytest.mark.parametrize("score", [None, "private score"])
def test_prediction_requires_numeric_score(score):
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=Mock(
            return_value=[
                {
                    "entity_group": "PER",
                    "start": 0,
                    "end": 5,
                    "score": score,
                }
            ]
        ),
        alignment_mode="strict",
        spans_key="entities",
    )

    with pytest.raises(ValueError, match="numeric score") as error:
        pipe(spacy.blank("en").make_doc("Alice"))

    assert str(score) not in str(error.value)


def test_serialization_rebuilds_pipeline_from_config(tmp_path):
    pipe = HuggingFaceTokenPipe(
        name=FACTORY_NAME,
        pipeline=Mock(),
        alignment_mode="strict",
        spans_key="entities",
    )

    assert pipe.to_bytes() == b""
    assert pipe.from_bytes(b"serialized") is pipe
    assert pipe.to_disk(tmp_path) is None
    assert pipe.from_disk(tmp_path) is pipe
