"""
Utility functions for the Sourcerer application.

This module provides various utility functions used throughout the application,
including UUID generation, MIME type detection, and file type checking.
"""

import mimetypes
import secrets
import uuid
from pathlib import Path
from typing import ClassVar

from sourcerer.settings import TEXT_EXTENSIONS


def is_text_mime(filename):
    """
    Determine if a file has a text MIME type.

    This function uses the mimetypes module to guess the MIME type of a file
    based on its filename, then checks if the MIME type starts with "text/".

    Args:
        filename (str): The name of the file to check

    Returns:
        bool: True if the file has a text MIME type, False otherwise
    """
    mime, _ = mimetypes.guess_type(filename)
    return mime is not None and mime.startswith("text/")


def generate_uuid():
    """
    Generate a unique identifier (UUID).

    This function creates a UUID using the uuid4() function from the uuid module.
    The UUID is prefixed with 'a' to ensure compatibility for ID usage in various
    contexts.

    Returns:
        str: A unique identifier string prefixed with 'a'
    """
    return f"a{uuid.uuid4()}"


def is_text_file(file_name):
    """
    Check if the given file is a text file based on its extension or MIME type.

    This function determines if a file is a text file by checking if its extension
    is in the predefined TEXT_EXTENSIONS list or if its MIME type indicates it's
    a text file.

    Args:
        file_name (str): The name of the file to check

    Returns:
        bool: True if the file is a text file, False otherwise
    """
    ext = Path(file_name).suffix.lower()
    if ext in TEXT_EXTENSIONS:
        return True
    return bool(is_text_mime(file_name))


def custom_sort_key(s: str | Path):
    """
    Converts a string by replacing '.' with a character '{' (ASCII 123)
    to ensure that strings are sorted in a specific order where '.'
    is considered after all letters in ASCII comparison.

    Args:
        s (str|Path): The string to be transformed for custom sorting.

    Returns:
        str: A string transformed to facilitate the desired sorting order.
    """
    return str(s).replace(".", "{")


class Singleton(type):
    """
    Metaclass that implements the singleton pattern, ensuring only one instance of a class exists.
    """

    _instances: ClassVar[dict["Singleton", type]] = {}

    def __call__(cls, *args, **kwargs):
        """
        Create or return the singleton instance of the class.

        If an instance does not exist, instantiate the class with the given arguments.
        Otherwise, return the existing instance.

        Args:
            *args: Positional arguments for class instantiation.
            **kwargs: Keyword arguments for class instantiation.

        Returns:
            object: The singleton instance of the class.
        """
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


def generate_unique_name() -> str:
    """
    Generate a unique name for a file or directory.

    Returns:
        str: A unique name
    """
    adjectives = [
        "goofy",
        "quirky",
        "snappy",
        "witty",
        "bubbly",
        "zany",
        "wonky",
        "clumsy",
        "cheeky",
        "sassy",
        "cryptic",
        "shadowy",
        "enigmatic",
        "arcane",
        "veiled",
        "hidden",
        "phantasmal",
        "whispering",
        "hollow",
        "ghostly",
        "mighty",
        "fierce",
        "brave",
        "bold",
        "ironclad",
        "unyielding",
        "stormforged",
        "grim",
        "feral",
        "dauntless",
        "stellar",
        "vivid",
        "luminous",
        "glimmering",
        "blazing",
        "radiant",
        "shimmering",
        "snazzy",
        "flashy",
        "dazzling",
    ]

    names = [
        "gandalf",
        "merlin",
        "morgana",
        "radagast",
        "saruman",
        "galadriel",
        "smaug",
        "elminster",
        "ambrosius",
        "balrog",
        "sauron",
        "rivendell",
        "azkaban",
        "gryffindor",
        "slytherin",
        "rowena",
        "helga",
        "alatar",
        "pellinore",
        "nimue",
        "glorfindel",
        "melian",
        "feanor",
        "titania",
        "oberon",
        "cerberus",
        "phoenix",
        "gryphon",
        "hydra",
        "basilisk",
        "leviathan",
        "wraith",
        "djinn",
        "fae",
        "nymph",
        "dryad",
        "selkie",
        "witchking",
        "morwen",
        "telvanni",
        "daedric",
        "argonian",
        "auriel",
        "azura",
        "boethiah",
        "nocturnal",
        "zarthos",
        "shadar",
        "kobold",
        "lich",
        "oracle",
        "summoner",
        "geomancer",
        "runeweaver",
        "voidcaller",
        "planewalker",
    ]

    adjective = secrets.choice(adjectives)
    name = secrets.choice(names)
    return f"{adjective}_{name}"


def join_non_empty(items: list, separator: str):
    """join strings with separator skipping empty values

    Args:
        items (list): A list of strings.
        separator(str): The separator to join strings with.
    """
    return separator.join([str(i) for i in items if i])
