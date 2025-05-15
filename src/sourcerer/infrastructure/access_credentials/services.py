"""
Implementation of access credential services.

This module provides concrete implementations of the BaseAccessCredentialsService
interface for various cloud providers and authentication methods.
"""

import json
from abc import ABC

import boto3
from azure.identity import ClientSecretCredential
from dependency_injector.wiring import Provide
from google.cloud import storage

from sourcerer.domain.access_credentials.entities import (
    AzureCredentials,
    Boto3Credentials,
    Credentials,
)
from sourcerer.domain.access_credentials.repositories import BaseCredentialsRepository
from sourcerer.domain.access_credentials.services import (
    AuthField,
    BaseAccessCredentialsService,
)
from sourcerer.domain.shared.entities import StorageProvider
from sourcerer.infrastructure.access_credentials.exceptions import (
    CredentialsAuthError,
    MissingAuthFieldsError,
)
from sourcerer.infrastructure.access_credentials.registry import (
    AccessCredentialsMethod,
    access_credentials_method,
)
from sourcerer.infrastructure.utils import generate_uuid
from sourcerer.presentation.di_container import DiContainer


class CredentialsService:
    """
    Service for managing credentials.

    This class provides methods for listing, retrieving, activating,
    and deactivating credentials.
    """

    def __init__(
        self,
        credentials_repo: BaseCredentialsRepository = Provide[
            DiContainer.credentials_repository
        ],
    ):
        """
        Initialize the service with a credentials repository.

        Args:
            credentials_repo (BaseCredentialsRepository): Repository for storing credentials
        """
        self.credentials_repo = credentials_repo

    def list(self, active_only=False):
        """
        List credentials.

        Args:
            active_only (bool, optional): If True, return only active credentials.
                Defaults to False.

        Returns:
            List[Credentials]: List of credentials objects
        """
        return self.credentials_repo.list(active_only)

    def get(self, uuid):
        """
        Get credentials by UUID.

        Args:
            uuid (str): Unique identifier for the credentials

        Returns:
            Credentials: The credentials object
        """
        return self.credentials_repo.get(uuid)

    def activate(self, uuid):
        """
        Activate credentials by UUID.

        Args:
            uuid (str): Unique identifier for the credentials to activate
        """
        self.credentials_repo.activate(uuid)

    def deactivate(self, uuid):
        """
        Deactivate credentials by UUID.

        Args:
            uuid (str): Unique identifier for the credentials to deactivate
        """
        self.credentials_repo.deactivate(uuid)


class AccessCredentialsService(BaseAccessCredentialsService, ABC):
    """
    Base class for access credentials services.

    This abstract class serves as a base for provider-specific
    access credential service implementations.
    """

    def __init__(
        self,
        credentials_repo: BaseCredentialsRepository = Provide[
            DiContainer.credentials_repository
        ],
    ):
        """
        Initialize the service with a credentials repository.

        Args:
            credentials_repo (BaseCredentialsRepository): Repository for storing credentials
        """
        super().__init__(credentials_repo)

    @classmethod
    def validate_auth_fields_values(cls, auth_fields: dict) -> None:
        """
        Validate authentication fields.

        Args:
            auth_fields (dict): Dictionary containing authentication field,
                                where keys are field names and values are field values

        Raises:
            MissingAuthFieldsError: If any required authentication fields are missing
        """
        for field in cls.auth_fields():
            if field.required and field.key not in auth_fields:
                raise MissingAuthFieldsError(f"Missing required field: {field.key}")


class S3AccessCredentialsService(AccessCredentialsService, ABC):
    """
    Base class for AWS S3 access credentials services.

    This abstract class serves as a base for S3-specific
    access credential service implementations.
    """


