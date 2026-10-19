# Czech Language Support

> **Domain**: Finance, Legal, Public Administration, General
> **Data Type**: Czech-language free text (contracts, bank correspondence, ID documents, customer communication)
> **Goal**: Detect Czech PII and sensitive identifiers using Presidio's built-in Czech recognizers with a bilingual spaCy NLP engine

## Overview

**Domain**: Finance / Legal / Public Administration
**Data Type**: Czech-language documents
**Goal**: Detect Czech PII — including the rodné číslo (birth number), domestic
bank account numbers, official document numbers and Czech-notation dates —
alongside the English model so that bilingual (EN + CS) documents are
handled correctly.

This recipe provides:

- `spacy_en_cs.yaml` — a ready-to-use NLP engine configuration that loads both
  `en_core_web_lg` and the multilingual `xx_ent_wiki_sm` (spaCy publishes no
  Czech-specific pretrained pipeline)
- An overview of all Czech-specific recognizers available in Presidio

## Quick Start

### Prerequisites

```bash
pip install presidio-analyzer presidio-anonymizer
python -m spacy download en_core_web_lg
python -m spacy download xx_ent_wiki_sm
```

### Sample Data

```python
sample_text = (
    "Jmenuji se Jan Novák a narodil jsem se dne 12. dubna 1985. "
    "Moje rodné číslo je 850412/0003. "
    "Kontaktovat mě můžete na telefonním čísle +420 601 234 567. "
    "Moje číslo občanského průkazu je 123456789 "
    "a číslo cestovního pasu je AB123456. "
    "Bankovní účet mám vedený pod číslem 19-123456789/0800. "
    "IBAN účtu je CZ6508000000192000145399."
)
```

### Basic Configuration

```python
from presidio_analyzer import AnalyzerEngine
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import (
    CzBankAccountRecognizer,
    CzBirthNumberRecognizer,
    CzDateRecognizer,
    CzDriverLicenseRecognizer,
    CzIdCardRecognizer,
    CzPassportRecognizer,
)
from presidio_anonymizer import AnonymizerEngine

# Load the bilingual EN + CS spaCy configuration
provider = NlpEngineProvider(conf_file="spacy_en_cs.yaml")
nlp_engine = provider.create_engine()

analyzer = AnalyzerEngine(
    nlp_engine=nlp_engine,
    supported_languages=["en", "cs"],
)

# The Czech recognizers ship disabled by default (upstream convention for
# non-default languages); register them for the Czech pipeline explicitly.
for recognizer in (
    CzBirthNumberRecognizer(),
    CzBankAccountRecognizer(),
    CzIdCardRecognizer(),
    CzPassportRecognizer(),
    CzDriverLicenseRecognizer(),
    CzDateRecognizer(),
):
    analyzer.registry.add_recognizer(recognizer)

anonymizer = AnonymizerEngine()

# Analyze Czech text
results = analyzer.analyze(text=sample_text, language="cs")
anonymized = anonymizer.anonymize(text=sample_text, analyzer_results=results)

print(anonymized.text)
```

Alternatively, enable the recognizers declaratively by copying
`default_recognizers.yaml` and flipping `enabled: true` on the `Cz*` entries.

## Approach

Presidio ships pattern-based recognizers for 5 Czech entity types plus Czech
`DATE_TIME` coverage (see table below). Each recognizer targets a single
entity, uses lookaround-anchored regex patterns with base confidence between
0.1 and 0.6, and relies on:

1. **Context words** (inflected Czech terminology near the match — the
   enhancer matches surface forms, so declensions like "účtu", "průkazu"
   are listed explicitly) to boost confidence
2. **Check digit validation** where the official specification defines one
   (rodné číslo mod 11, bank account weighted mod 11)

Identifiers that regularly collide with `PHONE_NUMBER` (rodné číslo such as
`850412/0003`, bank accounts such as `19-123456789/0800`) rely on the
combination of a higher base score and context boosting to win score-based
conflict resolution against the phone recognizer's flat 0.4 score.

