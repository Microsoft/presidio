import os
from typing import Optional

import pathspec
import yaml
from presidio_analyzer import AnalyzerEngine


class PresidioCLIConfigError(Exception):
    """Represents an error in the configuration file."""

    pass


class PresidioCLIConfig(object):
    """Represents Presidio CLI configuration file. Reads the file and transforms the contents to class fields."""  # noqa: E501

    def __init__(
        self, content: Optional[str] = None, file: Optional[str] = None
    ) -> None:
        assert (content is None) ^ (file is None)
        self.ignore = None
        self.locale = None
        self.analyzer = AnalyzerEngine()
        self.threshold = 0
        self.language = "en"
        self.allow_list = []
        if file is not None:
            with open(file) as f:
                content = f.read()
        self.parse(content)
        self.validate()

    def is_file_ignored(self, filepath: str) -> bool:
        """
        Check if file should be processed by the Analyzer or ignored.

        :param filepath: Path of file to be processed.
        """
        return self.ignore and filepath and self.ignore.match_file(filepath)

    def is_text_file(self, filepath: str) -> bool:
        """Detect if file is a not a binary file.Based on https://stackoverflow.com/a/7392391.

        :param filepath: Path of the configuration file.
        """

        # Try to read the file as UTF-8.
        # In case some invalid UTF-8 characters are found,
        # an exception is caught and the file is not going
        # to be processed.
        try:
            with open(filepath, newline="", encoding="utf-8") as f:
                _ = f.read()
        except UnicodeDecodeError:
            return False

        textchars = bytearray(
            {7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7F}
        )
        with open(filepath, "rb") as f:
            # return true if it's not a binary
            return not bool(f.read(1024).translate(None, textchars))

    def extend(self, base_config: "PresidioCLIConfig") -> None:
        """
        In case the configuration file is based on another file, append detected entities from base config to current config and overwrite language and ignored files with contents of base config.

        :param base_config: PresidioCLIConfig object
        """  # noqa: E501
        assert isinstance(base_config, PresidioCLIConfig)

        # Create list with unique entries
        if base_config.entities is not None:
            self.entities = list(set(base_config.entities + self.entities))

        if base_config.ignore is not None:
            self.ignore = base_config.ignore

        if base_config.language is not None:
            self.language = base_config.language

    def parse(self, raw_content: str) -> None:
        """
        Read the content of YAML file and save the properties in class fields.

        :param raw_content: String with the contents of configuration file.
        """
        try:
            conf = yaml.safe_load(raw_content)
        except Exception as e:
            raise PresidioCLIConfigError("invalid config: %s" % e)

        if not isinstance(conf, dict):
            raise PresidioCLIConfigError("invalid config: not a dict")

        self.entities = conf.get("entities", {})

        if self.entities == {}:
            self.entities = self.analyzer.get_supported_entities()

        if "threshold" in conf:
            try:
                # YAML loads true/yes/on as booleans, which float() would accept
                if isinstance(conf["threshold"], bool):
                    raise TypeError("threshold is a boolean")
                threshold = float(conf["threshold"])
            except (TypeError, ValueError, OverflowError) as e:
                raise PresidioCLIConfigError(
                    f"Invalid threshold value: {conf['threshold']}. "
                    "Threshold must be a number"
                ) from e
            if not 0 <= threshold <= 1:
                raise PresidioCLIConfigError(
                    f"Invalid threshold value: {conf['threshold']}. "
                    f"Threshold must be between 0 and 1"
                )
            self.threshold = threshold
        if "allow" in conf:
            self.allow_list = conf["allow"]
        if "language" in conf:
            self.language = conf["language"]
        if "extends" in conf:
            path = get_extended_config_file(conf["extends"])
            base = PresidioCLIConfig(file=path)
            try:
                self.extend(base)
            except Exception as e:
                raise PresidioCLIConfigError("invalid config: %s" % e)

        if "ignore" in conf:
            if not isinstance(conf["ignore"], str):
                raise PresidioCLIConfigError(
                    "invalid config: ignore should contain file patterns"
                )
            self.ignore = pathspec.PathSpec.from_lines(
                "gitwildmatch", conf["ignore"].splitlines()
            )

        if "locale" in conf:
            if not isinstance(conf["locale"], str):
                raise PresidioCLIConfigError(
                    "invalid config: locale should be a string"
                )
            self.locale = conf["locale"]

    def validate(self) -> None:
        """Check if entities requested to be detected in input file are supported by Presidio."""  # noqa: E501
        for id in self.entities:
            try:
                assert id in self.analyzer.get_supported_entities()
            except Exception:
                raise PresidioCLIConfigError("invalid config: no such entity %s" % id)


def get_extended_config_file(name: str) -> str:
    """
    Check if the configuration file is one of sample configs or if it is a file supplied by the user.

    :param name: file name
    :return: Full path of configuration file
    """  # noqa: E501
    # Is it a standard conf shipped with yamllint...
    if "/" not in name:
        std_conf = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "conf", name + ".yaml"
        )

        if os.path.isfile(std_conf):
            return std_conf

    # or a custom conf on filesystem?
    return name