@access_credentials_method(AccessCredentialsMethod(StorageProvider.S3, "key_pair"))
class S3AccessKeySecretKeyPair(S3AccessCredentialsService):
    """
    AWS S3 access credentials service using access key and secret key.

    This class provides methods for storing, retrieving, and authenticating
    with AWS S3 using access key and secret key credentials.
    """

    def store(self, name, credentials: dict):
        """
        Store AWS access key credentials.

        Args:
            name (str): Name identifier for the credentials
            credentials (dict): Dictionary containing AWS credential information
        """
        self.credentials_repo.create(
            Credentials(
                uuid=generate_uuid(),
                name=name,
                provider=StorageProvider.S3,
                credentials_type="key_pair",
                credentials=json.dumps(credentials),
                active=True,
            )
        )

    def extract(self, uuid: str):
        """
        Extract credentials by UUID.

        Args:
            uuid (str): UUID of the credentials to extract

        Returns:
            Credentials: The credentials object
        """
        return self.credentials_repo.get(uuid)

    def authenticate(self, credentials: str):  # type: ignore
        """
        Authenticate using stored credentials.

        Args:
            credentials (str): JSON string containing credential information

        Returns:
            boto3.Session: Authenticated boto3 session
        """
        try:
            credentials: dict = json.loads(credentials)

            session_args = {
                "aws_access_key_id": credentials.get("aws_access_key_id"),
                "aws_secret_access_key": credentials.get("aws_secret_access_key"),
            }

            if region := credentials.get("region"):
                session_args["region_name"] = region

            session = boto3.Session(**session_args)

            return Boto3Credentials(
                session=session,
                endpoint_url=credentials.get("endpoint_url", None),
                signature_version=credentials.get("signature_version", None),
            )
        except Exception as e:
            raise CredentialsAuthError("Failed to authenticate") from e

    @classmethod
    def auth_fields(cls):
        """
        Get list of authentication fields.

        Returns:
            List[AuthField]: List of authentication field definitions
        """
        return [
            AuthField("aws_access_key_id", "AWS Access Key Id", True),
            AuthField("aws_secret_access_key", "AWS Secret Access Key", True),
            AuthField("region", "Region", False),
            AuthField("endpoint_url", "Endpoint Url", False),
        ]


@access_credentials_method(AccessCredentialsMethod(StorageProvider.S3, "profile_name"))
class S3ProfileName(S3AccessCredentialsService):
    """
    AWS S3 access credentials service using profile name.

    This class provides methods for storing, retrieving, and authenticating
    with AWS S3 using a named profile from AWS configuration.
    """

    def store(self, name, credentials: dict):
        """
        Store AWS profile name credentials.

        Args:
            name (str): Name identifier for the credentials
            credentials (dict): Dictionary containing profile name information
        """
        self.credentials_repo.create(
            Credentials(
                uuid=generate_uuid(),
                name=name,
                provider=StorageProvider.S3,
                credentials_type="profile_name",
                credentials=json.dumps(credentials),
                active=True,
            )
        )

    def extract(self, uuid: str):
        """
        Extract credentials by UUID.

        Args:
            uuid (str): UUID of the credentials to extract

        Returns:
            Credentials: The credentials object
        """
        return self.credentials_repo.get(uuid)

    def authenticate(self, credentials: str):  # type: ignore
        """
        Authenticate using stored profile name.

        Args:
            credentials (str): Dictionary containing profile name information

        Returns:
            boto3.Session: Authenticated boto3 session
        """
        try:
            credentials: dict = json.loads(credentials)
            session = boto3.Session(profile_name=credentials.get("profile_name"))
            return Boto3Credentials(
                session=session,
                endpoint_url=credentials.get("endpoint_url"),
            )
        except Exception as e:
            raise CredentialsAuthError("Failed to authenticate") from e

    @classmethod
    def auth_fields(cls) -> list[AuthField]:
        """
        Get list of authentication fields.

        Returns:
            List[AuthField]: List of authentication field definitions
        """
        return [
            AuthField("profile_name", "Profile Name", True),
            AuthField("endpoint_url", "Endpoint Url", False),
        ]


