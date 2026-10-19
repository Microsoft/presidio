"""REST API server for image redactor."""

import base64
import logging
import os
from io import BytesIO

from flask import Flask, Response, jsonify, request
from PIL import Image
from presidio_image_redactor import ImageRedactorEngine
from presidio_image_redactor.entities import InvalidParamError
from presidio_image_redactor.entities.api_request_convertor import (
    color_fill_string_to_value,
    get_json_data,
    image_to_byte_array,
)

DEFAULT_PORT = "3000"

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
    """Flask server for image redactor."""

    def __init__(self):
        self.logger = logging.getLogger("presidio-image-redactor")
        self.app = Flask(__name__)
        self.logger.info("Starting image redactor engine")
        self.engine = ImageRedactorEngine()
        self.logger.info(WELCOME_MESSAGE)

        @self.app.route("/health")
        def health() -> str:
            """Return basic health probe result."""
            return "Presidio Image Redactor service is up"

        @self.app.route("/redact", methods=["POST"])
        def redact():
            """Return a redacted image."""
            params = get_json_data(request.form.get("data"))
            color_fill = color_fill_string_to_value(params)
            if request.get_json(silent=True) and "image" in request.json:
                im = Image.open(BytesIO(base64.b64decode(request.json.get("image"))))
                analyzer_entities = request.json.get("analyzer_entities")
                redacted_image = self.engine.redact(
                    im, color_fill, entities=analyzer_entities
                )
                img_byte_arr = image_to_byte_array(redacted_image, im.format)
                return Response(
                    base64.b64encode(img_byte_arr), mimetype="application/octet-stream"
                )

            elif request.files and "image" in request.files:
                im = Image.open(request.files.get("image"))
                redacted_image = self.engine.redact(im, color_fill, score_threshold=0.4)
                img_byte_arr = image_to_byte_array(redacted_image, im.format)
                return Response(img_byte_arr, mimetype="application/octet-stream")
            else:
                raise InvalidParamError("Invalid parameter, please add image data")

        @self.app.errorhandler(InvalidParamError)
        def invalid_param(err):
            self.logger.warning(
                f"failed to redact image with validation error: {err.err_msg}"
            )
            return jsonify(error=err.err_msg), 422

        @self.app.errorhandler(Exception)
        def server_error(e):
            self.logger.error(f"A fatal error occurred during execution: {e}")
            return jsonify(error="Internal server error"), 500


def create_app():  # noqa
    server = Server()
    return server.app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    app.run(host="0.0.0.0", port=port)
