# Changelog

All notable changes to this project will be documented in this file.

## [unreleased]
### Analyzer
#### Added

* Added `InUpiRecognizer` for detecting Indian UPI (Unified Payments Interface) payment IDs (Thanks @shauryaraghav)

### Analyzer
#### Added
- Added `UuidRecognizer` (generic, entity type `UUID`) to detect UUIDs in the standard 8-4-4-4-12 hyphenated hexadecimal format, covering RFC 4122 versions 1-5 and RFC 9562 versions 6-8. Validates version and variant nibbles and filters the nil UUID to reduce false positives.
- South African ID number (`ZA_ID_NUMBER`) recognizer for the 13-digit national identity number, using pattern matching, context words, birth-date validation, and Luhn checksum validation. Disabled by default.
- South African recognizers for `ZA_PASSPORT`, `ZA_INCOME_TAX_NUMBER`, `ZA_DRIVER_LICENSE`, `ZA_VAT_NUMBER`, `ZA_COMPANY_REGISTRATION`, `ZA_TRAFFIC_REGISTER_NUMBER`, `ZA_LICENSE_PLATE`, `ZA_MOBILE_NUMBER`, and `ZA_TELEPHONE_NUMBER`. All disabled by default.
- Added `NoOpNlpEngine` for configurations that do not require NLP engine artifacts, enabling standalone recognizers such as `HuggingFaceNerRecognizer` to run without a spaCy or Stanza model (#2071) (Thanks @ultramancode)
- Added per-recognizer and per-entity score threshold configuration in the recognizer registry YAML, with the analyzer's global `default_score_threshold` as the fallback (#2116) (Thanks @rodboev)
- Added `PhUmidRecognizer` for Philippine Unified Multi-Purpose ID (UMID/CRN) numbers in dashed and plain 12-digit formats; disabled by default (#2045) (Thanks @Surya-5555)

#### Changed
- The `kr` language code is deprecated in favor of the ISO 639-1 code `ko`. `KrRrnRecognizer` and `KrPassportRecognizer` still accept `kr` in `supported_languages` as a backward-compatibility alias for registries configured against their original class defaults; the alias will be removed in <release TBD>. `KrBrnRecognizer`, `KrDriverLicenseRecognizer` and `KrFrnRecognizer` have only ever defaulted to `ko`, so `kr` was removed from their `default_recognizers.yaml` entries in this release. (#2236)

#### Fixed
- `PhoneRecognizer.DEFAULT_SUPPORTED_REGIONS` used `"UK"`, which is not a valid `phonenumbers` (libphonenumber) region code — region codes are ISO 3166-1 alpha-2, where the United Kingdom is `"GB"`. The `"UK"` entry was a no-op, so UK numbers in national/local format (e.g. `020 7946 0958`) were never detected by default; only international-format `+44 …` numbers matched, because they carry the country code and match under any region. Replaced `"UK"` with `"GB"`.
- Language model recognizers (`BasicLangExtractRecognizer`, `AzureOpenAILangExtractRecognizer`) configured in a recognizer registry YAML now honour `config_path` (and other recognizer-specific kwargs). Previously these entries were validated by the strict `PredefinedRecognizerConfig` schema, which has no `config_path` field and does not allow extra keys, so `config_path` was silently dropped and the recognizer fell back to its bundled default model configuration. Added a `LangExtractRecognizerConfig` model (`extra="allow"`) and registered both recognizer class names in `CONFIG_MODEL_MAP`.
- `BasicLangExtractRecognizer` now honours values under `langextract.model.provider.language_model_params` (including `timeout` and `num_ctx`). Previously these were silently dropped because `langextract.extract()` ignores its `language_model_params` argument when a pre-built `ModelConfig` is passed via `config=`, causing Ollama-backed recognizers to fall back to langextract's 120s default regardless of the configured timeout. The recognizer now merges `language_model_params` into `ModelConfig.provider_kwargs`, which is the path that reaches the provider constructor. Explicit entries under `provider.kwargs:` still take precedence. Also fixed a `TypeError` when `kwargs:` or `language_model_params:` is `null` in the YAML. (#1943, Thanks @lsternlicht)
- Fixed `UsSsnRecognizer` over-blocking valid SSNs in the `987654320`-`987654329` range due to an 8-digit instead of full 9-digit prefix in the sample-SSN denylist check (#2074) (Thanks @AUTHENSOR)
- Fixed `FiHetuRecognizer` and `SgUenRecognizer` dropping valid lower-case identifiers by normalizing the check character to upper case before checksum comparison (#2141) (Thanks @uwezkhan)
- Fixed `FiHetuRecognizer` incorrectly accepting 29 Feb on non-leap century years by deriving the full 4-digit year from the century-separator character before date validation (#2111) (Thanks @jichaowang02-lang)
- Fixed `EsNieRecognizer.validate_result` always passing the digit guard because `isdigit` was referenced instead of called, raising a `TypeError` for invalid inputs instead of returning `False` (#2146) (Thanks @MohamedAklamaash)
- Fixed `DateRecognizer` ISO 8601 pattern accepting impossible month/day values such as month 00, 13-19 or day 00, 32-39 (#2113) (Thanks @jichaowang02-lang)
- Fixed `EsNifRecognizer` and `EsNieRecognizer` dropping valid lowercase Spanish identifiers by upper-casing the check letter before the mod-23 checksum (#2076) (Thanks @AUTHENSOR)
- Fixed `AuAbnRecognizer` checksum incorrectly remapping a leading-zero first digit to 9 instead of subtracting 1 per the official ABR algorithm (#2109) (Thanks @jichaowang02-lang)
- Fixed `NgNinRecognizer` rejecting valid NIINs with a leading zero caused by `int()` conversion stripping the leading zero before Verhoeff checksum validation (#2106) (Thanks @jichaowang02-lang)
- Fixed Thai TNIN pattern rejecting valid province codes 22, 52, and 58 due to over-narrow character-class ranges (#2107) (Thanks @jichaowang02-lang)
- Fixed `FiHetuRecognizer` pattern accepting illegal century separators because `+-A` in the character class was interpreted as a range rather than three separate literals (#2108) (Thanks @jichaowang02-lang)
- Fixed `InVehicleRegistrationRecognizer` under-scoring valid registrations with zero-padded district codes by normalizing to a two-digit string before the district map lookup (#2110) (Thanks @jichaowang02-lang)
- Fixed `UkNinoRecognizer` pattern matching a numeric suffix character, producing false positives such as `AB 12 34 56 1`, caused by `{1}` quantifier placed inside the character class (#2112) (Thanks @jichaowang02-lang)
- Fixed `DeFuehrerscheinRecognizer` docstring example that contradicted the recognizer's own regex and tests (#2138) (Thanks @jichaowang02-lang)
- Fixed documentation incorrectly stating that `IpRecognizer` validates a checksum (#2133) (Thanks @Coshea46)

#### Added
- Philippine passport (`PH_PASSPORT`) recognizer with pattern matching and context support. Disabled by default.

### Anonymizer
#### Security
- Bumped `cryptography` lower bound to `>=48.0.1` to resolve GHSA-537c-gmf6-5ccf (HIGH, vulnerable OpenSSL statically linked into wheels below 48.0.1) (#2144) (Thanks @Copilot)

### General
#### Added
- Added `BatchDeanonymizeEngine` to complement `BatchAnonymizerEngine` for batch deanonymization over lists and nested dictionaries.
- Added a `--threshold` flag to `presidio-cli` to override the analyzer confidence threshold directly from the command line (#2114) (Thanks @rodboev)

#### Changed
- Migrated CI and service-image dependency installation from Poetry to [uv](https://github.com/astral-sh/uv) with committed lockfiles, fixing prolonged dependency-resolution hangs and making builds reproducible.
- Added Python 3.14 package support for `presidio-anonymizer`, `presidio-image-redactor`, `presidio-cli`, `presidio-structured`, and `presidio` by allowing Python `<3.15` and excluding `spacy==3.8.14` on Python 3.14 where applicable (#2096) (Thanks @Copilot)
- Added `healthcheck` and `restart: unless-stopped` policies to all services in `docker-compose.yml` so containers auto-recover on crash and report readiness (#2149) (Thanks @hiro-nikaitou)
- Updated the `LICENSE` file copyright from "Microsoft Corporation" to "Presidio Contributors" (#2134) (Thanks @cobypeled)
- Replaced `presidio@microsoft.com` author email with `presidio@dataprivacystack.org` in all package `pyproject.toml` files (#2128) (Thanks @Copilot)
- Improved CI stability by optimizing disk usage, pinning the Ollama Docker image to a specific version, and running Ollama end-to-end tests on arm64 runners (#2167) (Thanks @SharonHart)
- Updated mobile homepage layout with a compact mascot for smaller screens (#2130) (Thanks @SharonHart)

#### Fixed
- Retried the Zensical documentation build on transient crashes (e.g. SIGKILL/exit 247) so the docs release pipeline no longer fails intermittently (Thanks @Copilot)
- Fixed NLP engine initialization in the GLiNER usage sample (#2135) (Thanks @matteobachini-vianova)
- Quoted `pip install` extras examples in documentation to prevent shell expansion of bracket expressions (#2093) (Thanks @nyxst4ck)

## [2.2.363] - 2026-06-28
### General
#### Added
- Optional `countries` filter on `RecognizerRegistry.load_predefined_recognizers()` to scope predefined country-specific recognizers to a subset of locales (e.g. `countries=["us", "uk"]`). The same filter is also exposed as a top-level `supported_countries` field in the recognizer-registry YAML, mirroring `supported_languages`, and as an advisory per-recognizer `country_code:` field on every predefined country-specific entry in `default_recognizers.yaml` (cross-checked against the class attribute at load time). Country tagging works via two reconciled paths: the class-level `EntityRecognizer.COUNTRY_CODE` ClassVar (canonical for predefined recognizers) and the new `country_code` constructor kwarg on `EntityRecognizer` / `PatternRecognizer` (the path for custom recognizers without a subclass — flows through `PatternRecognizer.from_dict` so YAML `type: custom` entries can declare `country_code:` directly). Conflicting values raise `ValueError` at construction time so a predefined country recognizer can never be silently re-tagged. The resolved tag is read via the `country_code()` and `is_country_specific()` instance methods, and serialized through `to_dict()` / `from_dict()` for round-tripping. Inputs to the `countries` filter are validated up front (rejects bare strings, non-iterables, non-string elements, and blank codes). Locale-agnostic recognizers and untagged custom recognizers are always loaded regardless of the filter, preserving backwards compatibility. Adds `RecognizerRegistry.get_country_codes()` for introspection and a `WARNING` log when a requested country has no matching recognizer. See `docs/analyzer/filtering_by_country.md`. Fixes #1328.
- Published source distributions alongside wheels in the PyPI release pipeline (#1924) (Thanks @Copilot)

#### Changed
- Rebranded repository documentation and links for Data Privacy Stack, added project transition notices about Presidio's move to its new home at https://presidio.dataprivacystack.org/project_transition/, migrated the docs site to Material for MkDocs/Zensical, and updated docs publishing and search verification workflows (#2097, #2098, #2100, #2102, #2104, #2117, #2118, #2119, #2120, #2121, #2122) (Thanks @omri374, @SharonHart)
- Moved container image publishing from Microsoft Container Registry to GitHub Container Registry under `ghcr.io/data-privacy-stack`, updated Docker usage documentation, and fixed GHCR authentication and provenance publishing in CI (#2103, #2123, #2124) (Thanks @SharonHart, @Copilot)
- Updated Dependabot coverage and grouping for package, Docker, Docker Compose, and GitHub Actions dependencies, with defensive dependency range controls (#1928, #1929, #1965, #1984, #2005) (Thanks @dependabot, @Copilot, @SharonHart)
- Updated GitHub Actions dependencies, Docker base images, and sample dependency pins across CI/release workflows (#1913, #1914, #1915, #1920, #1927, #1935, #1936, #1937, #1938, #1966, #1967, #1968, #1975, #1976, #1985, #1991, #1996) (Thanks @dependabot)
- Updated Copilot development instructions for the repository (#1866) (Thanks @omri374)

#### Fixed
- Skipped the coverage PR-comment step outside pull request runs to prevent CI failures on push and workflow-dispatch runs (#1921) (Thanks @Copilot)
- Cleaned stale Poetry virtual environments during CI reruns to avoid mixed NumPy installs and `IndentationError` failures (#2091) (Thanks @Copilot)
- Fixed OpenAI anonymization sample typos, Fabric sample dependency guidance, and duplicate ZIP-code example documentation (#2017, #2027, #2034) (Thanks @ynachiket, @BelizSertcan)

### Analyzer
#### Added
- Recognizer registry YAML entries now accept `score_thresholds` for recognizer-wide and entity-specific score cutoffs, with the analyzer's `default_score_threshold` as the fallback.
- UK Driving Licence Number (`UK_DRIVING_LICENCE`) recognizer with pattern matching and context support (#1857) (Thanks @tee-jagz)
- German PII recognizers for `DE_TAX_ID`, `DE_TAX_NUMBER`, `DE_PASSPORT`, `DE_ID_CARD`, `DE_SOCIAL_SECURITY`, `DE_HEALTH_INSURANCE`, `DE_KFZ`, `DE_HANDELSREGISTER`, and `DE_PLZ`; all are disabled by default (#1909) (Thanks @MvdB)
- `SE_PERSONNUMMER` recognizer for Swedish personal identity and coordination numbers, plus Swedish Organisationsnummer recognition; both are disabled by default (#1912, #1918) (Thanks @goveebee)
- `SlimSpacyNlpEngine` and slim analyzer configs, enabling lightweight tokenization/lemmatization while delegating NER to recognizers such as GLiNER (#1916) (Thanks @SharonHart)
- Canadian SIN (`CA_SIN`) recognizer with English/French context and Luhn checksum validation (#1934) (Thanks @kennionblack)
- Turkish recognizers for `TR_NATIONAL_ID`, `TR_LICENSE_PLATE`, and `TR_PHONE_NUMBER`; all are disabled by default (#1995, #1999, #2006) (Thanks @mrcuren)
- Spanish Passport (`ES_PASSPORT`) recognizer (#2011) (Thanks @asensionacher)
- Optional `countries` filter for `RecognizerRegistry.load_predefined_recognizers()`, country metadata on predefined/custom recognizers, country-code introspection, and YAML `supported_countries` support (#2000) (Thanks @ynachiket)
- Configurable `supported_entity` support in `PhoneRecognizer`, including correct propagation to recognizer results (#2014) (Thanks @max-tarlov-infinitusai)
- Philippines TIN (`PH_TIN`) and Philippine mobile number (`PH_MOBILE_NUMBER`) recognizers; both are disabled by default (#2016, #2038) (Thanks @aaronaco, @Surya-5555)
- South African ID number (`ZA_ID_NUMBER`) recognizer with birth-date and Luhn validation; disabled by default (#2064) (Thanks @thatomokoena)

#### Changed
- Consolidated analyzer configuration into a single `analyzer.yaml` flow while preserving the older config files with deprecation banners (#1970) (Thanks @SharonHart)
- Added Python 3.14 package support for `presidio-analyzer` by allowing Python `<3.15` and avoiding `spacy==3.8.14`, which does not provide compatible Python 3.14 wheels (#2105) (Thanks @michaelgiraldo)
- Updated analyzer dependencies and metadata for `stanza`, `gliner`, `spacy-huggingface-pipelines`, `pydantic`, `pyyaml`, `azure-ai-textanalytics`, `azure-core`, `phonenumbers`, `tldextract`, `azure-identity`, `numpy`, and explicit `click` support (#1979, #1981, #1982, #1987, #1988, #1989, #1992, #1993, #1994, #2001, #2058, #2090, #2092) (Thanks @dependabot, @Copilot, @SharonHart)

#### Fixed
- Resolved LangExtract configuration path loading for installed PyPI packages (#1917) (Thanks @RonShakutai)
- Fixed analyzer Docker configuration handling and Stanza model accessibility (#1930) (Thanks @TheSabari07)
- Improved IP recognizer regexes and regression coverage for IPv4-mapped/embedded and compressed IPv6 edge cases (#1941, #1940, #2062) (Thanks @kennionblack, @extrasmall0, @AlexanderSanin)
- Corrected German recognizer checksum and structural validation for KVNR, RVNR, LANR, VAT ID, passport/ID MRZ checksums, BSNR, tax IDs, and default registry coverage (#1990) (Thanks @MvdB)
- Fixed Polish PESEL checksum validation (#1998) (Thanks @sienioApius)
- Fixed `PhoneRecognizer` default region typo from `FE` to `FR` (#2009) (Thanks @Copilot)
- Preserved GLiNER and recognizer-specific configuration fields through Pydantic validation and config serialization (#2007, #2081) (Thanks @yuriihavrylko, @ultramancode)
- Ignored empty allow-list terms in regex matching (#2061) (Thanks @uwezkhan)
- Capped URL recognizer host matching to avoid quadratic backtracking (#2063) (Thanks @uwezkhan)
- Fixed Singapore UEN detection for Format C identifiers with the `R` prefix (#2088) (Thanks @jichaowang02-lang)
- Fixed Australian ACN checksum validation for valid ACNs whose check digit is `0` (#2087) (Thanks @jichaowang02-lang)
- Added missing IBAN registry formats for EG, IQ, LY, LC, SC, and UA (#2078) (Thanks @AUTHENSOR)
- Matched punycode/IDN domains in email recognition so internationalized email addresses are detected (#2077) (Thanks @AUTHENSOR)
- Updated URL recognizer test bounds for Data Privacy Stack domains (#2125) (Thanks @SharonHart)

### Anonymizer
#### Added
- Added `merge_entities_with_whitespace` support to `anonymize()` so adjacent analysis results can be merged across whitespace before anonymization (#1932) (Thanks @harishkernel)

#### Changed
- Updated the optional Azure Identity dependency for anonymizer AHDS support (#1983) (Thanks @dependabot)

#### Fixed
- Custom operator `validate()` no longer calls the user-supplied lambda with a dummy `"PII"` value. Previously, stateful lambdas accumulating a token-to-original-value map for de-anonymization would receive a spurious validation invocation, inserting a junk entry and skewing later token counters. The return-type contract is now enforced in `operate()` when the lambda runs on real data (#2025) (Thanks @HammadSiddiqui)

### Image Redactor
#### Added
- Added Azure SDK credential support to `DocumentIntelligenceOCR` so callers can use Azure Identity credentials instead of API keys (#2085) (Thanks @mturac)

#### Changed
- Updated image-redactor dependencies for `opencv-python`, `gunicorn`, `pytesseract`, and `azure-ai-formrecognizer` (#1978, #1977, #1980, #1986) (Thanks @dependabot)

#### Fixed
- Returned the rendered image when no text is detected during image-redactor verification (#2040) (Thanks @AlexanderSanin)
- Fixed duplicate entity sorting in the DICOM verification engine and removed double bounding-box formatting in `eval_dicom_instance` (#2084, #2079) (Thanks @ArjunPakhan, @AlexanderSanin)
- Fixed an undefined variable in the Document Intelligence OCR setup example in the image-redactor documentation (#2089) (Thanks @Dashtid)

### Presidio-Structured
#### Changed
- Added an explicit `click` dependency to package metadata (#2058) (Thanks @Copilot)

## [2.2.362] - 2026-03-15
### General
#### Added
- Published `presidio` as a PyPI meta-package that installs `presidio-analyzer` and `presidio-anonymizer`, making `pip install presidio` work as expected. Inspired by and thanks to Sakthi Santhosh Anumand and Harsha Vardhan for the original idea. (#1889) (Thanks @Copilot)

#### Changed
- Pinned all CI/CD GitHub Actions and Docker base images to commit SHAs to mitigate supply chain attacks (#1861) (Thanks @Copilot)
- Pinned `ruff` and `build` pip installs with SHA256 hashes for OSSF scorecard compliance (#1864) (Thanks @Copilot)
- Updated GitHub Actions dependencies (`actions/checkout`, `actions/setup-python`, `actions/setup-dotnet`, `actions/cache`, `actions/github-script`, `actions/dependency-review-action`, `azure/login`, `docker/setup-buildx-action`, `github/codeql-action`, `microsoft/security-devops-action`) and base Python Docker images (#1870, #1871, #1872, #1873, #1874, #1875, #1876, #1877, #1878, #1879, #1885, #1886, #1887, #1895, #1896, #1897, #1898) (Thanks @dependabot)
- Updated README to clarify Presidio's no-authentication-by-design stance with security guidance (#1903) (Thanks @Copilot)

#### Fixed
- Broken documentation links (#1856) (Thanks @andyjessen)

#### Security
- Fixed CVE-2024-47874 and CVE-2025-54121 (Starlette vulnerabilities) (#1860) (Thanks @SharonHart)
- Fixed CVE-2025-2953 and CVE-2025-3730 (#1859) (Thanks @SharonHart)

### Analyzer
#### Added
- `HuggingFaceNerRecognizer` for direct NER model inference using HuggingFace pipelines without requiring spaCy (#1834) (Thanks @ultramancode)
- Transformer-based `MedicalNERRecognizer` as a subclass of `HuggingFaceNerRecognizer` for clinical entity detection (#1853) (Thanks @stevenelliottjr)
- US NPI (National Provider Identifier) recognizer with Luhn checksum validation and context support (#1847) (Thanks @stevenelliottjr)
- UK Postcode (UK_POSTCODE) recognizer with pattern matching and context support (#1858) (Thanks @tee-jagz)
- UK Passport (UK_PASSPORT) and Vehicle Registration (UK_VEHICLE_REGISTRATION) recognizers (#1862) (Thanks @tee-jagz)
- Nigerian National Identification Number (NG_NIN) recognizer with Verhoeff checksum validation and Nigerian Vehicle Registration (NG_VEHICLE_REGISTRATION) recognizer (#1863) (Thanks @tee-jagz)
- ONNX Runtime backend support for `GLiNERRecognizer` via `load_onnx_model=True` parameter, resolving crashes on CPUs without AVX2 support (#1884) (Thanks @Copilot)
- Configurable regex execution timeout (default 60 seconds) via `REGEX_TIMEOUT_SECONDS` environment variable to prevent catastrophic backtracking (#1904) (Thanks @Copilot)
- GPU device control via environment variable for explicit GPU/CPU selection (#1844) (Thanks @RonShakutai)
- LLM-as-a-judge evaluation integration for assessing PII detection quality (#1900) (Thanks @RonShakutai)
- Sampling support for the evaluation framework (#1894) (Thanks @RonShakutai)
- Dataset interface for the evaluation framework (#1893) (Thanks @RonShakutai)

#### Fixed
- Erroneous anchor in Italian driver license regex that caused missed matches (#1899) (Thanks @Br1an67)
- `validation_result` type annotation in API docs and type hints (#1869) (Thanks @akios-ai)
- Bare `except` clauses replaced with `except Exception` for proper exception handling (#1881) (Thanks @haosenwang1018)
- Context enhancement substring matching bug where context words were incorrectly matched as substrings (#1827) (Thanks @ravi-jindal)

### Image Redactor
#### Fixed
- `_process_names` unconditionally treating all DICOM metadata as PHI; now correctly filters using both `is_patient` and `is_name` checks (#1855) (Thanks @Mr-Neutr0n)

## [2.2.361] - 2026-02-12
### Analyzer
#### Changed
- Fixed context enhancement substring matching bug where context words were incorrectly matched as substrings (e.g., 'lic' matching 'duplicate'). Added configurable `context_matching_mode` parameter to `LemmaContextAwareEnhancer` with two options: "substring" (default, maintains backward compatibility for compound words like "creditcard"), and "whole_word" (prevents false positives like 'lic' matching 'duplicate') (#1061)

#### Added
- US_MBI recognizer for Medicare Beneficiary Identifier with pattern matching and context support (#1821) (Thanks @chrisvoncsefalvay)
- MAC address recognizer for detecting MAC addresses in various formats (#1829) (Thanks @kyoungbinkim)
- Korean Business Registration Number (KR_BRN) recognizer (#1822) (Thanks @RektPunk)
- Korean Foreigner Registration Number (KR_FRN) recognizer (#1825) (Thanks @RektPunk)
- Korean Driver License (KR_DRIVER_LICENSE) recognizer (#1820) (Thanks @RektPunk)
- Korean Passport (KR_PASSPORT) recognizer (#1814) (Thanks @kyoungbinkim)
- Thai National ID Number (TH_TNIN) recognizer with format and checksum validation (#1713) (Thanks @pangchewe)
- Configurable LangExtract recognizer supporting any LLM provider with custom YAML configurations (#1815) (Thanks @telackey)
- Azure OpenAI support for LangExtract recognizer with managed identity authentication for GPT-4o, GPT-4, etc. (#1801) (Thanks @dorlugasigal)
- Batch processing support in REST API - accepts arrays of texts and returns arrays of results with backward compatibility (#1806) (Thanks @telackey)
- GPU device control via `PRESIDIO_DEVICE` environment variable for explicit GPU/CPU selection (#1843) (Thanks @RonShakutai)
- Support for multiple recognizer instances from same class via `class_name` parameter (#1819) (Thanks @RonShakutai)
- Pydantic-based YAML configuration validation with ConfigurationValidator class for improved reliability and error reporting (#1780) (Thanks @omri374)
- Japanese and Chinese mobile number test cases for PhoneRecognizer (#1808) (Thanks @WenwenHLF)

#### Changed
- GPU optimizations with DeviceDetector singleton providing 4-10x performance improvements for GLiNER, Transformers, and Stanza engines (#1812) (Thanks @RonShakutai)
- Configurable extraction parameters for LangExtract recognizers via YAML (max_char_buffer, timeout, num_ctx, fence_output, use_schema_constraints) (#1811) (Thanks @RonShakutai)
- Lazy initialization for device detector singleton (#1831) (Thanks @RonShakutai)
- Simplified IBAN regex pattern from 8 to 3 capture groups for better performance (#1818) (Thanks @Copilot)
- Improved Korean RRN regex pattern with negative lookahead/lookbehind and gender digit validation (#1807) (Thanks @kyoungbinkim)

#### Fixed
- GLiNER GPU inference by properly passing map_location parameter (#1813) (Thanks @eveningcafe)
- GLiNER text truncation issue during processing (#1805) (Thanks @jedheaj314)
- IBAN regex trailing character handling to prevent false matches (#1818) (Thanks @Copilot)
- Python 3.10 build compatibility by pinning onnxruntime <1.24.1 for Python 3.10 (#1848) (Thanks @SharonHart)
- TypeError in third-party recognizers by removing invalid **kwargs from __init__ methods (#1800) (Thanks @RonShakutai)
- Pattern recognizer example language specification (#1835) (Thanks @andyjessen)

### Anonymizer
#### Changed
- **BREAKING CHANGE**: Hash operator now uses random salt by default to prevent brute-force and dictionary attacks. Same PII values will produce different hashes unless a `salt` parameter is explicitly provided. Users requiring referential integrity must provide their own salt. Minimum salt length: 16 bytes. See documentation for migration guide. (#1846) (Thanks @Copilot)
- Updated cryptography dependency to >=46.0.4 to address CVE-2025-15467 security vulnerability (#1841) (Thanks @Copilot)

### General
#### Added
- GPU acceleration documentation guide with setup and usage instructions (#1826) (Thanks @dilshad-aee)
- Telemetry redaction sample demonstrating PII removal from telemetry data (#1824) (Thanks @Jakob-98)

#### Changed
- Migrated CI workflows (lint, dependency review, release) to ubuntu-slim runners for improved efficiency (#1840) (Thanks @Copilot)
- Updated actions/cache from v4 to v5 with Node.js 24 runtime support (#1817) (Thanks @dependabot)

### Image Redactor
#### Changed
- DICOM: use_metadata will now use both is_patient and is_name to generate the PHI list of words via change to _make_phi_list.
- Image Redactor: Added redact_and_return_bbox method to ImageRedactorEngine, which returns both the redacted image and the detected bounding boxes for redacted regions.

## [2.2.360] - 2025-09-09
### Analyzer
#### Added
- Korean Resident Registration Number (RRN) recognizer with checksum validation for numbers issued prior to October 2020 (#1675) (Thanks @siwoo-jung)
- Azure Health Data Services (AHDS) de-identification service integration as a remote recognizer with Entra ID authentication (#1624) (Thanks @rishasurana)
- Comprehensive input validation methods for NlpEngineProvider to ensure valid arguments for engines, configuration, and file paths (#1653) (Thanks @siwoo-jung)

#### Changed
- Updated Indian Aadhaar recognizer to support contextual delimiters (-, :, space) for improved detection accuracy (#1677) (Thanks @K3y5tr0ke)
- Fixed Italian Driver License recognizer regex to include missing characters per government requirements, excluding only A, O, Q, I (#1651) (Thanks @K3y5tr0ke)
- Refactored recognizers folder structure for better organization and maintainability (#1670) (Thanks @omri374)

### Anonymizer
#### Added
- Azure Health Data Services (AHDS) Surrogate anonymization operator with medical domain expertise for realistic PHI surrogate generation (#1672) (Thanks @rishasurana)

#### Changed
- Fixed code indentation issues in encrypt.py for better code quality (#1660) (Thanks @aliyss)

### General
#### Added
- Comprehensive GitHub Copilot instructions with development guidelines, build processes, and e2e testing procedures (#1693) (Thanks @Copilot)
- New GitHub Actions CI & release workflows with multi-platform Docker image support for AMD64 and ARM64 architectures (#1697) (Thanks @tamirkamara)
- Dual-path CI workflow to fix GitHub Actions failures for external contributors by auto-detecting fork vs. main repository PRs (#1708) (Thanks @Copilot)
- OIDC trusted publishing for PyPI releases eliminating manual API token management and enhancing security (#1702) (Thanks @Copilot)
- Comprehensive YAML and Python examples for context-aware recognizers documentation (#1710) (Thanks @MRADULTRIPATHI)

#### Changed
- Updated actions/checkout from v4 to v5 to support Node.js 24 runtime (#1699) (Thanks @dependabot)
- Fixed PR template to use proper GitHub issue linking syntax for automatic issue association and closing (#1701) (Thanks @Copilot)
- Updated LiteLLM documentation with detailed guide links for better integration guidance (#1698) (Thanks @BhargavDT)
- Fixed broken links in CONTRIBUTING.md and developing recognizers documentation after recognizers refactoring (#1674) (Thanks @siwoo-jung)
- Fixed OpenSSF badge embedding in README.MD for proper display (#1673) (Thanks @SharonHart)
- Removed Terrascan from Microsoft Defender for DevOps workflow to eliminate false positives on non-IAC repository (#1691) (Thanks @Copilot)

#### Security
- Updated Streamlit and PyTorch dependency versions to fix CVE vulnerabilities (#1685) (Thanks @SharonHart)
- Updated requests library to mitigate security vulnerability GHSA-9hjg-9r4m-mvj7 (#1683) (Thanks @SharonHart)
- Locked pandas dependency in Streamlit to prevent version conflicts (#1689) (Thanks @SharonHart)

## [2.2.359] - 2025-07-06
### Analyzer
- Allow loading of StanzaRecognizer when StanzaNlpEngine is configured, improving NLP engine flexibility (#1643) (Thanks @omri374)
- Excluded recognition_metadata attribute from REST Analyze Response DTO to clean up API responses (#1627) (Thanks @SharonHart)
- Added ISO 8601 support to DateRecognizer for improved date parsing (#1621) (Thanks @StefH)
- Prevented misidentification of 13-digit timestamps as credit cards (#1609) (Thanks @eagle-p)
- Updated analyzer_engine_provider.md for clarity and completeness (#1590) (Thanks @AvinandanBandyopadhyay)
- Bumped python from 3.9 to 3.12 in presidio-analyzer Dockerfile (#1583) (Thanks @dependabot)
- Bumped phonenumbers version for improved validation and parsing (#1579) (Thanks @omri374)
- Refactored InstanceCounterAnonymizer to simplify index retrieval logic (#1577) (Thanks @ShakutaiGit)
- Fixed issue #1574 to support as_tuples in relevant functions (#1575) (Thanks @omri374)
- Updated initial scores in IN_PAN for better recognition performance (#1565) (Thanks @omri374)
- Added accelerate as a missing build dependency to fix build failures (#1564) (Thanks @SharonHart)
- Don't set a default for LABELS_TO_IGNORE if not specified, to avoid unintended behavior (#1563) (Thanks @SharonHart)
- Updated 08_no_code.md for documentation improvements (#1561) (Thanks @alan-insam)
- Added the ability to disable the NLP recognizer via configuration (#1558) (Thanks @omri374)
- Removed 'class' from API documentation for clarity (#1554) (Thanks @omri374)
- Set country-specific default recognizers to enabled=false for safer defaults (#1586) (Thanks @omri374)
- Most country specific recognizers that expect English were put as optional to avoid false positives, and would not work out-of-the-box (#1586). Specifically:
    - SgFinRecognizer
    - AuAbnRecognizer
    - AuAcnRecognizer
    - AuTfnRecognizer
    - AuMedicareRecognizer
    - InPanRecognizer
    - InAadhaarRecognizer
    - InVehicleRegistrationRecognizer
    - InPassportRecognizer
    - EsNifRecognizer
    - InVoterRecognizer

  To re-enable them, either change the [default YAML](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/conf/default_recognizers.yaml) to have them as `enabled: true`, or via code, add them to the recognizer registry manually.
    - Yaml based: see more here: [YAML based configuration](https://presidio.dataprivacystack.org/analyzer/analyzer_engine_provider/).
    - Code based:
      ```py
      from presidio_analyzer import AnalyzerEngine
      from presidio_analyzer.predefined_recognizers import AuAbnRecognizer
      
      # Initialize an analyzer engine with the recognizer registry
      analyzer = AnalyzerEngine()
      
      # Create an instance of the AuAbnRecognizer
      au_abn_recognizer = AuAbnRecognizer()
      
      # Add the recognizer to the registry
      analyzer.registry.add_recognizer(au_abn_recognizer)
      ```

### Anonymizer
- Update python base image to 3.13 (#1612) (Thanks @dependabot[bot])
- Bumped python from 3.12-windowsservercore to 3.13-windowsservercore in presidio-anonymizer Dockerfile (#1612) (Thanks @dependabot)
- Ensured anonymizer sorts analyzer results input by start and end for correct whitespace merging (#1588) (Thanks @mkh1991)
- Bumped python from 3.9 to 3.12 in presidio-anonymizer Dockerfile (#1582) (Thanks @dependabot)

### Image Redactor
- Bumped python from 3.12-slim to 3.13-slim in presidio-image-redactor Dockerfile (#1611) (Thanks @dependabot)
- Bumped python from 3.10 to 3.12 in presidio-image-redactor Dockerfile (#1581) (Thanks @dependabot)

### General
- Fixed typographical errors in documentation files for better clarity (#1637) (Thanks @kilavvy)
- Corrected spelling mistakes across code comments and documentation for improved readability (#1636) (Thanks @leopardracer)
- Fixed typos in documentation and test descriptions, enhancing clarity and consistency in the codebase (#1631) (Thanks @zeevick10)
- Corrected typos in docstrings and comments to maintain documentation quality (#1630) (Thanks @kilavvy)
- Fixed typos in documentation and test descriptions, ensuring accurate references and descriptions (#1628) (Thanks @leopardracer)
- Removed unnecessary run.bat script from the repository (#1626) (Thanks @SharonHart)
- Added "/TestResults" to .gitignore file to prevent test result artifacts from being committed (#1622) (Thanks @StefH)
- Added links to the discussion board about Docker prebuilt images to documentation (#1614) (Thanks @omri374)
- Fixed spelling, grammar, and style issues in Presidio V2 documentation (#1610) (Thanks @Vruddhi18)
- Updated .gitignore to include the .vs folder (#1608) (Thanks @StefH)
- Fixed typo in api-docs.yml to improve documentation accuracy (#1602) (Thanks @StefH)
- Reverted a previous update to codeql-analysis.yml to restore earlier configuration (#1595) (Thanks @SharonHart)
- Updated codeql-analysis.yml for improved code scanning configuration (#1594) (Thanks @SharonHart)
- Fixed paths-ignore in codeql-analysis.yml to refine scanning scope (#1593) (Thanks @SharonHart)
- Ignored docs/ directory in CodeQL analysis to prevent unnecessary scanning (#1592) (Thanks @SharonHart)
- Fixed minor typos in code and documentation (#1585) (Thanks @omahs)
- Restored dependabot scanning for security and dependency updates (#1580) (Thanks @SharonHart)
- Added SUPPORT.md file to provide support information to users (#1568) (Thanks @omri374)

## [2.2.358] - 2025-03-18

### Analyzer
- Fixed: Updated URL regex pattern to correctly exclude trailing single (') and double (") quotes from matched URLs.
- Drop dependency of spacy_stanza package, and add supporting code to stanza_nlp_engine, to support recent stanza versions
- Add parameters to allow users to define the number of processes and batch size when running BatchAnalyzerEngine.
- Fix InPassportRecognizer regex recognizer
  
### Anonymizer
- Changed: Deprecate `MD5` hash type option, defaulting into `sha256`.
- Replace crypto package dependency from pycryptodom to cryptography 
- Remove azure-core dependency from anonymizer
  
### Image Redactor
- Changed: Updated the return type annotation of `ocr_bboxes` in `verify_dicom_instance()` from `dict` to `list`.  

### Presidio Structured

### General
- Updated the `Evaluating DICOM Redaction` documentation to reflect changes in verify_dicom_instance() within the DicomImagePiiVerifyEngine class.

## [2.2.357] - 2025-01-13

### Analyzer
- Example GLiNER integration (#1504)

### General
- Docs revamp and docstring bug fixes (#1500)
- Minor updates to the mkdocstrings config (#1503)

## [2.2.356] - 2024-12-15

### Analyzer
- Added logic to handle phone numbers with country code (#1426) (Thanks @kauabh)
- Added UK National Insurance Number Recognizer (#1446) (Thanks @hhobson)
- Fixed regex match_time output (#1488) (Thanks @andrewisplinghoff)
- Added fix to ensure configuration files are closed properly when loading them (#1423) (Thanks @saulbein)
- Closing handles for YAML file (#1424) (Thanks @roeybc)
- Reduce memory usage of Analyzer test suite (#1429) (Thanks @hhobson)
- Added `batch_size` parameter to `BatchAnalyzerEngine` (#1449) (Thanks @roeybc)
- Remove ignored labels from supported entities (#1454) (Thanks @omri374)
- Update US_SSN CONTEXT and unit test (#1455) (Thanks @claesmk)
- Fixed bug with Azure AI language context (#1458) (Thanks @omri374)
- Add support for allow_list, allow_list_match, regex_flags in REST API (#1484) (Thanks @hdw868)
- Add a link to model classes to simplify configuration (#1472) (Thanks @omri374)
- Restricting spacy.cli for version 3.7.0 (#1495) (Thanks @kshitijcode)

### Anonymizer
- No changes specified for Anonymizer in this release.


### Presidio-Structured
- Fix presidio-structured build - lock numpy version (#1465) (Thanks @SharonHart)


### Image Redactor
- Fix bug with image conversion (#1445) (Thanks @omri374)

### General
- Removed Python 3.8 support (EOL) and added 3.12 (#1479) (Thanks @omri374)
- Update Docker build to use gunicorn for containers (#1497) (Thanks @RKapadia01)
- New Dev containers for analyzer, analyzer+transformers, anonymizer (#1459) (Thanks @roeybc)
- Added dev containers for: analyzer, analyzer+transformers, anonymizer, and image redaction (#1450) (Thanks @roeybc)
- Added support for allow_list, allow_list_match, regex_flags in REST API (#1488) (Thanks @hdw868)
- Typo fix in if condition (#1419) (Thanks @omri374)
- Minor notebook changes (#1420) (Thanks @omri374)
- Do not release `presidio-cli` as part of the release pipeline (#1422) (Thanks @SharonHart)
- (Docs) Use Presidio across Anthropic, Bedrock, VertexAI, Azure OpenAI, etc. with LiteLLM Proxy (#1421) (Thanks @krrishdholakia)
- Update CI due to DockerCompose project name issue (#1428) (Thanks @omri374)
- Update docker-compose installation docs (#1439) (Thanks @MWest2020)
- Fix space typo in docs (#1459) (Thanks @artfuldev)
- Unlock numpy after dropping 3.8 (#1480) (Thanks @SharonHart)


## [2.2.355] - 2024-10-28
### Added
#### Docs
 * Add a link to HashiCorp vault operator resource ([#1468](https://github.com/data-privacy-stack/presidio/pull/1468)) (Thanks [Akshay Karle](https://github.com/akshaykarle))
### Changed
#### Analyzer
 * Updates to the transformers conf docs and yaml file ([#1467](https://github.com/data-privacy-stack/presidio/pull/1467)) 

#### Docs
 * docs: clarify the docs on deploying presidio to k8s ([#1453](https://github.com/data-privacy-stack/presidio/pull/1453)) (Thanks [Roel Fauconnier](https://github.com/roel4ez))


## [2.2.355] - July 9th 2024

> Note: A new YAML based mechanism has been added to support no-code customization and creation of recognizers. 
The default recognizers are now automatically loaded from file.


### Added
#### Analyzer
* Recognizer for Spanish Foreigners Identity Code (NIE Numero de Identificacion de Extranjeros).
* Recognizer for Finnish Personal Identity Codes (Henkilötunnus) (#1394) (Thanks honderr).
* New Predefined Recognizer for Indian Passport #1350 (#1351) (Thanks Hiten-98)
* Add new recognizer for IN_VOTER #1344 (#1345) (Thanks kjdeveloper8)
* Spanish NIE (Foreigners ID card) recognizer (#1359) (Thanks areyesfalcon)
* Added regex functionality for allow lists in the analyzer (#1357) (Thanks NarekAra)
* Loading analyzer engine & recognizer registry from configuration file (#1367)
* Align ports with documentation and postman collection. (#1375) (Thanks ungana)
* Analyzer documentation (#1384)
* Fix the entity filtering of the transformer_recognizer.py analzye function (#1403) (Thanks andreas-eberle)

### Changed
#### Analyzer
* Update conf files location (#1358)
* Fix OverflowError in crypto_recognizer (#1377)
* Improve url detector (#1398) (Thanks afogel)
* Update Dockerfile.windows (#1413) (thanks markvantilburg)
* Changing predefined recognizers to use the config file (#1393) (Thanks RoeyBC)
#### Anonymizer
* Update Dockerfile.windows (#1414) (thanks markvantilburg)

#### General
* Add Ruff linter + Apply Ruff fix (#1379)
* Auto-formatting, fix D rules (#1381)
* Fix N818, E721 (#1382)
* Migrate Python Packaging to pyproject.toml (#1383) 
* From Pipenv to Poetry (#1391)
* Fix ports in docs (#1408)

## [2.2.353] - March 31st 2024

### Added
#### Analyzer
* Support 'M' prefix in SG_NRIC_FIN Recognizer and expand tests (#1304) (Thanks @miltonsim)
* Add Bech32 and Bech32m Bitcoin Address Validation in Crypto Recognizer and expand tests (#1307) (Thanks @miltonsim)
* Predefined pattern recognizer : IN_VEHICLE_REGISTRATION (#1288) (Thanks @devopam)
* Addition of leniency parameter in predefined PhoneRecognizer (#1311) (Thanks @VMD7)
* Add Singapore UEN Recognizer (#1315) (Thanks @miltonsim)
* Update spacy_stanza.md (#1325) (Thanks @AndreasThinks)
* Adding Span Marker Recognizer Sample (#1321) (Thanks @VMD7)
* Cache compiled regexes in analyzer (#1335) (Thanks @Edward-Upton)

#### Anonymizer
* Added pseudonimyzation sample (#1296)


#### Image redactor
* Added tesseract to installation (#1312)
  
#### Structured
* Analysis builder improvements (#1295) (Thanks @ebotiab)
* Implement user-defined entity selection strategies in Presidio Structured (#1319) (Thanks @miltonsim)

### Changed
#### Analyzer
* Fix for incorrectly referenced recognizer in analysis_explaination using PhoneRecognizer (#1330) *Thanks @egillv021)
* Fix bug where "bank" and "check" wouldn't work (#1333) (Thanks @usr-ein and @Samuel Prevost)
* Bugfix in tutorial (#1310)
* Changed default aggregation_strategy to max (#1342)

#### Image Redactor
* Fixed wrong condition for dicom metadata (#1347)

## [2.2.353] - Feb 12th 2024

### Added
#### Analyzer
* Add predefined_recognizer: IN_AADHAAR (#1256)

#### Anonymizer
* Added the option to add custom operators + pseudonymization sample (#1284)

### Changed

#### Analyzer
* Fix failing test due to optional package (#1258)
* Update publish-to-pypi.yml (#1259)
* Allow local Spacy Models to be loaded in NLP Engine (#1269)
* Upgrade pip in windows containers (#1272)

#### Image Redactor
* Bugfix in ImageAnalyzerEngine  #1274


## [2.2.352] - Jan 22nd 2024
### Added
#### Structured
* Added alpha of presidio-structured, a library (presidio-structured) which re-uses existing logic from existing presidio components to allow anonymization of (semi-)structured data. (#1192)

#### Analyzer
* Add PL PESEL recognizer (#1209)
* Azure AI language recognizer (#1228)
* Add_conf_to_package_data (#1243)

#### Anonymizer
* Add keep operator as deanonymizer (#1255)
* Update anonymize_list type hints and document that sometimes items will be ignored. (#1252)


#### General
* Add Dockerfile for Windows containers (#1194)

### Changed
#### Analyzer
* Drop WA driver license number (#1214)
* Change ner_model_configuration from list to map (#1222)
* Bugfix in SpacyRecognizer (#1221)
* Bugfix in NerModelConfiguration (#1230)
* Add_conf_to_package_data (#1243)

#### Anonymizer
* Improved the logic of conflict handling in AnonymizerEngine (#1196)

#### Image Redactor
* Change default score threshold in image redactor (#1210)
* fixes bug #1227 (#1231)
* Added missing dependencies for opencv-python and azure forms recognizer (#1257)

#### General
* Remove inclusive-lint step (#1207)
* Updates to demo website with new NLP Engine (#1181)


## [2.2.351] - Nov. 6th 2024
### Changed
#### Analyzer
* Hotfix for NerModelConfiguration not created correctly (#1208)

## [2.2.350] - Nov. 2nd 2024
### Changed
#### Analyzer
* Hotfix: default.yaml is not parsed correctly (#1202)

## [2.2.35] - Nov. 2nd 2024
### Changed
#### Analyzer
* Put org in ignore as it has many FPs (#1200)


## [2.2.34] - Oct. 30th 2024

### Added
#### Analyzer
* New Predefined Recognizer: IN_PAN (#1100)
  
#### Anonymizer
* Anonymizer - Pass bytes key to Encrypt / Decrypt (#1147)
  
#### Image redactor
* DICOM redactor improvement: Enabling more photometric interpretations (#1103)
* DICOM redactor improvement: Adding exceptions for when DICOM file does not have pixel data (#1104)
* Small reordering of kwargs as prereq for allow list functionality (#1110)
* DICOM redactor improvement: Preventing distortion when multiple sets of pixels are in one instance (#1109)
* DICOM redactor improvement: Enabling compatibility with compressed images (#1105)
* DICOM redactor improvement: Enable return of redacted bboxes (#1111)
* DICOM redactor improvement: Enable selection of redact approach (#1113)
* Enable toggle of printing output location after redacting from file (#1144)
* Changing test exception type check (#1148)
* Enabling allow list approach with all image redaction (#1145)
* Improve process names method in DICOM image redactor (#1150)
* Adding examples of toggling metadata usage and saving bboxes (#1158)
* Updating verification engines to include latest updates to redactor engines (#1162)
* Improved bbox processor (#1163)
* Updating verification engines and enable plotting of custom bboxes (#1164)
* Added image processing class to preprocess the image before running OCR (#1166)
* Added support for Microsoft's document intelligence OCR
  
### Changed
#### Analyzer
* Refactored the `NlpEngine` and Ner recognizers (`SpacyRecognizer`, `TransformersRecognizer`, `StanzaRecognizer`) to allow simpler integration of huggingface and transformers models (#1159). This includes:
    - Changes in how NER results flow through Presidio (see docs)
    - NER/model definition is now defined using a conf file or a `NerModelConfiguration` object.
    - Integrated `spacy-huggingface-pipelines` for a more robust integration of huggingface models.        
* As a result, `SpacyRecognizer` logic has changed, please see #1159. Some fields within the class are now deprecated.
* Updated type checks (#1175)
* Enabled regex flags manipulation (#1193)
  
#### Anonymizer
* Initial logic check for merging 2 entities (#1092)
* Fix Sphinx warning in OperatorConfig (#1143)
* Fix type mismatch in check_label_groups parameter in spacy_recognizer (#1130)
* anonymize_list return type hint fix (#1178)
* 
#### General
* We no longer use Pipenv.lock. Locking happens as part of the CI. (#1152)
* Changed the ACR instance (#1089)
* Updated to Cred Scan V3 (#1154) 

## [2.2.33] - June 1st 2023
### Added
#### Anonymizer
* Added `keep`, an no-op anonymizer that allows preserving some types of PII while keeping track of its position in anonymized output. (#1062)
* Added `BatchAnonymizerEngine` to complement the `BatchAnalyzerEngine` for lists, and dicts (#993)

### General
* Drop support for Python 3.7
* Add support for Python 3.11
* New demo app for Presidio, based on Streamlit (#1054)
* GPT based synthetic data generation (#1051)

## [2.2.32] - 25.01.2023
### Changed
#### General
* Updated dependencies

#### Analyzer
* Fixed exception on whitespace in AU recognizers
* Updated API version for Text Analytics in sample

#### Anonymizer
* Fixed merge entity from the same type

#### Image redactor
* Modified `ImagePiiVerifyEngine` to allow passing of kwargs
* Updated template for building image redactor yaml
* Updated all image redactor engines and OCR classes to allow passing of an OCR confidence threshold and other OCR parameters
* Moved general bounding box operations to new class `BboxProcessor`
* Updated `presidio-image-redactor` version from 0.0.45 to 0.0.46

### Added
#### Analyzer
* Added revised example for transformer recognizer

#### Image redactor
* Added evaluation code for the DICOM image redaction capabilities
* REST API to support web applications payload

#### General
* Updated documentation to include instructions on using DICOM evaluation code
* Updated documentation to mention OCR thresholding

## [2.2.31] - 14.12.2022
### Changed
#### Image-Redactor
* Added DICOM image redaction capabilities (`DicomImageRedactorEngine` class and tests)
* Updated `setup.py` to include new required packages for DICOM capabilities
* Updated Pipfile and Pipfile.lock
* Updated `presidio-image-redactor` version from 0.0.44 to 0.0.45
* Updated the `ImagePiiVerifyEngine` class to allow use of custom analyzer engines

#### General
* Updated `NOTICE` to include licenses of added packages
* Updated docs with getting started code for new `DicomImageRedactorEngine`

## [2.2.30] - 25.10.2022
### Added
#### Analyzer
* Added Italian fiscal code recognizer
* Added Italian driver license recognizer
* Added Italian identity card recognizer
* Added Italian passport recognizer
* Added `TransformersNlpEngine` to support transformer based NER models within spaCy pipelines
* Added pattern for next gen US passport in `presidio-analyzer/presidio_analyzer/predefined_recognizers/us_passport_recognizer.py`

### Changed
#### Analyzer
* Improved MEDICAL_LICENSE pattern and fixed checksum verification
* Bugfix for context handling by aligning results to recognizers using a unique identifier and not recognizer name
* Updated Pipfile.lock

#### Anonymizer
* Removed constraint on empty texts

#### Image-Redactor
* Updated Pipfile.lock

#### General
* Updated `pipenv` version
* Updated `black` and `flake8` in pre-commit scripts
* Updated docs for NLP engine

## [2.2.29] - 12.07.2022
### Added

#### General
- Added Presidio to OSSF (Open Source Security Foundation)
- Added CodeQL scanning

#### Analyzer
- Introduced [BatchAnalyzerEngine](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/batch_analyzer_engine.py)
- Added [allow-list functionality](https://github.com/data-privacy-stack/presidio/blob/4cbfc1a80dc15da7d5a9cf5a1c680e8df4f2b349/presidio-analyzer/presidio_analyzer/analyzer_engine.py#L135) to ignore specific strings
- Added notebook on [anonymizing known values](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/Anonymizing%20known%20values.ipynb)
- Added [sample for using `transformers` models in Presidio](https://github.com/data-privacy-stack/presidio/blob/main/docs/samples/python/transformers_recognizer.py)

### Changed

#### Anonymizer
- Bug fix for getting the text before anonymizing (https://github.com/data-privacy-stack/presidio/pull/890)

#### Image redactor
- Deps update

## [2.2.28] - 04.05.2022
### Changed
#### Analyzer
* Improved deny-list regex and customizability
* Added documentation for existing spaCy models
* Bugfix in analysis explanation scores

#### Image redactor
* PIL version updated to 9.0.1

### Added
#### Analyzer
* Recognizers can be loaded from YAML


## [2.2.27] - 08.03.2022
### Changed

#### Analyzer
* Improved context mechanisms to support recognizer level context enhacenement and cross-entity context support

## [2.2.26] - 23.02.2022
### Changed

#### Analyzer
Bug fix in context support

## [2.2.25] - 21.02.2022
### Changed

#### Analyzer

* Added a URL recognizer
* Added a new capability for creating new logic for context detection. See [ContextAwareEnhancer](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/context_aware_enhancers/context_aware_enhancer.py) and [LemmaContextAwareEnhancer](https://github.com/data-privacy-stack/presidio/blob/main/presidio-analyzer/presidio_analyzer/context_aware_enhancers/lemma_context_aware_enhancer.py). Documentation would be added on a future release.
Furthermore, it is now possible to pass context words thruogh the `analyze` method (or via API) and those would be taken into account for context enhancement. 



#### Anonymizer

* Bug fix for entities at the end of a sentence.

#### Docs

- Formatted (black/flake8) the Python examples.

### Removed

#### Analyzer

* Removed the DOMAIN_NAME recognizer. This change means that the `DOMAIN_NAME` entity is no longer returned by Presidio. `URL` would be returned instead, and would catch full addresses and not just domain names (`https://www.microsoft.com/a/b.html` and not just `www.microsoft.com`)



## [2.2.24] - 23.01.2022
### Changed
* Fixed issue when IBAN followed by all caps can't be recognized
* Updated dependencies in Pipfile.lock
* Removed official Python 3.6 support and added support for 3.10
* Added docs for creating a streamlit app
* Added docs for using Flair

### Removed

### Deprecated

## [2.2.23] - 16.11.2021
### Changed
#### Analyzer:
* Added multi-regional phone number recognizer.
* Fixed duplicated entities removal.
* Added sample for structured / semi-structured data in batch.
* Dependencies version bumps.

#### Anonymizer:
* Added sample for getting an identified entity value using a custom Operator.
* Changed packages/imports .
* Added repr to classes.
* Added encryption and decryption samples.
* Remove AnonymizerResult in favor of OperatorResult, for an easier anonymization-deanonymization.
* Anonymizaer and Deanonymizaer to return `operator_name` instead of `operator` in OperatorResult.

## [2.2.2] - 09.06.2021
### Changed
#### Analyzer:
* Databricks based template in Azure Data Factory docs
* Adding ORGANIZATION recognizer docs
* Bumped pydantic from 1.7.3 to 1.7.4
* Updated call to stanza via spacy-stanza
* Added DATE_TIME recognizer
* Added Medical Licence recognizer
* Bumped spacy from 3.0.5 to 3.0.6

## [2.2.1] - 10.05.2021
### Changed
#### Analyzer:
* Create CODE_OF_CONDUCT
* ADF templates docs
* Fix spark sample to run presidio in broadcast
* Ad-hoc recognizers
* Text Analytics Integration Sample
* Documentation update and samples validation
* Adding tagger to the spaCy model pipeline
* Sample notebook for remote recognizer (using Text Analytics)
* Add matplotlib to image-redactor
* Added custom lambda anonymizer
* Added add pii_verify_engine to the image-redactor


## [2.2.0] - 12.04.2021
### Changed
#### Analyzer:
Upgrade Analyzer spacy version to 3.0.5

#### Anonymizer Engine:
1. Request entity AnonymizerConfig renamed OperatorConfig
    - In OperatorConfig: anonymizer_name -> operator_name
2. Response entity AnonymizerResult renamed to EngineResult
    - In EngineResult: List[AnonymizedEntity] -> List[OperatorResult]
    - In OperatorResult: 
        - anonymizer -> operator
        - anonymized_text -> text

#### Anonymize API:
1. Response entity anonymizer renamed to operator.
2. Response entity anonymizer_text renamed to text.

#### Deanonymize:
New endpoint for deanonymizing encrypted entities by the anonymizer.  


[unreleased]: https://github.com/data-privacy-stack/presidio/compare/2.2.363...HEAD
[2.2.363]: https://github.com/data-privacy-stack/presidio/compare/2.2.362...2.2.363
[2.2.362]: https://github.com/data-privacy-stack/presidio/compare/2.2.361...2.2.362
[2.2.361]: https://github.com/data-privacy-stack/presidio/compare/2.2.360...2.2.361
[2.2.360]: https://github.com/data-privacy-stack/presidio/compare/2.2.359...2.2.360
[2.2.359]: https://github.com/data-privacy-stack/presidio/compare/2.2.358...2.2.359
[2.2.358]: https://github.com/data-privacy-stack/presidio/compare/2.2.357...2.2.358
[2.2.357]: https://github.com/data-privacy-stack/presidio/compare/2.2.356...2.2.357
[2.2.356]: https://github.com/data-privacy-stack/presidio/compare/2.2.355...2.2.356
[2.2.355]: https://github.com/data-privacy-stack/presidio/compare/2.2.354...2.2.355
[2.2.354]: https://github.com/data-privacy-stack/presidio/compare/2.2.353...2.2.354
[2.2.353]: https://github.com/data-privacy-stack/presidio/compare/2.2.352...2.2.353
[2.2.352]: https://github.com/data-privacy-stack/presidio/compare/2.2.351...2.2.352
[2.2.351]: https://github.com/data-privacy-stack/presidio/compare/2.2.350...2.2.351
[2.2.350]: https://github.com/data-privacy-stack/presidio/compare/2.2.35...2.2.350
[2.2.35]: https://github.com/data-privacy-stack/presidio/compare/2.2.34...2.2.35
[2.2.34]: https://github.com/data-privacy-stack/presidio/compare/2.2.33...2.2.34
[2.2.33]: https://github.com/data-privacy-stack/presidio/compare/2.2.32...2.2.33
[2.2.32]: https://github.com/data-privacy-stack/presidio/compare/2.2.31...2.2.32
[2.2.31]: https://github.com/data-privacy-stack/presidio/compare/2.2.30...2.2.31
[2.2.30]: https://github.com/data-privacy-stack/presidio/compare/2.2.29...2.2.30
[2.2.29]: https://github.com/data-privacy-stack/presidio/compare/2.2.28...2.2.29
[2.2.28]: https://github.com/data-privacy-stack/presidio/compare/2.2.27...2.2.28
[2.2.27]: https://github.com/data-privacy-stack/presidio/compare/2.2.26...2.2.27
[2.2.26]: https://github.com/data-privacy-stack/presidio/compare/2.2.25...2.2.26
[2.2.25]: https://github.com/data-privacy-stack/presidio/compare/2.2.24...2.2.25
[2.2.24]: https://github.com/data-privacy-stack/presidio/compare/2.2.23...2.2.24
[2.2.23]: https://github.com/data-privacy-stack/presidio/compare/2.2.2...2.2.23
[2.2.2]: https://github.com/data-privacy-stack/presidio/compare/2.2.1...2.2.2
[2.2.1]: https://github.com/data-privacy-stack/presidio/compare/2.2.0...2.2.1