@access_credentials_method(
    AccessCredentialsMethod(StorageProvider.GoogleCloudStorage, "Service account")
)
class GCPCredentialsService(AccessCredentialsService):
    """
    Google Cloud Platform json credentials service.

    This class provides methods for storing, retrieving, and authenticating
    with GCP using credentials.
    """

    def store(self, name, credentials: dict):
        """
        Store GCP json credentials.

        Args:
            name (str): Name identifier for the credentials
            credentials (dict): Dictionary containing GCP credential information
        """
        self.credentials_repo.create(
            Credentials(
                uuid=generate_uuid(),
                name=name,
                provider=StorageProvider.GoogleCloudStorage,
                credentials_type="Service account",
                credentials=json.dumps(credentials),
                active=True,
            )
        )

    def extract(self, uuid):
        """
        Extract credentials by UUID.

        Args:
            uuid (str): UUID of the credentials to extract

        Returns:
            Credentials: The credentials object
        """
        return self.credentials_repo.get(uuid)

    def authenticate(self, credentials: str):  # type: ignore
        """
        Authenticate with Google Cloud Platform using service account credentials.

        This method parses the stored credentials JSON string, extracts the service account
        information, and creates a Google Cloud Storage client authenticated with those
        credentials.

        Args:
            credentials (str): JSON string containing the service account credentials

        Returns:
            storage.Client: Authenticated Google Cloud Storage client

        Raises:
            ValueError: If the credentials are missing required fields
            json.JSONDecodeError: If the credentials are not valid JSON
            Exception: If authentication fails for any other reason
        """
        try:
            # Parse the outer JSON structure
            parsed_credentials = json.loads(credentials)

            # Extract the service account JSON string
            service_acc_json = parsed_credentials.get("service_acc")
            if not service_acc_json:
                raise ValueError("Missing 'service_acc' field in credentials")

            # Parse the service account JSON
            try:
                service_acc_info = json.loads(service_acc_json)
            except json.JSONDecodeError as e:
                raise ValueError("Invalid service account JSON format") from e

            # Create and return the authenticated client
            return storage.Client.from_service_account_info(service_acc_info)

        except json.JSONDecodeError as e:
            raise CredentialsAuthError(f"Invalid credentials format: {str(e)}") from e
        except Exception as e:
            raise CredentialsAuthError(
                f"Failed to authenticate with GCP: {str(e)}"
            ) from e

    @classmethod
    def auth_fields(cls) -> list[AuthField]:
        """
        Get list of authentication fields.

        Returns:
            List[AuthField]: List of authentication field definitions
        """
        return [
            AuthField("service_acc", "Service acc", True, True),
        ]


@access_credentials_method(
    AccessCredentialsMethod(StorageProvider.AzureStorage, "Client Secret Credentials")
)
class AzureClientSecretCredentialsService(AccessCredentialsService):

    def store(self, name, credentials: dict):
        """
        Store Azure client_id and secret_key_pair credentials.

        Args:
            name (str): Name identifier for the credentials
            credentials (dict): Dictionary containing Azure application credential information
        """
        self.credentials_repo.create(
            Credentials(
                uuid=generate_uuid(),
                name=name,
                provider=StorageProvider.AzureStorage,
                credentials_type="Client Secret Credentials",
                credentials=json.dumps(credentials),
                active=True,
            )
        )

    def extract(self, uuid):
        """
        Extract credentials by UUID.

        Args:
            uuid (str): UUID of the credentials to extract

        Returns:
            Credentials: The credentials object
        """
        return self.credentials_repo.get(uuid)

    def authenticate(self, credentials: str):  # type: ignore
        try:
            # Parse the outer JSON structure
            parsed_credentials = json.loads(credentials)
            subscription_id = parsed_credentials.get("subscription_id")
            cloud_suffix = (
                parsed_credentials.get("cloud_suffix") or "blob.core.windows.net"
            )

            client_credentials = ClientSecretCredential(
                tenant_id=parsed_credentials.get("tenant_id"),
                client_id=parsed_credentials.get("client_id"),
                client_secret=parsed_credentials.get("client_secret"),
            )

            return AzureCredentials(
                credentials=client_credentials,
                subscription_id=subscription_id,
                cloud_suffix=cloud_suffix,
            )

        except json.JSONDecodeError as e:
            raise CredentialsAuthError(f"Invalid credentials format: {str(e)}") from e
        except Exception as e:
            raise CredentialsAuthError(
                f"Failed to authenticate with Azure: {str(e)}"
            ) from e

    @classmethod
    def auth_fields(cls) -> list[AuthField]:
        """
        Get list of authentication fields.

        Returns:
            List[AuthField]: List of authentication field definitions
        """
        return [
            AuthField("subscription_id", "Subscription Id", True),
            AuthField("tenant_id", "Tenant Id", True),
            AuthField("client_id", "Client Id", True),
            AuthField("client_secret", "Client Secret", True),
            AuthField(
                "cloud_suffix", "Cloud Suffix (default blob.core.windows.net)", False
            ),
        ]
