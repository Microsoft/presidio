import copy
import logging
from typing import Dict, List, Optional, Union

from presidio_analyzer import EntityRecognizer, RecognizerResult
from presidio_analyzer.context_aware_enhancers import ContextAwareEnhancer
from presidio_analyzer.nlp_engine import NlpArtifacts

logger = logging.getLogger("presidio-analyzer")


class LemmaContextAwareEnhancer(ContextAwareEnhancer):
    """
    A class representing a lemma based context aware enhancer logic.

    Context words might enhance confidence score of a recognized entity,
    LemmaContextAwareEnhancer is an implementation of Lemma based context aware logic,
    it compares spacy lemmas of each word in context of the matched entity to given
    context and the recognizer context words,
    if matched it enhance the recognized entity confidence score by a given factor.

    :param context_similarity_factor: How much to enhance confidence of match entity
    :param min_score_with_context_similarity: Minimum confidence score
    :param context_prefix_count: how many words before the entity to match context
    :param context_suffix_count: how many words after the entity to match context
    :param context_matching_mode: Matching mode for context words. Options:
        - "substring" (default): Match context words as substrings
          (e.g., 'card' matches 'creditcard', 'lic' matches 'duplicate').
          Maintains backward compatibility.
        - "whole_word": Match context words only as whole words
          (e.g., 'lic' matches 'lic' but not 'duplicate').
          Prevents false positives.
    """

    def __init__(
        self,
        context_similarity_factor: float = 0.35,
        min_score_with_context_similarity: float = 0.4,
        context_prefix_count: int = 5,
        context_suffix_count: int = 0,
        context_matching_mode: str = "substring",
    ):
        super().__init__(
            context_similarity_factor=context_similarity_factor,
            min_score_with_context_similarity=min_score_with_context_similarity,
            context_prefix_count=context_prefix_count,
            context_suffix_count=context_suffix_count,
        )
        if context_matching_mode not in ["whole_word", "substring"]:
            raise ValueError(
                f"context_matching_mode must be one of: 'whole_word', 'substring'. "
                f"Got: {context_matching_mode}"
            )
        self.context_matching_mode = context_matching_mode

    def enhance_using_context(
        self,
        text: str,
        raw_results: List[RecognizerResult],
        nlp_artifacts: NlpArtifacts,
        recognizers: List[EntityRecognizer],
        context: Optional[List[str]] = None,
    ) -> List[RecognizerResult]:
        """
        Update results in case the lemmas of surrounding words or input context
        words are identical to the context words.

        Using the surrounding words of the actual word matches, look
        for specific strings that if found contribute to the score
        of the result, improving the confidence that the match is
        indeed of that PII entity type

        :param text: The actual text that was analyzed
        :param raw_results: Recognizer results which didn't take
                            context into consideration
        :param nlp_artifacts: The nlp artifacts contains elements
                              such as lemmatized tokens for better
                              accuracy of the context enhancement process
        :param recognizers: the list of recognizers
        :param context: list of context words
        """  # noqa: D205,D400

        # create a deep copy of the results object, so we can manipulate it
        results = copy.deepcopy(raw_results)

        # create recognizer context dictionary
        recognizers_dict = {recognizer.id: recognizer for recognizer in recognizers}

        # Create empty list in None or lowercase all context words in the list
        if not context:
            context = []
        else:
            context = [word.lower() for word in context]

        # Sanity
        if nlp_artifacts is None:
            logger.warning("NLP artifacts were not provided")
            return results

        for result in results:
            recognizer = None
            # get recognizer matching the result, if found.
            if (
                result.recognition_metadata
                and RecognizerResult.RECOGNIZER_IDENTIFIER_KEY
                in result.recognition_metadata.keys()
            ):
                recognizer = recognizers_dict.get(
                    result.recognition_metadata[
                        RecognizerResult.RECOGNIZER_IDENTIFIER_KEY
                    ]
                )

            if not recognizer:
                logger.debug(
                    "Recognizer name not found as part of the "
                    "recognition_metadata dict in the RecognizerResult. "
                )
                continue

            # A recognizer may define its context words as a flat list shared
            # by all its entities, or as a dict mapping each entity type to
            # its own list of context words. Only boost the result with the
            # words applicable to its entity type.
            recognizer_context = self._get_context_words_for_entity(
                recognizer.context, result.entity_type
            )

            # skip recognizer result if the recognizer doesn't define
            # context words for this entity type
            if not recognizer_context:
                logger.debug(
                    "recognizer '%s' does not define context words for entity '%s'",
                    recognizer.name,
                    result.entity_type,
                )
                continue

            # skip context enhancement if already boosted by recognizer level
            if result.recognition_metadata.get(
                RecognizerResult.IS_SCORE_ENHANCED_BY_CONTEXT_KEY
            ):
                logger.debug("result score already boosted, skipping")
                continue

            # extract lemmatized context from the surrounding of the match
            word = text[result.start : result.end]

            surrounding_words = self._extract_surrounding_words(
                nlp_artifacts=nlp_artifacts, word=word, start=result.start
            )

            # combine other sources of context with surrounding words
            surrounding_words.extend(context)

            supportive_context_word = self._find_supportive_word_in_context(
                surrounding_words, recognizer_context, self.context_matching_mode
            )
            if supportive_context_word != "":
                result.score += self.context_similarity_factor
                result.score = max(result.score, self.min_score_with_context_similarity)
                result.score = min(result.score, ContextAwareEnhancer.MAX_SCORE)

                # Update the explainability object with context information
                # helped to improve the score
                result.analysis_explanation.set_supportive_context_word(
                    supportive_context_word
                )
                result.analysis_explanation.set_improved_score(result.score)
        return results

    @staticmethod
    def _get_context_words_for_entity(
        context: Optional[Union[List[str], Dict[str, List[str]]]],
        entity_type: str,
    ) -> List[str]:
        """Return the context words applicable to a result's entity type.

        A recognizer may define its context words as a flat list shared by
        all supported entities, or as a dict mapping each entity type to its
        own list of context words. In the dict form, an entity type with no
        entry gets no context words, so words for one entity cannot boost
        detections of another entity from the same recognizer.

        :param context: The recognizer's context words (list, dict, or None).
        :param entity_type: The entity type of the result being enhanced.
        :return: The list of context words to match against.
        """
        if not context:
            return []
        if isinstance(context, dict):
            return list(context.get(entity_type) or [])
        return list(context)

    @staticmethod
    def _find_supportive_word_in_context(
        context_list: List[str],
        recognizer_context_list: List[str],
        matching_mode: str = "substring",
    ) -> str:
        """
        Find words in the text which are relevant for context evaluation.

        A word is considered a supportive context word based on the matching mode:
        - "substring" (default): Substring match
          (e.g., 'card' matches 'creditcard', 'lic' matches 'duplicate')
        - "whole_word": Exact whole-word match (case-insensitive)
          (e.g., 'lic' matches 'lic' but not 'duplicate')

        :param context_list words before and after the matched entity within
               a specified window size
        :param recognizer_context_list a list of words considered as
                context keywords manually specified by the recognizer's author
        :param matching_mode: Matching mode ('whole_word' or 'substring').
               Defaults to 'substring'.
        """
        word = ""
        # If the context list is empty, no need to continue
        if context_list is None or recognizer_context_list is None:
            return word

        for predefined_context_word in recognizer_context_list:
            result = False

            if matching_mode == "substring":
                # Substring match (case-insensitive) - default behavior
                # for backward compatibility
                result = next(
                    (
                        True
                        for keyword in context_list
                        if predefined_context_word.lower() in keyword.lower()
                    ),
                    False,
                )
            elif matching_mode == "whole_word":
                # Exact whole-word match (case-insensitive)
                result = next(
                    (
                        True
                        for keyword in context_list
                        if predefined_context_word.lower() == keyword.lower()
                    ),
                    False,
                )

            if result:
                logger.debug("Found context keyword '%s'", predefined_context_word)
                word = predefined_context_word
                break

        return word

    def _extract_surrounding_words(
        self, nlp_artifacts: NlpArtifacts, word: str, start: int
    ) -> List[str]:
        """Extract words surrounding another given word.

        The text from which the context is extracted is given in the nlp
        doc.

        :param nlp_artifacts: An abstraction layer which holds different
                              items which are the result of a NLP pipeline
                              execution on a given text
        :param word: The word to look for context around
        :param start: The start index of the word in the original text
        """
        if not nlp_artifacts.tokens:
            logger.info("Skipping context extraction due to lack of NLP artifacts")
            # if there are no nlp artifacts, this is ok, we can
            # extract context and we return a valid, yet empty
            # context
            return [""]

        # Get the already prepared words in the given text, in their
        # LEMMATIZED version
        lemmatized_keywords = nlp_artifacts.keywords

        # since the list of tokens is not necessarily aligned
        # with the actual index of the match, we look for the
        # token index which corresponds to the match
        token_index = self._find_index_of_match_token(
            word, start, nlp_artifacts.tokens, nlp_artifacts.tokens_indices
        )

        # index i belongs to the PII entity, take the preceding n words
        # and the successing m words into a context list

        backward_context = self._add_n_words_backward(
            token_index,
            self.context_prefix_count,
            nlp_artifacts.lemmas,
            lemmatized_keywords,
        )
        forward_context = self._add_n_words_forward(
            token_index,
            self.context_suffix_count,
            nlp_artifacts.lemmas,
            lemmatized_keywords,
        )

        context_list = []
        context_list.extend(backward_context)
        context_list.extend(forward_context)
        context_list = list(set(context_list))
        logger.debug("Context list is: %s", " ".join(context_list))
        return context_list

    @staticmethod
    def _find_index_of_match_token(
        word: str,
        start: int,
        tokens,
        tokens_indices: List[int],
    ) -> int:
        found = False
        # we use the known start index of the original word to find the actual
        # token at that index, we are not checking for equivalence since the
        # token might be just a substring of that word (e.g. for phone number
        # 555-124564 the first token might be just '555' or for a match like '
        # rocket' the actual token will just be 'rocket' hence the misalignment
        # of indices)
        # Note: we are iterating over the original tokens (not the lemmatized)
        i = -1
        for i, token in enumerate(tokens, 0):
            # Either we found a token with the exact location, or
            # we take a token which its characters indices covers
            # the index we are looking for.
            if (tokens_indices[i] == start) or (start < tokens_indices[i] + len(token)):
                # found the interesting token, the one that around it
                # we take n words, we save the matching lemma
                found = True
                break

        if not found:
            raise ValueError(
                "Did not find word '" + word + "' "
                "in the list of tokens although it "
                "is expected to be found"
            )
        return i

    @staticmethod
    def _add_n_words(
        index: int,
        n_words: int,
        lemmas: List[str],
        lemmatized_filtered_keywords: List[str],
        is_backward: bool,
    ) -> List[str]:
        """
        Prepare a string of context words.

        Return a list of words which surrounds a lemma at a given index.
        The words will be collected only if exist in the filtered array

        :param index: index of the lemma that its surrounding words we want
        :param n_words: number of words to take
        :param lemmas: array of lemmas
        :param lemmatized_filtered_keywords: the array of filtered
               lemmas from the original sentence,
        :param is_backward: if true take the preceeding words, if false,
                            take the successing words
        """
        i = index
        context_words = []
        # The entity itself is no interest to us...however we want to
        # consider it anyway for cases were it is attached with no spaces
        # to an interesting context word, so we allow it and add 1 to
        # the number of collected words

        # collect at most n words (in lower case)
        remaining = n_words + 1
        while 0 <= i < len(lemmas) and remaining > 0:
            lower_lemma = lemmas[i].lower()
            if lower_lemma in lemmatized_filtered_keywords:
                context_words.append(lower_lemma)
                remaining -= 1
            i = i - 1 if is_backward else i + 1
        return context_words

    def _add_n_words_forward(
        self,
        index: int,
        n_words: int,
        lemmas: List[str],
        lemmatized_filtered_keywords: List[str],
    ) -> List[str]:
        return self._add_n_words(
            index, n_words, lemmas, lemmatized_filtered_keywords, False
        )

    def _add_n_words_backward(
        self,
        index: int,
        n_words: int,
        lemmas: List[str],
        lemmatized_filtered_keywords: List[str],
    ) -> List[str]:
        return self._add_n_words(
            index, n_words, lemmas, lemmatized_filtered_keywords, True
        )
