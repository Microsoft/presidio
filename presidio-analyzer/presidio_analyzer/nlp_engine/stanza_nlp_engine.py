import logging
import warnings
from typing import Any, Dict, Generator, List, Optional, Tuple, Union

try:
    import stanza
    from stanza import Pipeline
    from stanza.models.common.pretrain import Pretrain
    from stanza.models.common.vocab import UNK_ID
    from stanza.resources.common import DEFAULT_MODEL_DIR

except ImportError:
    stanza = None


from spacy import Language, blank
from spacy.tokens import Doc, Token
from spacy.util import registry

from presidio_analyzer.nlp_engine import (
    NerModelConfiguration,
    NlpArtifacts,
    SpacyNlpEngine,
    device_detector,
)

logger = logging.getLogger("presidio-analyzer")


class StanzaNlpEngine(SpacyNlpEngine):
    """
    StanzaNlpEngine is an abstraction layer over the nlp module.

    It provides processing functionality as well as other queries
    on tokens.
    The StanzaNlpEngine uses spacy-stanza and stanza as its NLP module

    :param models: Dictionary with the name of the spaCy model per language.
    For example: models = [{"lang_code": "en", "model_name": "en"}]
    :param ner_model_configuration: Parameters for the NER model.
    See conf/stanza.yaml for an example

    """

    engine_name = "stanza"
    is_available = bool(stanza)

    def __init__(
        self,
        models: Optional[List[Dict[str, str]]] = None,
        ner_model_configuration: Optional[NerModelConfiguration] = None,
        download_if_missing: bool = True,
    ):
        super().__init__(models, ner_model_configuration)
        self.download_if_missing = download_if_missing
        self.device = device_detector.get_device()

    def load(self) -> None:
        """Load the NLP model."""

        logger.debug(f"Loading Stanza models: {self.models}")

        # Enable GPU support using parent class method
        super()._enable_gpu()

        self.nlp = {}
        for model in self.models:
            self._validate_model_params(model)
            self.nlp[model["lang_code"]] = load_pipeline(
                model["model_name"],
                processors="tokenize,pos,lemma,ner",
                download_method="DOWNLOAD_RESOURCES"
                if self.download_if_missing
                else None,
                device=self.device,
            )

    def process_batch(
        self,
        texts: Union[List[str], List[Tuple[str, object]]],
        language: str,
        batch_size: int = 1,
        n_process: int = 1,
        as_tuples: bool = False,
    ) -> Generator[
        Union[Tuple[Any, NlpArtifacts, Any], Tuple[Any, NlpArtifacts]], Any, None
    ]:
        """Execute the NLP pipeline on a batch of texts using Stanza's bulk processing.

        This method overrides SpacyNlpEngine.process_batch to leverage Stanza's
        efficient bulk_process method, which processes multiple documents together
        for better GPU utilization.

        Note: Stanza batches internally at the sentence/token level, not docs.
        For optimal GPU performance, use larger batch sizes (e.g., 16-32 docs).
        GPU utilization depends on total sentences/tokens across all docs in batch.

        :param texts: A list of texts to process. if as_tuples is set to True,
            texts should be a list of tuples (text, context).
        :param language: The language of the texts.
        :param batch_size: Number of documents per bulk_process call.
            Recommended: 16-32+ for GPU, lower values acceptable for CPU.
        :param n_process: Not used for Stanza (kept for API compatibility).
        :param as_tuples: If set to True, inputs should be a sequence of
            (text, context) tuples. Output will then be a sequence of
            (text, NlpArtifacts, context) tuples. Defaults to False.

        :return: A generator of tuples (text, NlpArtifacts, context) or
            (text, NlpArtifacts) depending on the value of as_tuples.
        """

        if not self.nlp:
            raise ValueError("NLP engine is not loaded. Consider calling .load()")

        # Get the StanzaTokenizer (which wraps the Stanza pipeline)
        # In spaCy, tokenizers are accessed via .tokenizer, not .get_pipe()
        stanza_tokenizer = self.nlp[language].tokenizer
        stanza_pipeline = stanza_tokenizer.snlp

        text_list = list(texts) if not isinstance(texts, list) else texts

        for batch_start in range(0, len(text_list), batch_size):
            batch_end = min(batch_start + batch_size, len(text_list))
            batch = text_list[batch_start:batch_end]

            if as_tuples:
                batch_texts = [str(text) for text, context in batch]
                contexts = [context for text, context in batch]
            else:
                batch_texts = [str(text) for text in batch]
                contexts = None

            # Create Stanza Document objects and process via bulk_process
            # Stanza handles internal batching at sentence/token level
            stanza_docs = [stanza.Document([], text=text) for text in batch_texts]
            processed_stanza_docs = stanza_pipeline.bulk_process(stanza_docs)

            # Convert processed Stanza docs to spaCy docs using spacy-stanza's logic
            # We call _convert_doc() which reuses StanzaTokenizer's conversion path
            for idx, processed_stanza_doc in enumerate(processed_stanza_docs):
                spacy_doc = stanza_tokenizer._convert_doc(processed_stanza_doc)
                nlp_artifacts = self._doc_to_nlp_artifact(spacy_doc, language)

                if as_tuples:
                    yield batch_texts[idx], nlp_artifacts, contexts[idx]
                else:
                    yield batch_texts[idx], nlp_artifacts


