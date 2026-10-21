import json

import pytest

from presidio_structured import CsvReader, JsonReader

# "José" and "Bogotá" are not valid UTF-8 when written as cp1252.
LATIN1_NAME = "José"
LATIN1_CITY = "Bogotá"


@pytest.fixture
def cp1252_csv(tmp_path):
    path = tmp_path / "people.csv"
    path.write_bytes(f"name,city\n{LATIN1_NAME},{LATIN1_CITY}\n".encode("cp1252"))
    return path


@pytest.fixture
def cp1252_json(tmp_path):
    path = tmp_path / "person.json"
    body = json.dumps({"name": LATIN1_NAME, "city": LATIN1_CITY}, ensure_ascii=False)
    path.write_bytes(body.encode("cp1252"))
    return path


@pytest.fixture
def ascii_json(tmp_path):
    path = tmp_path / "ascii.json"
    path.write_text(json.dumps({"name": "John Doe", "id": 1}), encoding="ascii")
    return path


def test_when_csv_reader_has_encoding_then_it_is_used_for_read(cp1252_csv):
    df = CsvReader(encoding="cp1252").read(cp1252_csv)

    assert df.to_dict("records") == [{"name": LATIN1_NAME, "city": LATIN1_CITY}]


def test_when_csv_read_gets_encoding_then_it_overrides_the_reader_one(cp1252_csv):
    df = CsvReader(encoding="utf-8").read(cp1252_csv, encoding="cp1252")

    assert df.to_dict("records") == [{"name": LATIN1_NAME, "city": LATIN1_CITY}]


def test_when_csv_reader_has_no_encoding_then_utf8_file_still_reads(tmp_path):
    path = tmp_path / "utf8.csv"
    path.write_text(f"name,city\n{LATIN1_NAME},{LATIN1_CITY}\n", encoding="utf-8")

    df = CsvReader().read(path)

    assert df.to_dict("records") == [{"name": LATIN1_NAME, "city": LATIN1_CITY}]


def test_when_csv_read_gets_other_kwargs_then_they_reach_read_csv(cp1252_csv):
    df = CsvReader(encoding="cp1252").read(cp1252_csv, usecols=["name"])

    assert list(df.columns) == ["name"]


def test_when_json_reader_has_encoding_then_it_is_used_for_read(cp1252_json):
    data = JsonReader(encoding="cp1252").read(cp1252_json)

    assert data == {"name": LATIN1_NAME, "city": LATIN1_CITY}


def test_when_json_read_gets_encoding_then_it_overrides_the_reader_one(cp1252_json):
    data = JsonReader(encoding="utf-8").read(cp1252_json, encoding="cp1252")

    assert data == {"name": LATIN1_NAME, "city": LATIN1_CITY}


def test_when_default_json_reader_gets_encoding_then_it_is_used(cp1252_json):
    data = JsonReader().read(cp1252_json, encoding="cp1252")

    assert data == {"name": LATIN1_NAME, "city": LATIN1_CITY}


def test_when_json_reader_has_no_encoding_then_ascii_file_still_reads(ascii_json):
    data = JsonReader().read(ascii_json)

    assert data == {"name": "John Doe", "id": 1}


def test_when_json_read_gets_other_kwargs_then_they_reach_json_load(ascii_json):
    data = JsonReader(encoding="ascii").read(ascii_json, parse_int=float)

    assert isinstance(data["id"], float)
