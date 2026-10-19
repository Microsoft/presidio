import pytest
import spacy
from presidio_analyzer.nlp_engine import TransformersNlpEngine
from presidio_analyzer.nlp_engine import huggingface_token_pipe as token_pipe_module
from presidio_analyzer.nlp_engine.huggingface_token_pipe import FACTORY_NAME


def test_default_models():
    engine = TransformersNlpEngine()
    assert len(engine.models) > 0
    assert engine.models[0]["lang_code"] == "en"
    assert isinstance(engine.models[0]["model_name"], dict)


def test_validate_model_params_happy_path():
    model = {
        "lang_code": "en",
        "model_name": {
            "spacy": "en_core_web_sm",
            "transformers": "obi/deid_roberta_i2b2",
        },
    }

    TransformersNlpEngine._validate_model_params(model)


def test_load_adds_internal_hugging_face_pipe(mocker):
    inference = mocker.Mock()
    creator = mocker.patch.object(
        token_pipe_module, "hf_pipeline", return_value=inference
    )
    mocker.patch.object(
        token_pipe_module,
        "_pipeline_device",
        return_value=-1,
    )
    mocker.patch(
        "presidio_analyzer.nlp_engine.transformers_nlp_engine.spacy.load",
        return_value=spacy.blank("en"),
    )
    mocker.patch.object(TransformersNlpEngine, "_enable_gpu")
    mocker.patch.object(TransformersNlpEngine, "_download_spacy_model_if_needed")
    engine = TransformersNlpEngine(
        models=[
            {
                "lang_code": "en",
                "model_name": {
                    "spacy": "en_core_web_sm",
                    "transformers": "test-model",
                },
            }
        ]
    )

    engine.load()

    assert engine.nlp["en"].pipe_names == [FACTORY_NAME]
    creator.assert_called_once()
    assert creator.call_args.kwargs["model"] == "test-model"


@pytest.mark.parametrize(
    "key",
    [("lang_code"), ("model_name"), ("model_name.spacy"), ("model_name.transformers")],
)
def test_validate_model_params_missing_fields(key):
    model = {
        "lang_code": "en",
        "model_name": {
            "spacy": "en_core_web_sm",
            "transformers": "obi/deid_roberta_i2b2",
        },
    }
    keys = key.split(".")
    if len(keys) == 1:
        del model[keys[0]]
    else:
        del model[keys[0]][keys[1]]

    with pytest.raises(ValueError):
        TransformersNlpEngine._validate_model_params(model)
