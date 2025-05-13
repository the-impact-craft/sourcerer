"""
Access credentials entity classes.

This module defines data classes representing access credentials
used for authentication with various cloud providers.
"""

from dataclasses import dataclass
from datetime import datetime

import boto3
from azure.identity import ClientSecretCredential


@dataclass
class Credentials:
    """
    Represents access credentials for a provider.

    Attributes:
        uuid (str): Unique identifier for the credentials.
        name (str): Name of the credentials.
        provider (str): Name of the service provider.
        credentials_type (str): Type of credentials (e.g., key_pair).
        credentials (str): Serialized credentials data.
        active (bool): Indicates if the credentials are active.
        created_at (datetime | None): Timestamp when the credentials were created.
        updated_at (datetime | None): Timestamp when the credentials were last updated.
    """

    uuid: str
    name: str
    provider: str
    credentials_type: str
    credentials: str
    active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass
class Boto3Credentials:
    """
    Represents AWS credentials using boto3 session.

    Attributes:
        session (boto3.Session): The boto3 session object for AWS authentication.
        endpoint_url (str|None): Optional custom endpoint URL for AWS services.
        signature_version (str|None): Optional signature version for AWS API requests.
    """

    session: boto3.Session
    endpoint_url: str | None = None
    signature_version: str | None = None


@dataclass
class AzureCredentials:
    """
    Represents Azure credentials.

    Attributes:
        credentials (ClientSecretCredential): Azure identity credential object for authentication.
        subscription_id (str): The Azure subscription ID.
        cloud_suffix (str): The Azure cloud storage suffix (e.g., blob.core.windows.net).
    """

    credentials: ClientSecretCredential
    subscription_id: str
    cloud_suffix: str
