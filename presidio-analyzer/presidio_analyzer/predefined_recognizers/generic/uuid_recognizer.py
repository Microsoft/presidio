from typing import List, Optional

from presidio_analyzer import Pattern, PatternRecognizer


class UuidRecognizer(PatternRecognizer):
    """
    Recognize UUID (Universally Unique Identifier) using regex.

    Supports the standard 8-4-4-4-12 hyphenated hexadecimal format for
    RFC 4122 UUID versions 1-5 and RFC 9562 versions 6-8.

    Note: the nil UUID (00000000-0000-0000-0000-000000000000) is explicitly
    excluded as a non-identifying sentinel value.

    ref:
    - https://datatracker.ietf.org/doc/html/rfc4122
    - https://datatracker.ietf.org/doc/html/rfc9562
    """

    PATTERNS = [
        Pattern(
            "UUID (hyphenated)",
            r"\b[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\b",
            0.5,
        ),
    ]

    CONTEXT = ["uuid", "guid", "unique identifier"]

    # Valid version nibble values: 1-8 (versions 1-5 per RFC 4122;
    # versions 6, 7, 8 per RFC 9562)
    VALID_VERSIONS = {"1", "2", "3", "4", "5", "6", "7", "8"}

    # Valid variant bits (RFC 4122 variant): first hex digit of the
    # 4th group must be 8, 9, a, or b
    VALID_VARIANT_PREFIXES = {"8", "9", "a", "b"}

    NIL_UUID = "00000000-0000-0000-0000-000000000000"

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "UUID",
        name: Optional[str] = None,
    ):
        patterns = patterns if patterns else self.PATTERNS
        context = context if context else self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
            name=name,
        )

    def invalidate_result(self, pattern_text: str) -> bool:
        """
        Check if the pattern text is a valid UUID format.

        Validates the RFC 4122/9562 version nibble and variant bits to
        reduce false positives from arbitrary hex-hyphen strings, and
        filters out the nil UUID (all zeros), which is a well-known
        sentinel value rather than an identifying value.

        :param pattern_text: Text detected as pattern by regex
        :return: True if invalidated (invalid or non-identifying UUID)
        """
        if pattern_text.lower() == self.NIL_UUID:
            return True

        groups = pattern_text.split("-")
        if len(groups) != 5 or any(not g for g in groups):
            return True

        version_nibble = groups[2][0].lower()
        if version_nibble not in self.VALID_VERSIONS:
            return True

        variant_nibble = groups[3][0].lower()
        if variant_nibble not in self.VALID_VARIANT_PREFIXES:
            return True

        return False
