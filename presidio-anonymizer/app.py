"""REST API server for anonymizer."""

import json
import logging
import os
from logging.config import fileConfig
from pathlib import Path

from flask import Flask, Response, jsonify, request
from presidio_anonymizer import AnonymizerEngine, DeanonymizeEngine
from presidio_anonymizer.entities import InvalidParamError
from presidio_anonymizer.services.app_entities_convertor import AppEntitiesConvertor
from werkzeug.exceptions import BadRequest, HTTPException

DEFAULT_PORT = "3000"

LOGGING_CONF_FILE = "logging.ini"

WELCOME_MESSAGE = r"""
 _______  _______  _______  _______ _________ ______  _________ _______
(  ____ )(  ____ )(  ____ \(  ____ \\__   __/(  __  \ \__   __/(  ___  )
| (    )|| (    )|| (    \/| (    \/   ) (   | (  \  )   ) (   | (   ) |
| (____)|| (____)|| (__    | (_____    | |   | |   ) |   | |   | |   | |
|  _____)|     __)|  __)   (_____  )   | |   | |   | |   | |   | |   | |
| (      | (\ (   | (            ) |   | |   | |   ) |   | |   | |   | |
| )      | ) \ \__| (____/\/\____) |___) (___| (__/  )___) (___| (___) |
|/       |/   \__/(_______/\_______)\_______/(______/ \_______/(_______)
"""


class Server:
    """Flask server for anonymizer."""

    def __init__(self):
        fileConfig(Path(Path(__file__).parent, LOGGING_CONF_FILE))
        self.logger = logging.getLogger("presidio-anonymizer")
        self.logger.setLevel(os.environ.get("LOG_LEVEL", self.logger.level))
        self.app = Flask(__name__)
        self.logger.info("Starting anonymizer engine")
        self.anonymizer = AnonymizerEngine()
        self.deanonymize = DeanonymizeEngine()
        self.logger.info(WELCOME_MESSAGE)

        @self.app.route("/health")
        def health() -> str:
            """Return basic health probe result."""
            return "Presidio Anonymizer service is up"

        @self.app.route("/anonymize", methods=["POST"])
        def anonymize() -> Response:
            content = request.get_json()
            if not content:
                raise BadRequest("Invalid request json")

            anonymizers_config = AppEntitiesConvertor.operators_config_from_json(
                content.get("anonymizers")
            )
            if AppEntitiesConvertor.check_custom_operator(anonymizers_config):
                raise BadRequest("Custom type anonymizer is not supported")

            text = content.get("text", "")
            if isinstance(text, list):
                results = [
                    self.anonymizer.anonymize(
                        text=item_text,
                        analyzer_results=AppEntitiesConvertor.analyzer_results_from_json(
                            item_analyzer_results
                        ),
                        operators=anonymizers_config,
                    )
                    for item_text, item_analyzer_results in zip(
                        text,
                        _batch_items(
                            "analyzer_results", content.get("analyzer_results"), text
                        ),
                    )
                ]
                return Response(
                    json.dumps(results, default=lambda o: o.__dict__),
                    mimetype="application/json",
                )

            analyzer_results = AppEntitiesConvertor.analyzer_results_from_json(
                content.get("analyzer_results")
            )
            anoymizer_result = self.anonymizer.anonymize(
                text=text,
                analyzer_results=analyzer_results,
                operators=anonymizers_config,
            )
            return Response(anoymizer_result.to_json(), mimetype="application/json")

        @self.app.route("/deanonymize", methods=["POST"])
        def deanonymize() -> Response:
            content = request.get_json()
            if not content:
                raise BadRequest("Invalid request json")
            text = content.get("text", "")
            deanonymize_config = AppEntitiesConvertor.operators_config_from_json(
                content.get("deanonymizers")
            )

            if isinstance(text, list):
                results = [
                    self.deanonymize.deanonymize(
                        text=item_text,
                        entities=AppEntitiesConvertor.deanonymize_entities_from_json(
                            {"anonymizer_results": item_entities}
                        ),
                        operators=deanonymize_config,
                    )
                    for item_text, item_entities in zip(
                        text,
                        _batch_items(
                            "anonymizer_results",
                            content.get("anonymizer_results"),
                            text,
                        ),
                    )
                ]
                return Response(
                    json.dumps(results, default=lambda o: o.__dict__),
                    mimetype="application/json",
                )

            deanonymize_entities = AppEntitiesConvertor.deanonymize_entities_from_json(
                content
            )
            deanonymized_response = self.deanonymize.deanonymize(
                text=text, entities=deanonymize_entities, operators=deanonymize_config
            )
            return Response(
                deanonymized_response.to_json(), mimetype="application/json"
            )

        @self.app.route("/anonymizers", methods=["GET"])
        def anonymizers():
            """Return a list of supported anonymizers."""
            return jsonify(self.anonymizer.get_anonymizers())

        @self.app.route("/deanonymizers", methods=["GET"])
        def deanonymizers():
            """Return a list of supported deanonymizers."""
            return jsonify(self.deanonymize.get_deanonymizers())

        @self.app.errorhandler(InvalidParamError)
        def invalid_param(err):
            self.logger.warning(
                f"Request failed with parameter validation error: {err.err_msg}"
            )
            return jsonify(error=err.err_msg), 422

        @self.app.errorhandler(HTTPException)
        def http_exception(e):
            return jsonify(error=e.description), e.code

        @self.app.errorhandler(Exception)
        def server_error(e):
            self.logger.error(f"A fatal error occurred during execution: {e}")
            return jsonify(error="Internal server error"), 500


def _batch_items(field_name, value, texts):
    """Align a per-item results field with a batch ``text`` list.

    :param field_name: name of the request field, used in the error message.
    :param value: the raw request value for that field (expected to be a list
        of lists, one per item in ``texts``), or ``None`` if omitted.
    :param texts: the batch ``text`` list the request is being validated against.
    """
    if value is None:
        return [[] for _ in texts]
    if len(value) != len(texts):
        raise InvalidParamError(
            f"Invalid input, '{field_name}' must contain one list of results "
            f"per item in 'text' when 'text' is a list ({len(texts)} text "
            f"items, {len(value)} '{field_name}' items)"
        )
    return value


def create_app():  # noqa
    server = Server()
    return server.app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    app.run(host="0.0.0.0", port=port)
