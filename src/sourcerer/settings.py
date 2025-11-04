"""
Application settings module.

This module contains configuration settings for the application,
including encryption keys, UI constants, and file type definitions.
It centralizes configuration values to make them easily accessible
and modifiable throughout the application.
"""

import os
from pathlib import Path

from platformdirs import user_state_dir

from sourcerer.utils import get_encryption_key

APP_NAME = "sourcerer"

APP_DIR = Path(user_state_dir(APP_NAME))
os.makedirs(APP_DIR, exist_ok=True)

DB_NAME = "sourcerer.db"

ENCRYPTION_KEY = get_encryption_key(APP_DIR)

MAX_PARALLEL_STORAGE_LIST_OPERATIONS = 3

# Maximum number of parallel download operations
MAX_PARALLEL_DOWNLOADS = 8

PATH_DELIMITER = "/"

# UI icons for different file system elements
DIRECTORY_ICON = "📁"
FILE_ICON = "📄"

# Action icons
DOWNLOAD_ICON = "📥"
UPLOAD_ICON = "📤"
PREVIEW_ICON = "✨"
PRESIGNED_URL_ICON = "🔗"

# Time threshold for detecting double-clicks (in seconds)
DOUBLE_CLICK_THRESHOLD = 1.5

# Set of file extensions that are considered text files
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".csv",
    ".tsv",
    ".log",
    ".ini",
    ".py",
    ".js",
    ".ts",
    ".html",
    ".css",
    ".xml",
    ".toml",
    ".cfg",
    ".sh",
    ".bat",
    ".java",
    ".c",
    ".cpp",
    ".go",
    ".rs",
    ".tfstate",
    ".tf",
}


PAGE_SIZE = 100
PREVIEW_LENGTH_LIMIT = 10_000
PREVIEW_LIMIT_SIZE = 2 * 1024 * 1024  # 2 MB

MAX_CREDENTIALS_CACHE_SIZE = 30

DEFAULT_UPLOAD_CHUNK_SIZE_MB = 30
DEFAULT_DOWNLOAD_CHUNK_SIZE_MB = 30
DEFAULT_PRESIGNED_URL_TTL_SECONDS = 3600
