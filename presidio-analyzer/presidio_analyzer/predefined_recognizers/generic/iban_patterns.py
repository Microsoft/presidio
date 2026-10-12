"""
List of different regex patterns for IBAN.

The IBAN patterns are based on the IBAN specification here
https://en.wikipedia.org/wiki/International_Bank_Account_Number
In addition, an IBAN example per country can be found here:
git shttps://www.xe.com/ibancalculator/countrylist
An IBAN checker is available here: https://www.iban.com/iban-checker
"""

# IBAN parts format
CC = "[A-Z]{2}"  # country code
CK = "[0-9]{2}[ ]?"  # checksum
BOS = "^"
EOS = "$"  # end of string

A = "[A-Z][ ]?"
A2 = "([A-Z][ ]?){2}"
A3 = "([A-Z][ ]?){3}"
A4 = "([A-Z][ ]?){4}"

C = "[a-zA-Z0-9][ ]?"
C2 = "([a-zA-Z0-9][ ]?){2}"
C3 = "([a-zA-Z0-9][ ]?){3}"
C4 = "([a-zA-Z0-9][ ]?){4}"

N = "[0-9][ ]?"
N2 = "([0-9][ ]?){2}"
N3 = "([0-9][ ]?){3}"
N4 = "([0-9][ ]?){4}"

