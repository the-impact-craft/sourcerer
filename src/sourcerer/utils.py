import contextlib
import os
import uuid
from pathlib import Path

import requests


def get_encryption_key(path: Path) -> str:
    """
    Get the encryption key from a file or generate a new one if the file doesn't exist.

    path (Path): The path to the file where the encryption key is stored.
    Returns:
        str: The encryption key
    """

    key_file_path = path / "encryption_key"

    # If key file exists, read the key from it
    if os.path.exists(key_file_path):
        with open(key_file_path, encoding="utf-8") as f:
            return f.read().strip()

    # Otherwise, generate a new key and store it

    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(key_file_path), exist_ok=True)

    new_key = str(uuid.uuid4())
    with open(key_file_path, "w", encoding="utf-8") as f:
        f.write(new_key)

    return new_key


def get_last_package_version(name):
    """
    Fetch the latest version of a package from PyPI.
    Args:
        name (str): The name of the package.
    Returns:
        str: The latest version of the package, or None if an error occurs.
    """
    with contextlib.suppress(Exception):
        url = f"https://pypi.org/pypi/{name}/json"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()["info"]["version"]
    return None
