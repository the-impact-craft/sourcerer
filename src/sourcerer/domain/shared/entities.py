"""
Shared entity classes and constants.

This module defines shared entities and constants used across
different parts of the application.
"""


class StorageProvider:
    """
    Constants representing supported cloud storage providers.

    This class defines string constants for each supported storage provider,
    which are used throughout the application to identify provider types.
    """

    S3 = "S3"
    GoogleCloudStorage = "Google Cloud Storage"
    AzureStorage = "Azure Storage"