The multilingual `xx_ent_wiki_sm` model adds named-entity recognition for
PERSON, LOCATION and ORGANIZATION on top of the pattern recognizers. Czech
dates ("12. dubna 1985") are covered by `CzDateRecognizer` because no Czech
NER model emitting DATE labels is available.

### Supported Czech Entities

| Entity | Name | Check digit |
|--------|------|-------------|
| `CZ_BIRTH_NUMBER` | Rodné číslo | ✅ mod 11 (§ 13 z. č. 133/2000 Sb.) |
| `CZ_BANK_ACCOUNT` | Číslo bankovního účtu | ✅ weighted mod 11 (vyhláška ČNB č. 169/2011 Sb.) |
| `CZ_ID_CARD` | Číslo občanského průkazu | – |
| `CZ_PASSPORT` | Číslo cestovního pasu | – |
| `CZ_DRIVER_LICENSE` | Číslo řidičského průkazu | – |
| `DATE_TIME` | Czech date notation (via `CzDateRecognizer`) | – |

## Results

Formal evaluation against a labelled Czech dataset has not yet been performed.
To benchmark this recipe follow the [Presidio Research evaluation workflow](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/4_Evaluate_Presidio_Analyzer.ipynb):

1. Generate synthetic Czech text with the [data generator](https://github.com/data-privacy-stack/presidio-research/blob/master/notebooks/1_Generate_data.ipynb)
2. Configure the analyzer with `spacy_en_cs.yaml`
3. Run the evaluator and report precision / recall / F₂ / latency

**Precision**: TBD
**Recall**: TBD
**F₂ Score**: TBD
**Latency**: TBD

### Key Findings

- Recognizers with check digit validation (rodné číslo, bank account) achieve
  very low false-positive rates on checksum-valid inputs, and deliberately
  keep checksum-failing but date-plausible matches at the base pattern score:
  many circulating rodná čísla predate the strict mod 11 rule, so context
  words decide those cases instead of a hard reject.
- Recognizers without a checksum (ID card, passport, driving licence)
  rely heavily on context words; setting `score_threshold=0.4` filters
  context-free digit strings effectively.
- Czech legal citations (`262/2006 Sb.`, `89/2012 Sb.`) share the `NNN/YYYY`
  shape with prefix-less bank accounts and are ubiquitous in legal text; the
  bank account recognizer invalidates prefix-less matches with a numerator of
  up to 3 digits and a year-like 1900–2099 "bank code", and never promotes a
  checksum pass over a year-like code the ČNB did not issue.
- `xx_ent_wiki_sm` ships without a lemmatizer, so the context enhancer
  compares surface forms. The bundled context word lists therefore contain
  the inflected forms that actually occur next to each identifier.

## Tips for Others

- **Set `score_threshold`** to 0.4–0.5 for production use to filter out
  low-confidence pattern-only matches from context-free digit strings.
- **Use the `entities` parameter** to limit detection to the entity types
  relevant to your domain (e.g. only `CZ_BIRTH_NUMBER` and `CZ_BANK_ACCOUNT`
  in banking correspondence).
- **Higher-quality Czech NER**: for better PERSON/LOCATION recall, switch to
  the `TransformersNlpEngine` with a Czech NER model from the HuggingFace hub
  (e.g. [`richielo/small-e-czech-finetuned-ner-wikiann`](https://huggingface.co/richielo/small-e-czech-finetuned-ner-wikiann),
  a Czech ELECTRA model fine-tuned on WikiANN) and keep the same
  `model_to_presidio_entity_mapping`. Stanza currently provides no Czech NER
  package either, so transformers is the recommended upgrade path.
- **Full street addresses** ("Václavské náměstí 123/45, 110 00 Praha 1") are
  only as good as the NER model's LOCATION spans; generic models often split
  them into street and city fragments. Add a custom address recognizer if
  your domain requires whole-address redaction.

---

**Author**: Data Privacy Stack contributors
**Date**: 2026-07-11