# Code taken from https://github.com/explosion/spacy-stanza
# Supports Stanza > 1.7.0
def load_pipeline(
    name: str,
    *,
    lang: str = "",
    dir: Optional[str] = None,
    package: str = "default",
    processors: Union[dict, str] = None,
    logging_level: Optional[Union[int, str]] = None,
    verbose: Optional[bool] = None,
    device: Optional[str] = None,
    **kwargs,
) -> Language:
    """Create a blank nlp object for a given language code.

    with a stanza pipeline as part of the tokenizer.

    To use the default stanza pipeline with
    the same language code, leave the tokenizer config empty. Otherwise, pass
    in the stanza pipeline settings in config["nlp"]["tokenizer"].

    name (str): The language code, e.g. "en".
    lang: str = "",
    dir: Optional[str] = None,
    package: str = "default",
    processors: Union[dict, str] = {},
    logging_level: Optional[Union[int, str]] = None,
    verbose: Optional[bool] = None,
    device: Optional[str] = None,
    **kwargs: Options for the individual stanza processors.
    RETURNS (Language): The nlp object.
    """

    if not processors:
        processors = {}

    # Create an empty config skeleton
    config = {"nlp": {"tokenizer": {"kwargs": {}}}}
    if lang == "":
        lang = name
    # Set the stanza tokenizer
    config["nlp"]["tokenizer"]["@tokenizers"] = "PipelineAsTokenizer.v1"
    # Set the stanza options
    config["nlp"]["tokenizer"]["lang"] = lang
    config["nlp"]["tokenizer"]["dir"] = dir
    config["nlp"]["tokenizer"]["package"] = package
    config["nlp"]["tokenizer"]["processors"] = processors
    config["nlp"]["tokenizer"]["logging_level"] = logging_level
    config["nlp"]["tokenizer"]["verbose"] = verbose
    config["nlp"]["tokenizer"]["device"] = device
    config["nlp"]["tokenizer"]["kwargs"].update(kwargs)
    return blank(name, config=config)


