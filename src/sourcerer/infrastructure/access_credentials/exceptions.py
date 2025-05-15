from sourcerer.domain.access_credentials.exceptions import (
    BaseAccessCredentialsError,
)


class CredentialsAuthError(BaseAccessCredentialsError):
    """
    Exception raised when there is an error parsing access credentials.

    This exception is raised when the access credentials cannot be
    authenticated or parsed correctly. It indicates that the provided
    credentials are invalid or not in the expected format.
    This can occur during operations such as login, token validation,
    or any other authentication process that relies on the provided
    credentials.
    """


class MissingAuthFieldsError(CredentialsAuthError):
    """
    Exception raised when there are missing authentication fields.

    This exception is raised when the required authentication fields
    are missing from the provided credentials. It indicates that the
    authentication process cannot proceed without the necessary
    credentials. This can occur during operations such as login,
    token validation, or any other authentication process that relies
    on the provided credentials.
    """