regex_per_country = {
    # Albania (8n, 16c) ALkk bbbs sssx cccc cccc cccc cccc
    "AL": "(AL)" + CK + N4 + N4 + C4 + C4 + C4 + C4,
    # Andorra (8n, 12c) ADkk bbbb ssss cccc cccc cccc
    "AD": "(AD)" + CK + N4 + N4 + C4 + C4 + C4,
    # Austria (16n) ATkk bbbb bccc cccc cccc
    "AT": "(AT)" + CK + N4 + N4 + N4 + N4,
    # Azerbaijan    (4c,20n) AZkk bbbb cccc cccc cccc cccc cccc
    "AZ": "(AZ)" + CK + C4 + N4 + N4 + N4 + N4 + N4,
    # Bahrain   (4a,14c)    BHkk bbbb cccc cccc cccc cc
    "BH": "(BH)" + CK + A4 + C4 + C4 + C4 + C2,
    # Belarus (4c, 4n, 16c)   BYkk bbbb aaaa cccc cccc cccc cccc
    "BY": "(BY)" + CK + C4 + N4 + C4 + C4 + C4 + C4,
    # Belgium (12n)   BEkk bbbc cccc ccxx
    "BE": "(BE)" + CK + N4 + N4 + N4,
    # Bosnia and Herzegovina    (16n)   BAkk bbbs sscc cccc ccxx
    "BA": "(BA)" + CK + N4 + N4 + N4 + N4,
    # Brazil (23n,1a,1c) BRkk bbbb bbbb ssss sccc cccc ccct n
    "BR": "(BR)" + CK + N4 + N4 + N4 + N4 + N4 + N3 + A + C,
    # Bulgaria  (4a,6n,8c)  BGkk bbbb ssss ttcc cccc cc
    "BG": "(BG)" + CK + A4 + N4 + N + N + C2 + C4 + C2,
    # Costa Rica    (18n)   CRkk 0bbb cccc cccc cccc cc (0 = always zero)
    "CR": "(CR)" + CK + "[0]" + N3 + N4 + N4 + N4 + N2,
    # Croatia   (17n)   HRkk bbbb bbbc cccc cccc c
    "HR": "(HR)" + CK + N4 + N4 + N4 + N4 + N,
    # Cyprus    (8n,16c)    CYkk bbbs ssss cccc cccc cccc cccc
    "CY": "(CY)" + CK + N4 + N4 + C4 + C4 + C4 + C4,
    # Czech Republic    (20n)   CZkk bbbb ssss sscc cccc cccc
    "CZ": "(CZ)" + CK + N4 + N4 + N4 + N4 + N4,
    # Denmark   (14n)   DKkk bbbb cccc cccc cc
    "DK": "(DK)" + CK + N4 + N4 + N4 + N2,
    # Dominican Republic    (4a,20n)    DOkk bbbb cccc cccc cccc cccc cccc
    "DO": "(DO)" + CK + A4 + N4 + N4 + N4 + N4 + N4,
    # EAt Timor    (19n) TLkk bbbc cccc cccc cccc cxx
    "TL": "(TL)" + CK + N4 + N4 + N4 + N4 + N3,
    # Estonia   (16n) EEkk bbss cccc cccc cccx
    "EE": "(EE)" + CK + N4 + N4 + N4 + N4,
    # Faroe Islands    (14n) FOkk bbbb cccc cccc cx
    "FO": "(FO)" + CK + N4 + N4 + N4 + N2,
    # Finland   (14n) FIkk bbbb bbcc cccc cx
    "FI": "(FI)" + CK + N4 + N4 + N4 + N2,
    # France    (10n,11c,2n) FRkk bbbb bsss sscc cccc cccc cxx
    "FR": "(FR)" + CK + N4 + N4 + N2 + C2 + C4 + C4 + C + N2,
    # Georgia   (2c,16n)  GEkk bbcc cccc cccc cccc cc
    "GE": "(GE)" + CK + C2 + N2 + N4 + N4 + N4 + N2,
    # Germany   (18n) DEkk bbbb bbbb cccc cccc cc
    "DE": "(DE)" + CK + N4 + N4 + N4 + N4 + N2,
    # Gibraltar (4a,15c)  GIkk bbbb cccc cccc cccc ccc
    "GI": "(GI)" + CK + A4 + C4 + C4 + C4 + C3,
    # Greece    (7n,16c)  GRkk bbbs sssc cccc cccc cccc ccc
    "GR": "(GR)" + CK + N4 + N3 + C + C4 + C4 + C4 + C3,
    # Greenland     (14n) GLkk bbbb cccc cccc cc
    "GL": "(GL)" + CK + N4 + N4 + N4 + N2,
    # Guatemala (4c,20c)  GTkk bbbb mmtt cccc cccc cccc cccc
    "GT": "(GT)" + CK + C4 + C4 + C4 + C4 + C4 + C4,
    # Hungary   (24n) HUkk bbbs sssx cccc cccc cccc cccx
    "HU": "(HU)" + CK + N4 + N4 + N4 + N4 + N4 + N4,
    # Iceland   (22n) ISkk bbbb sscc cccc iiii iiii ii
    "IS": "(IS)" + CK + N4 + N4 + N4 + N4 + N4 + N2,
    # Ireland   (4c,14n)  IEkk aaaa bbbb bbcc cccc cc
    "IE": "(IE)" + CK + C4 + N4 + N4 + N4 + N2,
    # Israel (19n) ILkk bbbn nncc cccc cccc ccc
    "IL": "(IL)" + CK + N4 + N4 + N4 + N4 + N3,
    # Italy (1a,10n,12c)  ITkk xbbb bbss sssc cccc cccc ccc
    "IT": "(IT)" + CK + A + N3 + N4 + N3 + C + C3 + C + C4 + C3,
    # Jordan    (4a,22n)  JOkk bbbb ssss cccc cccc cccc cccc cc
    "JO": "(JO)" + CK + A4 + N4 + N4 + N4 + N4 + N4 + N2,
    # Kazakhstan    (3n,13c)  KZkk bbbc cccc cccc cccc
    "KZ": "(KZ)" + CK + N3 + C + C4 + C4 + C4,
    # Kosovo    (4n,10n,2n)   XKkk bbbb cccc cccc cccc
    "XK": "(XK)" + CK + N4 + N4 + N4 + N4,
    # Kuwait    (4a,22c)  KWkk bbbb cccc cccc cccc cccc cccc cc
    "KW": "(KW)" + CK + A4 + C4 + C4 + C4 + C4 + C4 + C2,
    # Latvia    (4a,13c)  LVkk bbbb cccc cccc cccc c
    "LV": "(LV)" + CK + A4 + C4 + C4 + C4 + C,
    # Lebanon   (4n,20c)  LBkk bbbb cccc cccc cccc cccc cccc
    "LB": "(LB)" + CK + N4 + C4 + C4 + C4 + C4 + C4,
    # LiechteNtein (5n,12c)  LIkk bbbb bccc cccc cccc c
    "LI": "(LI)" + CK + N4 + N + C3 + C4 + C4 + C,
    # Lithuania (16n) LTkk bbbb bccc cccc cccc
    "LT": "(LT)" + CK + N4 + N4 + N4 + N4,
    # Luxembourg    (3n,13c)  LUkk bbbc cccc cccc cccc
    "LU": "(LU)" + CK + N3 + C + C4 + C4 + C4,
    # Malta (4a,5n,18c)   MTkk bbbb ssss sccc cccc cccc cccc ccc
    "MT": "(MT)" + CK + A4 + N4 + N + C3 + C4 + C4 + C4 + C3,
    # Mauritania    (23n) MRkk bbbb bsss sscc cccc cccc cxx
    "MR": "(MR)" + CK + N4 + N4 + N4 + N4 + N4 + N3,
    # Mauritius (4a,19n,3a)   MUkk bbbb bbss cccc cccc cccc 000m mm
    "MU": "(MU)" + CK + A4 + N4 + N4 + N4 + N4 + N3 + A3,
    # Moldova   (2c,18c)  MDkk bbcc cccc cccc cccc cccc
    "MD": "(MD)" + CK + C4 + C4 + C4 + C4 + C4,
    # Monaco    (10n,11c,2n)  MCkk bbbb bsss sscc cccc cccc cxx
    "MC": "(MC)" + CK + N4 + N4 + N2 + C2 + C4 + C4 + C + N2,
    # Montenegro    (18n) MEkk bbbc cccc cccc cccc xx
    "ME": "(ME)" + CK + N4 + N4 + N4 + N4 + N2,
    # Netherlands   (4a,10n)  NLkk bbbb cccc cccc cc
    "NL": "(NL)" + CK + A4 + N4 + N4 + N2,
    # North Macedonia   (3n,10c,2n)   MKkk bbbc cccc cccc cxx
    "MK": "(MK)" + CK + N3 + C + C4 + C4 + C + N2,
    # Norway    (11n) NOkk bbbb cccc ccx
    "NO": "(NO)" + CK + N4 + N4 + N3,
    # Pakistan  (4c,16n)  PKkk bbbb cccc cccc cccc cccc
    "PK": "(PK)" + CK + C4 + N4 + N4 + N4 + N4,
    # Palestinian territories   (4c,21n)  PSkk bbbb xxxx xxxx xccc cccc cccc c
    "PS": "(PS)" + CK + C4 + N4 + N4 + N4 + N4 + N4 + N,
    # Poland    (24n) PLkk bbbs sssx cccc cccc cccc cccc
    "PL": "(PL)" + CK + N4 + N4 + N4 + N4 + N4 + N4,
    # Portugal  (21n) PTkk bbbb ssss cccc cccc cccx x
    "PT": "(PT)" + CK + N4 + N4 + N4 + N4 + N4 + N,
    # Qatar (4a,21c)  QAkk bbbb cccc cccc cccc cccc cccc c
    "QA": "(QA)" + CK + A4 + C4 + C4 + C4 + C4 + C4 + C,
    # Romania   (4a,16c)  ROkk bbbb cccc cccc cccc cccc
    "RO": "(RO)" + CK + A4 + C4 + C4 + C4 + C4,
    # San Marino    (1a,10n,12c)  SMkk xbbb bbss sssc cccc cccc ccc
    "SM": "(SM)" + CK + A + N3 + N4 + N3 + C + C4 + C4 + C3,
    # Saudi Arabia  (2n,18c)  SAkk bbcc cccc cccc cccc cccc
    "SA": "(SA)" + CK + N2 + C2 + C4 + C4 + C4 + C4,
    # Serbia    (18n) RSkk bbbc cccc cccc cccc xx
    "RS": "(RS)" + CK + N4 + N4 + N4 + N4 + N2,
    # Slovakia  (20n) SKkk bbbb ssss sscc cccc cccc
    "SK": "(SK)" + CK + N4 + N4 + N4 + N4 + N4,
    # Slovenia  (15n) SIkk bbss sccc cccc cxx
    "SI": "(SI)" + CK + N4 + N4 + N4 + N3,
    # Spain (20n) ESkk bbbb ssss xxcc cccc cccc
    "ES": "(ES)" + CK + N4 + N4 + N4 + N4 + N4,
    # Sweden    (20n) SEkk bbbc cccc cccc cccc cccc
    "SE": "(SE)" + CK + N4 + N4 + N4 + N4 + N4,
    # Switzerland   (5n,12c)  CHkk bbbb bccc cccc cccc c
    "CH": "(CH)" + CK + N4 + N + C3 + C4 + C4 + C,
    # Tunisia   (20n) TNkk bbss sccc cccc cccc cccc
    "TN": "(TN)" + CK + N4 + N4 + N4 + N4 + N4,
    # Turkey    (5n,17c)  TRkk bbbb bxcc cccc cccc cccc cc
    "TR": "(TR)" + CK + N4 + N + C3 + C4 + C4 + C4 + C2,
    # United Arab Emirates  (3n,16n)  AEkk bbbc cccc cccc cccc ccc
    "AE": "(AE)" + CK + N4 + N4 + N4 + N4 + N3,
    # United Kingdom (4a,14n) GBkk bbbb ssss sscc cccc cc
    "GB": "(GB)" + CK + A4 + N4 + N4 + N4 + N2,
    # Vatican City  (3n,15n)  VAkk bbbc cccc cccc cccc cc
    "VA": "(VA)" + CK + N4 + N4 + N4 + N4 + N2,
    # Virgin Islands, British   (4c,16n)  VGkk bbbb cccc cccc cccc cccc
    "VG": "(VG)" + CK + C4 + N4 + N4 + N4 + N4,
    # Egypt (25n) EGkk bbbb ssss cccc cccc cccc ccccc
    "EG": "(EG)" + CK + N4 + N4 + N4 + N4 + N4 + N4 + N,
    # Iraq  (4a,15n)  IQkk bbbb sssc cccc cccc ccc
    "IQ": "(IQ)" + CK + A4 + N4 + N4 + N4 + N3,
    # Libya (21n) LYkk bbbs ssss cccc cccc c
    "LY": "(LY)" + CK + N4 + N4 + N4 + N4 + N4 + N,
    # Saint Lucia   (4a,24c)  LCkk bbbb cccc cccc cccc cccc cccc cccc
    "LC": "(LC)" + CK + A4 + C4 + C4 + C4 + C4 + C4 + C4,
    # Seychelles    (4a,20n,3a)   SCkk bbbb ssnn cccc cccc cccc cccm mmm
    "SC": "(SC)" + CK + A4 + N4 + N4 + N4 + N4 + N4 + A3,
    # Ukraine   (6n,19c)  UAkk bbbb bbcc cccc cccc cccc cccc c
    "UA": "(UA)" + CK + N4 + N2 + C4 + C4 + C4 + C4 + C3,
}
