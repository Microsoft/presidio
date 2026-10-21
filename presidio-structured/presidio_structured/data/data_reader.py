"""Helper data classes, mostly simple wrappers  to ensure consistent user interface."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, Optional, Union

import pandas as pd


class ReaderBase(ABC):
    """
    Base class for data readers.

    This class should not be instantiated directly, instead init a subclass.
    """

    @abstractmethod
    def read(self, path: Union[str, Path], **kwargs) -> Any:
        """
        Extract data from file located at path.

        :param path: String defining the location of the file to read.
        :return: The data read from the file.
        """
        pass


class CsvReader(ReaderBase):
    """
    Reader for reading csv files.

    Usage::

        reader = CsvReader()
        data = reader.read(path="filepath.csv")

    A reader can also be given an encoding to use for every file it reads::

        reader = CsvReader(encoding="cp1252")
        data = reader.read(path="filepath.csv")

    """

    def __init__(self, encoding: Optional[str] = None):
        """
        Initialize the reader.

        :param encoding: Encoding to read files with, unless read() is
            called with an explicit encoding. Defaults to None, which
            leaves the choice to pandas, i.e. utf-8.
        """
        self.encoding = encoding

    def read(self, path: Union[str, Path], **kwargs) -> pd.DataFrame:
        """
        Read csv file to pandas dataframe.

        :param path: String defining the location of the csv file to read.
        :param encoding: Encoding to read the file with, overriding the one
            the reader was created with. Remaining keyword arguments go to
            pandas.read_csv.
        :return: Pandas DataFrame with the data read from the csv file.
        """
        kwargs.setdefault("encoding", self.encoding)
        return pd.read_csv(path, **kwargs)


class JsonReader(ReaderBase):
    """
    Reader for reading json files.

    Usage::

        reader = JsonReader()
        data = reader.read(path="filepath.json")

    A reader can also be given an encoding to use for every file it reads::

        reader = JsonReader(encoding="cp1252")
        data = reader.read(path="filepath.json")

    """

    def __init__(self, encoding: Optional[str] = None):
        """
        Initialize the reader.

        :param encoding: Encoding to read files with, unless read() is
            called with an explicit encoding. Defaults to None, which
            leaves the choice to open(), i.e. the platform's locale
            encoding.
        """
        self.encoding = encoding

    def read(self, path: Union[str, Path], **kwargs) -> Dict[str, Any]:
        """
        Read json file to dict.

        :param path: String defining the location of the json file to read.
        :param encoding: Encoding to open the file with, overriding the one
            the reader was created with. Remaining keyword arguments go to
            json.load, which has no encoding parameter of its own.
        :return: dictionary with the data read from the json file.
        """
        encoding = kwargs.pop("encoding", self.encoding)
        with open(path, encoding=encoding) as f:
            data = json.load(f, **kwargs)
        return data