@registry.tokenizers("PipelineAsTokenizer.v1")
def create_tokenizer(
    lang: str = "",
    dir: Optional[str] = None,
    package: str = "default",
    processors: Union[dict, str] = None,
    logging_level: Optional[Union[int, str]] = None,
    verbose: Optional[bool] = None,
    device: Optional[str] = None,
    kwargs: dict = None,
):
    """Create a tokenizer factory for a given language code.

    :param lang: The language code, e.g. "en".
    :param dir: The model directory.
    :param package: The model package.
    :param processors: The processors to use.
    :param logging_level: The logging level.
    :param verbose: Whether to be verbose.
    :param device: The device to use (e.g., "cpu", "cuda").
        Note: MPS is currently not supported.
    :param kwargs: Additional keyword arguments.
    """
    if not processors:
        processors = {}
    if not kwargs:
        kwargs = {}

    def tokenizer_factory(
        nlp,
        lang=lang,
        dir=dir,
        package=package,
        processors=processors,
        logging_level=logging_level,
        verbose=verbose,
        device=device,
        kwargs=kwargs,
    ) -> StanzaTokenizer:
        if dir is None:
            dir = DEFAULT_MODEL_DIR
        snlp = Pipeline(
            lang=lang,
            dir=dir,
            package=package,
            processors=processors,
            logging_level=logging_level,
            verbose=verbose,
            device=device,
            **kwargs,
        )
        return StanzaTokenizer(
            snlp,
            nlp.vocab,
        )

    return tokenizer_factory


class MultiWordTokenSurface:
    """Surface view over a Stanza multi-word token (mwt).

    Stanza's mwt processor splits contractions such as the German "im"
    into multiple words ("in" + "dem"). Flattening the expanded words into
    the token list breaks the alignment with the original text (and with
    it every character offset, dropping NER entities). This wrapper exposes
    the unexpanded surface form as a single token instead: `text` and
    `lemma` are the surface form, all other annotations are borrowed from
    the first expanded word.
    """

    def __init__(self, token):
        """Init with a Stanza token that has more than one word.

        :param token: A stanza.models.common.doc.Token with more than one word.
        """
        self._token = token
        self._first_word = token.words[0]

    @property
    def words(self):
        """The words Stanza expanded this multi-word token into."""
        return self._token.words

    @property
    def text(self):
        """The surface form of the token, as it appears in the text."""
        return self._token.text

    @property
    def lemma(self):
        """The surface form is used as its own lemma.

        A lemma taken from one of the expanded words (e.g. "in" for "im")
        would not correspond to any span of the original text.
        """
        return self._token.text

    def __getattr__(self, name):
        """Delegate annotations not defined here to the first expanded word.

        Only called for attributes not found through normal lookup,
        e.g. upos, xpos, feats, head and deprel.
        """
        first_word = self.__dict__.get("_first_word")
        if first_word is None:
            raise AttributeError(name)
        return getattr(first_word, name)


