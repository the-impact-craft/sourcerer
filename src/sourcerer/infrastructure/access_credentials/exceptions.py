from sourcerer.domain.access_credentials.exceptions import (
    BaseAccessCredentialsException,
)


class CredentialsAuthError(BaseAccessCredentialsException):
    """
    Exception raised when there is an error parsing access credentials.

    This exception is raised when the access credentials cannot be
    authenticated or parsed correctly. It indicates that the provided
    credentials are invalid or not in the expected format.
    This can occur during operations such as login, token validation,
    or any other authentication process that relies on the provided
    credentials.
    """
