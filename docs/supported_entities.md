# PII entities supported by Presidio

Presidio contains predefined recognizers for PII entities.
This page describes the different entities Presidio can detect and the method Presidio employs to detect those.

In addition, Presidio allows you to add custom entity recognizers.
For more information, refer to the [adding new recognizers documentation](analyzer/adding_recognizers.md).

## List of supported entities

### Global

|Entity Type | Description | Detection Method |
| --- | --- | --- |
|CREDIT_CARD |A credit card number is between 12 to 19 digits. <https://en.wikipedia.org/wiki/Payment_card_number>|Pattern match and checksum|
|CRYPTO|A Crypto wallet number. Currently only Bitcoin address is supported|Pattern match, context and checksum|
|DATE_TIME|Absolute or relative dates or periods or times smaller than a day.|Pattern match and context|
|EMAIL_ADDRESS|An email address identifies an email box to which email messages are delivered|Pattern match, context and RFC-822 validation|
|IBAN_CODE|The International Bank Account Number (IBAN) is an internationally agreed system of identifying bank accounts across national borders to facilitate the communication and processing of cross border transactions with a reduced risk of transcription errors.|Pattern match, context and checksum|
|IMEI|International Mobile Equipment Identity, a 15-digit identifier for mobile devices.|Pattern match, context and checksum|
|IP_ADDRESS|An Internet Protocol (IP) address (either IPv4 or IPv6).|Pattern match, context and checksum|
|MAC_ADDRESS| A Media Access Control (MAC) address is a unique identifier assigned to network interfaces for communications on the physical network segment.|Pattern match and context|
|NRP|A person’s Nationality, religious or political group.|Custom logic and context|
|LOCATION|Name of politically or geographically defined location (cities, provinces, countries, international regions, bodies of water, mountains|Custom logic and context|
|PERSON|A full person name, which can include first names, middle names or initials, and last names.|Custom logic and context|
|PHONE_NUMBER|A telephone number. The `PhoneRecognizer` can be extended programmatically for country-specific detection by configuring `supported_regions` and `supported_entity` (e.g. Philippines: `PhoneRecognizer(supported_regions=["PH"], supported_entity="PH_MOBILE_NUMBER")`, Turkey: `PhoneRecognizer(supported_regions=["TR"], supported_entity="TR_PHONE_NUMBER")`)|Custom logic, pattern match and context|
|MEDICAL_LICENSE|Common medical license numbers.|Pattern match, context and checksum|
|URL|A URL (Uniform Resource Locator), unique identifier used to locate a resource on the Internet|Pattern match, context and top level url validation|
|UUID|A Universally Unique Identifier (UUID) in the standard 8-4-4-4-12 hyphenated hexadecimal format. Covers RFC 4122 versions 1-5 and RFC 9562 versions 6-8; the nil UUID (all zeros) is excluded as a non-identifying sentinel.|Pattern match, validation of version/variant nibbles, and context|
|VIN|Vehicle Identification Number, a 17-character identifier assigned to motor vehicles per ISO 3779. Disabled by default.|Pattern match, context and checksum|

### USA

|Entity Type|Description|Detection Method|
|--- |--- |--- |
|US_BANK_NUMBER|A US bank account number is between 8 to 17 digits.|Pattern match and context|
|US_DRIVER_LICENSE|A US driver license according to <https://ntsi.com/drivers-license-format/>|Pattern match and context|
|US_ITIN | US Individual Taxpayer Identification Number (ITIN). Nine digits that start with a "9" and contain a "7" or "8" as the 4 digit.|Pattern match and context|
|US_CLAIM_NUMBER|A US healthcare claim identifier used in billing and claims processing.|Pattern match, context enhancement, and entity threshold|
|US_HEALTH_INSURANCE_MEMBER_ID|A US health insurance member or subscriber identifier printed on an insurance card. Healthcare or insurance context increases detection confidence.|Pattern match, context enhancement, and entity threshold|
|US_MBI|A US Medicare Beneficiary Identifier (MBI) with 11 alphanumeric characters.|Pattern match and context|
|US_NPI|A US National Provider Identifier (NPI) is a 10-digit number issued to healthcare providers by CMS under HIPAA.|Pattern match, context and checksum|
|US_PASSPORT |A US passport number with 9 digits.|Pattern match and context|
|US_PRESCRIPTION_NUMBER|A US prescription or pharmacy order identifier.|Pattern match, context enhancement, and entity threshold|
|US_PRIOR_AUTHORIZATION_NUMBER|A US prior authorization identifier used for treatment or drug approval requests.|Pattern match, context enhancement, and entity threshold|
|US_PROVIDER_TAX_ID|A US provider organization tax identifier (TIN/EIN) used in healthcare billing workflows.|Pattern match, context enhancement, and entity threshold|
|US_REFERRAL_NUMBER|A US healthcare referral identifier, including specialty or infusion referral numbers.|Pattern match, context enhancement, and entity threshold|
|US_SSN|A US Social Security Number (SSN) with 9 digits.|Pattern match and context|

### UK

|Entity Type|Description|Detection Method|
|--- |--- |--- |
|UK_DRIVING_LICENCE|UK driving licence number issued by the DVLA. A 16-character alphanumeric string encoding surname, date of birth, and initials.|Pattern match, context and validation|
|UK_NHS|A UK NHS number is 10 digits.|Pattern match, context and checksum|
|UK_NINO|UK [National Insurance Number](https://en.wikipedia.org/wiki/National_Insurance_number) is a unique identifier used in the administration of National Insurance and tax.|Pattern match and context|
|UK_PASSPORT|A UK passport number consists of 2 letters followed by 7 digits (e.g., AB1234567), used in passports issued from 2015 onwards.|Pattern match and context|
|UK_POSTCODE|A UK [postcode](https://en.wikipedia.org/wiki/Postcodes_in_the_United_Kingdom) is a 5-8 character alphanumeric code used by the Royal Mail for mail sorting.|Pattern match and context|
|UK_VEHICLE_REGISTRATION|A UK vehicle registration number (number plate) in current (2001+), prefix (1983-2001), or suffix (1963-1983) format.|Pattern match, context and validation|

### Spain

|Entity Type|Description|Detection Method|
|--- |--- |--- |
|ES_NIF         | A Spanish NIF number (Personal tax ID).|Pattern match, context and checksum|
|ES_NIE         | A Spanish NIE number (Foreigners ID card).|Pattern match, context and checksum|
|ES_PASSPORT    | A Spanish passport number.|Pattern match and context|

### Italy

|Entity Type|Description|Detection Method|
|--- |--- |--- |
|IT_FISCAL_CODE| An Italian personal identification code. <https://en.wikipedia.org/wiki/Italian_fiscal_code>|Pattern match, context and checksum|
|IT_DRIVER_LICENSE| An Italian driver license number.|Pattern match and context|
|IT_VAT_CODE| An Italian VAT code number |Pattern match, context and checksum|
|IT_PASSPORT|An Italian passport number.|Pattern match and context|
|IT_IDENTITY_CARD|An Italian identity card number. <https://en.wikipedia.org/wiki/Italian_electronic_identity_card>|Pattern match and context|

### Poland

|Entity Type|Description|Detection Method|
|--- |--- |--- |
|PL_PESEL|Polish PESEL number|Pattern match, context and checksum|

### Singapore

|FieldType|Description|Detection Method|
|--- |--- |--- |
|SG_NRIC_FIN| A National Registration Identification Card | Pattern match and context |
|SG_UEN| A Unique Entity Number (UEN) is a standard identification number for entities registered in Singapore. | Pattern match, context, and checksum |

### Australia

|FieldType|Description|Detection Method|
|--- |--- |--- |
|AU_ABN| The Australian Business Number (ABN) is a unique 11 digit identifier issued to all entities registered in the Australian Business Register (ABR). | Pattern match, context, and checksum |
|AU_ACN| An Australian Company Number is a unique nine-digit number issued by the Australian Securities and Investments Commission to every company registered under the Commonwealth Corporations Act 2001 as an identifier. | Pattern match, context, and checksum |
|AU_TFN| The tax file number (TFN) is a unique identifier issued by the Australian Taxation Office to each taxpaying entity | Pattern match, context, and checksum |
|AU_MEDICARE| Medicare number is a unique identifier issued by Australian Government that enables the cardholder to receive a rebates of medical expenses under Australia's Medicare system| Pattern match, context, and checksum |

### India
| FieldType  | Description                                                                                                                                                         |Detection Method|
|------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|--- |
| IN_PAN     | The Indian Permanent Account Number (PAN) is a unique 12 character alphanumeric identifier issued to all business and individual entities registered as Tax Payers. | Pattern match, context |
| IN_AADHAAR | Indian government issued unique 12 digit individual identity number                                                                                                 | Pattern match, context, and checksum |
| IN_VEHICLE_REGISTRATION | Indian government issued transport (govt, personal, diplomatic, defence)  vehicle registration number                                                               | Pattern match, context, and checksum |
| IN_VOTER | Indian Election Commission issued 10 digit alpha numeric voter id for all indian citizens (age 18 or above) | Pattern match, context |
| IN_PASSPORT | Indian Passport Number | Pattern match, Context |
| IN_GSTIN | The Indian Goods and Services Tax Identification Number (GSTIN) is a 15-character identifier with state code (01-37), PAN, registration number, 'Z', and checksum. | Pattern match, context, and validation |

### Finland
| FieldType  | Description                                                                                             | Detection Method                         |
|------------|---------------------------------------------------------------------------------------------------------|------------------------------------------|
| FI_PERSONAL_IDENTITY_CODE     | The Finnish Personal Identity Code (Henkilötunnus) is a unique 11 character individual identity number. | Pattern match, context and custom logic. |

### Korea
| FieldType  | Description                                                                                             | Detection Method                         |
|------------|---------------------------------------------------------------------------------------------------------|------------------------------------------|
| KR_DRIVER_LICENSE    |  The Korean driver license number is a 12-digit number. | Pattern match, context and custom logic. |
| KR_FRN     | The Korean Foreigner Registration Number (FRN) is a 13-digit number. | Pattern match, context and custom logic. |
| KR_PASSPORT| The Korean Passport Number  | Pattern match, context. |
| KR_BRN     | The Korean Business Registration Number (BRN) is a 10-digit number assigned to business entities for taxation purposes. | Pattern match, context and custom logic. |
| KR_RRN     | The Korean Resident Registration Number (RRN) is a 13-digit number issued to all Korean residents. | Pattern match, context and custom logic. |


### Nigeria
| FieldType  | Description                                                                                             | Detection Method                         |
|------------|---------------------------------------------------------------------------------------------------------|------------------------------------------|
| NG_NIN     | The Nigerian National Identification Number (NIN) is a unique 11-digit number issued by the National Identity Management Commission (NIMC). | Pattern match, context, and checksum |
| NG_VEHICLE_REGISTRATION | Nigerian vehicle registration plate number in the current format (2011+): 3 letters (LGA code), 3 digits (serial), 2 letters (year/batch). | Pattern match and context |

### Philippines
| FieldType  | Description                                                                                             | Detection Method                         |
|------------|---------------------------------------------------------------------------------------------------------|------------------------------------------|
| PH_PASSPORT | Philippine Passport Number. Alphanumeric format, usually 1 letter followed by 7 digits and 1 letter, or 2 letters followed by 7 digits (e.g., P1234567A, EB1234567). | Pattern match and context |
| PH_TIN     | Philippines Taxpayer Identification Number (TIN). 9 or 12-digit number issued by the Bureau of Internal Revenue (BIR). | Pattern match, context, and checksum |

### Canada

|FieldType|Description|Detection Method|
|--- |--- |--- |
|CA_SIN|A Canadian Social Insurance Number (SIN) is a 9-digit number issued by Employment and Social Development Canada (ESDC) to administer government programs. The last digit is a Luhn check digit. SINs starting with 0 or 8 are reserved and not issued.|Pattern match, context, and checksum|
|CA_POSTAL_CODE|A Canadian postal code in the standard A1A 1A1 format (letter-digit-letter, space, digit-letter-digit). The letters D, F, I, O, Q, U are never used in any letter position; W and Z are additionally excluded from the first letter position.|Pattern match and context|

### Sweden
| FieldType  | Description                                                                                             | Detection Method                         |
|------------|---------------------------------------------------------------------------------------------------------|------------------------------------------|
| SE_ORGANISATIONSNUMMER    | The Swedish Organisations ID Number is a unique 10-digit number issued to all Swedish organisations. | Pattern match, context, and checksum. |
| SE_PERSONNUMMER    | The Swedish Personal ID Number is a unique 10/12-digit number issued to all Swedish residents. The recognizer also supports Samordningsnummer (coordination numbers) issued to individuals who are not (yet) registered residents but need a Swedish identifier (e.g., temporary workers, students). | Pattern match, context, and checksum. |

### South Africa
| FieldType  | Description                                                                                             | Detection Method                         |
|------------|---------------------------------------------------------------------------------------------------------|------------------------------------------|
| ZA_ID_NUMBER | The South African identity number is a 13-digit identifier in the `YYMMDDSSSSCAZ` format, where the trailing digit is validated with the Luhn algorithm. | Pattern match, context, and checksum. |
| ZA_PASSPORT | The South African passport number is a 9-character identifier with prefix letter A, D, M, or T followed by 8 digits. | Pattern match, context, and validation. |
| ZA_INCOME_TAX_NUMBER | The South African SARS income tax reference number is a 10-digit numeric identifier, commonly starting with 0, 1, 2, 3, or 9. | Pattern match, context, and validation. |
| ZA_DRIVER_LICENSE | The South African eNaTIS driver's licence number is an alphanumeric identifier of 10–14 characters. | Pattern match, context, and validation. |
| ZA_VAT_NUMBER | The South African VAT registration number is a 10-digit identifier starting with 4. | Pattern match, context, and validation. |
| ZA_COMPANY_REGISTRATION | The South African CIPC company registration number uses modern `YYYY/NNNNNN/NN` format or legacy prefixed formats such as CK. | Pattern match, context, and validation. |
| ZA_TRAFFIC_REGISTER_NUMBER | The South African eNaTIS traffic register number is a 13-digit identifier for foreigners and organisations, disambiguated from ZA_ID_NUMBER via validation. | Pattern match, context, and validation. |
| ZA_LICENSE_PLATE | The South African vehicle licence plate uses provincial formats such as compact suffix forms (e.g. KD93GKGP) or spaced layouts (e.g. DK 28 LF GP). | Pattern match, context, and validation. |
| ZA_MOBILE_NUMBER | The South African mobile (cellular) number uses a 9-digit national significant number with country code +27 or domestic trunk prefix 0 (primarily 06x, 07x, and cellular 08x ranges). | `phonenumbers` match, line-type filter, and context. |
| ZA_TELEPHONE_NUMBER | The South African telephone number covers geographic landlines (01x–05x) and non-mobile service lines such as toll-free (080), sharecall (086), and VoIP (087). | `phonenumbers` match, line-type filter, and context. |

### Thai
| FieldType  | Description                                                                                             | Detection Method                         |
|------------|---------------------------------------------------------------------------------------------------------|------------------------------------------|
| TH_TNIN    | The Thai National ID Number (TNIN) is a unique 13-digit number issued to all Thai residents. | Pattern match, context and custom logic. |

### Turkey

| FieldType  | Description                                                                                             | Detection Method                         |
|------------|---------------------------------------------------------------------------------------------------------|------------------------------------------|
| TR_NATIONAL_ID    | The Turkish National Identification Number (TCKN) is a unique 11-digit number issued to all Turkish citizens. | Pattern match, context and checksum. |
| TR_LICENSE_PLATE  | Turkish vehicle license plate (plaka): 2-digit province code (01–81), 1–3 letters (A–Z, excluding Q, W, X), and 2–4 digits. Standard civilian format only. Legal basis: KTK Madde 23. | Pattern match, context and province code validation. |

### Philippines

| FieldType  | Description                                                                                             | Detection Method                         |
|------------|---------------------------------------------------------------------------------------------------------|------------------------------------------|
| PH_UMID    | Philippine Unified Multi-Purpose ID (UMID) / Common Reference Number (CRN). 12-digit format (e.g., 0111-1234567-8). Acts as a master ID connecting SSS, GSIS, PhilHealth, and Pag-IBIG. Disabled by default. | Pattern match and context |

### Germany

| Entity Type | Description | Detection Method |
| --- | --- | --- |
| DE_TAX_ID | German Steueridentifikationsnummer (Steuer-IdNr.): unique 11-digit personal tax identification number issued by the Bundeszentralamt für Steuern. Legal basis: §§ 139a–139e AO. | Pattern match, context and checksum (ISO 7064 Mod 11, 10) |
| DE_TAX_NUMBER | German Steuernummer: tax number assigned by the local Finanzamt, in ELSTER unified 13-digit format or state-specific slash-separated formats. Legal basis: § 139a AO. | Pattern match and context |
| DE_PASSPORT | German Reisepassnummer: 9-character alphanumeric document number using ICAO Doc 9303 character set. Legal basis: Passgesetz (PassG) § 4. | Pattern match and context |
| DE_ID_CARD | German Personalausweisnummer: 9-character alphanumeric document number (nPA since Nov 2010) or legacy T+8-digit format. Legal basis: Personalausweisgesetz (PAuswG). | Pattern match and context |
| DE_SOCIAL_SECURITY | German Rentenversicherungsnummer (RVNR): 12-character identifier encoding birth date, surname initial, serial and check digit. Legal basis: § 147 SGB VI. | Pattern match, context and checksum (DRV algorithm) |
| DE_HEALTH_INSURANCE | German Krankenversicherungsnummer (KVNR): 10-character identifier (1 letter + 9 digits) printed on the elektronische Gesundheitskarte (eGK). Legal basis: § 290 SGB V. Special category: health data (DSGVO Art. 9). | Pattern match, context and checksum (GKV-Spitzenverband algorithm) |
| DE_KFZ | German KFZ-Kennzeichen (vehicle registration plate): district code (1–3 letters), identifier (1–2 letters), and 1–4 digits, optionally with E (electric) or H (historic) suffix. Legal basis: Fahrzeug-Zulassungsverordnung (FZV) § 8. | Pattern match and context |
| DE_HANDELSREGISTER | German Handelsregisternummer: commercial register number with HRA (sole traders / partnerships) or HRB (corporations) prefix followed by 1–6 digits. HRA entries directly identify natural persons (sole traders). Legal basis: §§ 9, 14 HGB, HRV. | Pattern match and context |
| DE_PLZ | German Postleitzahl (postal code): 5-digit code in the range 01001–99998. Constitutes personal data in combination with other address fields (DSGVO Art. 4 Nr. 1). **High false-positive risk** – only reliable with address-context words present; base confidence is 0.05. Legal basis: DSGVO Art. 4 Nr. 1. | Pattern match and context (context required for actionable results) |

### Medical / Clinical

Detected using the `MedicalNERRecognizer` (requires the `transformers` extra). Uses the [blaze999/Medical-NER](https://huggingface.co/blaze999/Medical-NER) model by default.

|Entity Type | Description | Detection Method |
| --- | --- | --- |
|MEDICAL_DISEASE_DISORDER | A disease or disorder (e.g. diabetes, hypertension). | NER model (HuggingFace transformers) |
|MEDICAL_MEDICATION | A medication or drug name (e.g. metformin, aspirin). | NER model (HuggingFace transformers) |
|MEDICAL_THERAPEUTIC_PROCEDURE | A therapeutic or diagnostic procedure (e.g. surgery, MRI). | NER model (HuggingFace transformers) |
|MEDICAL_CLINICAL_EVENT | A clinical event (e.g. admission, discharge). | NER model (HuggingFace transformers) |
|MEDICAL_BIOLOGICAL_ATTRIBUTE | A biological attribute or measurement (e.g. blood pressure, BMI). | NER model (HuggingFace transformers) |
|MEDICAL_BIOLOGICAL_STRUCTURE | A biological or anatomical structure (e.g. liver, left ventricle). | NER model (HuggingFace transformers) |
|MEDICAL_FAMILY_HISTORY | A family medical history reference. | NER model (HuggingFace transformers) |
|MEDICAL_HISTORY | A patient medical history reference. | NER model (HuggingFace transformers) |

## Adding a custom PII entity

See [this documentation](analyzer/adding_recognizers.md) for instructions on how to add a new Recognizer for a new type of PII entity.

## Complementing Presidio with Azure AI Language PII

[Azure AI Language PII](https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/overview)
 is a cloud-based service that provides Natural Language Processing (NLP) features for detecting PII in text.

A list of supported entities by Azure AI Language PII [can be found here](https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/concepts/entity-categories).

To add Azure AI language into Presidio, [see this sample](samples/python/text_analytics/index.md#how-to-integrate-azure-ai-language-into-presidio).


## Complementing Presidio with Azure Health Data Services PHI

Azure Health Data Services PHI is a cloud-based service that provides Natural Language Processing (NLP) features for detecting PHI in text.

A list of supported entities by Azure Health Data Services PHI [can be found here](https://learn.microsoft.com/en-us/azure/healthcare-apis/deidentification/overview).

To add Azure AI language into Presidio, [see this sample](samples/python/ahds/index.md#how-to-integrate-azure-health-data-services-dei-dentification-into-presidio).


### Connecting to 3rd party PII detectors

See [this documentation](analyzer/adding_recognizers.md#creating-a-remote-recognizer) for instructions on how to implement an external PII detector for a new or existing type of PII entity.