# Code taken from https://github.com/explosion/spacy-stanza
# Supports Stanza > 1.7.0
class StanzaTokenizer(object):
    """The entire stanza pipeline in a custom tokenizer.

    Because we're only running the Stanza pipeline once and don't split
    it up into spaCy pipeline components, we'll set all the attributes within
    a custom tokenizer.
    """

    def __init__(self, snlp, vocab):
        """Initialize the tokenizer.

        snlp (stanza.Pipeline): The initialized Stanza pipeline.
        vocab (spacy.vocab.Vocab): The vocabulary to use.
        RETURNS (Tokenizer): The custom tokenizer.
        """
        self.snlp = snlp
        self.vocab = vocab
        self.svecs = self._find_embeddings(snlp)

    def __call__(self, text):
        """Convert a Stanza Doc to a spaCy Doc.

        text (Unicode): The text to process.
        RETURNS (spacy.tokens.Doc): The spaCy Doc object.
        """
        if not text:
            return Doc(self.vocab)
        elif text.isspace():
            return Doc(self.vocab, words=[text], spaces=[False])

        snlp_doc = self.snlp(text)
        return self._convert_doc(snlp_doc)

    def _convert_doc(self, snlp_doc):
        """Convert a processed Stanza Document to a spaCy Doc.

        This method contains the conversion logic separated from text processing,
        allowing it to be called with already-processed Stanza documents.

        :param snlp_doc: Processed Stanza Document
        :return: spaCy Doc object
        """
        if not snlp_doc.text:
            return Doc(self.vocab)
        elif snlp_doc.text.isspace():
            return Doc(self.vocab, words=[snlp_doc.text], spaces=[False])

        text = snlp_doc.text
        snlp_tokens, snlp_heads = self.__get_tokens_with_heads(snlp_doc)
        pos = []
        tags = []
        morphs = []
        deps = []
        heads = []
        lemmas = []
        token_texts = [t.text for t in snlp_tokens]
        is_aligned = True
        try:
            words, spaces = self.__get_words_and_spaces(token_texts, text)
        except ValueError:
            words = token_texts
            spaces = [True] * len(words)
            is_aligned = False
            warnings.warn(
                "Due to multiword token expansion or an alignment "
                "issue, the original text has been replaced by space-separated "
                "expanded tokens.",
                stacklevel=4,
            )
        offset = 0
        for i, word in enumerate(words):
            if word.isspace() and (
                i + offset >= len(snlp_tokens) or word != snlp_tokens[i + offset].text
            ):
                # insert a space token
                pos.append("SPACE")
                tags.append("_SP")
                morphs.append("")
                deps.append("")
                lemmas.append(word)

                # increment any heads left of this position that point beyond
                # this position to the right (already present in heads)
                for j in range(0, len(heads)):
                    if j + heads[j] >= i:
                        heads[j] += 1

                # decrement any heads right of this position that point beyond
                # this position to the left (yet to be added from snlp_heads)
                for j in range(i + offset, len(snlp_heads)):
                    if j + snlp_heads[j] < i + offset:
                        snlp_heads[j] -= 1

                # initial space tokens are attached to the following token,
                # otherwise attach to the preceding token
                if i == 0:
                    heads.append(1)
                else:
                    heads.append(-1)

                offset -= 1
            else:
                token = snlp_tokens[i + offset]
                assert word == token.text

                pos.append(token.upos or "")
                tags.append(token.xpos or token.upos or "")
                morphs.append(token.feats or "")
                deps.append(token.deprel or "")
                heads.append(snlp_heads[i + offset])
                lemmas.append(token.lemma or "")

        doc = Doc(
            self.vocab,
            words=words,
            spaces=spaces,
            pos=pos,
            tags=tags,
            morphs=morphs,
            lemmas=lemmas,
            deps=deps,
            heads=[head + i for i, head in enumerate(heads)],
        )
        ents = []
        for ent in snlp_doc.entities:
            ent_span = doc.char_span(ent.start_char, ent.end_char, ent.type)
            ents.append(ent_span)
        if not is_aligned or not all(ents):
            warnings.warn(
                f"Can't set named entities because of multi-word token "
                f"expansion or because the character offsets don't map to "
                f"valid tokens produced by the Stanza tokenizer:\n"
                f"Words: {words}\n"
                f"Entities: {[(e.text, e.type, e.start_char, e.end_char) for e in snlp_doc.entities]}",  # noqa
                stacklevel=4,
            )
        else:
            doc.ents = ents

        if self.svecs is not None:
            doc.user_token_hooks["vector"] = self.token_vector
            doc.user_token_hooks["has_vector"] = self.token_has_vector
        return doc

    def pipe(self, texts):
        """Tokenize a stream of texts.

        texts: A sequence of Unicode texts.
        YIELDS (Doc): A sequence of Doc objects, in order.
        """
        for text in texts:
            yield self(text)

    @staticmethod
    def __get_tokens_with_heads(snlp_doc):
        """Flatten the tokens in the Stanza Doc and extract the token indices.

        extract the token indices of the sentence start tokens to set is_sent_start.

        Multi-word tokens (words expanded by Stanza's mwt processor,
        e.g. the German contraction "im" into "in" + "dem") are kept as a
        single surface token, so that the token texts remain aligned with
        the original text and character offsets (e.g. of NER entities)
        are preserved.

        snlp_doc (stanza.Document): The processed Stanza doc.
        RETURNS (list): The tokens (words).
        """
        tokens = []
        heads = []
        offset = 0
        for sentence in snlp_doc.sentences:
            # Stanza tokens, with multi-word tokens kept unexpanded
            sentence_tokens = []
            # Map each (expanded) word index within the sentence to the index
            # of the emitted token covering it, so that dependency heads of
            # words surrounding a multi-word token stay correct after it is
            # collapsed into a single token.
            word_index_to_token_index = {}
            word_index = 0
            for token in sentence.tokens:
                if not token.words:
                    continue
                token_index = len(sentence_tokens)
                if len(token.words) > 1:
                    sentence_tokens.append(MultiWordTokenSurface(token))
                else:
                    sentence_tokens.append(token.words[0])
                for _ in range(len(token.words)):
                    word_index_to_token_index[word_index] = token_index
                    word_index += 1
            for token_index, token in enumerate(sentence_tokens):
                # Here, we're calculating the absolute token index in the doc,
                # then the *relative* index of the head (the governor's word
                # index is 1-based, 0 means root and is left at 0)
                if token.head:
                    head = (
                        offset
                        + word_index_to_token_index.get(token.head - 1, token_index)
                        - len(tokens)
                    )
                else:
                    head = 0
                heads.append(head)
                tokens.append(token)
            offset += len(sentence_tokens)
        return tokens, heads

    @staticmethod
    def __get_words_and_spaces(words, text):
        if "".join("".join(words).split()) != "".join(text.split()):
            raise ValueError("Unable to align mismatched text and words.")
        text_words = []
        text_spaces = []
        text_pos = 0
        # normalize words to remove all whitespace tokens
        norm_words = [word for word in words if not word.isspace()]
        # align words with text
        for word in norm_words:
            try:
                word_start = text[text_pos:].index(word)
            except ValueError:
                raise ValueError("Unable to align mismatched text and words.")
            if word_start > 0:
                text_words.append(text[text_pos : text_pos + word_start])
                text_spaces.append(False)
                text_pos += word_start
            text_words.append(word)
            text_spaces.append(False)
            text_pos += len(word)
            if text_pos < len(text) and text[text_pos] == " ":
                text_spaces[-1] = True
                text_pos += 1
        if text_pos < len(text):
            text_words.append(text[text_pos:])
            text_spaces.append(False)
        return text_words, text_spaces

    def token_vector(self, token: Token):
        """Get Stanza's pretrained word embedding for given token.

        :param token: The token whose embedding will be returned
        :return (np.ndarray[ndim=1, dtype='float32']): the embedding/vector.
            token.vector.size > 0 if Stanza pipeline contains a processor with
            embeddings, else token.vector.size == 0.
            A 0-vector (origin) will be returned
        when the token doesn't exist in snlp's pretrained embeddings.
        """
        unit_id = self.svecs.vocab.unit2id(token.text)
        return self.svecs.emb[unit_id]

    def token_has_vector(self, token):
        """Check if the token exists as a unit in snlp's pretrained embeddings."""
        return self.svecs.vocab.unit2id(token.text) != UNK_ID

    @staticmethod
    def _find_embeddings(snlp):
        """Find pretrained word embeddings in any of a SNLP's processors.

        RETURNS (Pretrain): Or None if no embeddings were found.
        """
        embs = None
        for proc in snlp.processors.values():
            if hasattr(proc, "pretrain") and isinstance(proc.pretrain, Pretrain):
                embs = proc.pretrain
                break
        return embs

    # dummy serialization methods
    def to_bytes(self, **kwargs):  # noqa
        return b""

    def from_bytes(self, _bytes_data, **kwargs):  # noqa
        return self

    def to_disk(self, _path, **kwargs):  # noqa
        return None

    def from_disk(self, _path, **kwargs):  # noqa
        return self
