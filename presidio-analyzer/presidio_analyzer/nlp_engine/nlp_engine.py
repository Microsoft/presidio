from abc import ABC, abstractmethod
from typing import Iterable, Iterator, List, Tuple

from presidio_analyzer.nlp_engine import NlpArtifacts


class NlpEngine(ABC):
    """
    NlpEngine is an abstraction layer over the nlp module.

    It provides NLP preprocessing functionality as well as other queries
    on tokens.
    """

    @property
    def has_ner(self) -> bool:
        """Return whether this engine performs Named Entity Recognition natively.

        The default is ``True``. Engines without native NER output should
        override this property and return ``False``; otherwise, they are
        treated as NER-capable.
        """
        return True

    @abstractmethod
    def load(self) -> None:
        """Load the NLP model."""

    @abstractmethod
    def is_loaded(self) -> bool:
        """Return True if the model is already loaded."""

    @abstractmethod
    def process_text(self, text: str, language: str) -> NlpArtifacts:
        """Execute the NLP pipeline on the given text and language."""

    @abstractmethod
    def process_batch(
        self,
        texts: Iterable[str],
        language: str,
        batch_size: int = 1,
        n_process: int = 1,
        **kwargs,
    ) -> Iterator[Tuple[str, NlpArtifacts]]:
        """Execute the NLP pipeline on a batch of texts.

        Returns a tuple of (text, NlpArtifacts)
        """

    @abstractmethod
    def is_stopword(self, word: str, language: str) -> bool:
        """
        Return true if the given word is a stop word.

        (within the given language)
        """

    @abstractmethod
    def is_punct(self, word: str, language: str) -> bool:
        """
        Return true if the given word is a punctuation word.

        (within the given language)
        """

    @abstractmethod
    def get_supported_entities(self) -> List[str]:
        """Return the supported entities for this NLP engine."""
        pass

    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Return the supported languages for this NLP engine."""
        pass
